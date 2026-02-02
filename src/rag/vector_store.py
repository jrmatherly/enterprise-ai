"""Qdrant vector store client.

Manages Qdrant collections for document embeddings.
"""

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from src.core.config import get_settings


class VectorStore:
    """Qdrant vector store for RAG embeddings.

    Each knowledge base has its own collection with:
    - Vector embeddings (dimensions from config)
    - Payload: document_id, chunk_index, text, metadata, ACL
    """

    def __init__(self, client: QdrantClient, embedding_dim: int | None = None):
        self.client = client
        # Get embedding dimensions from config if not provided
        settings = get_settings()
        self.embedding_dim = embedding_dim or settings.embedding_dimensions

    async def create_collection(
        self,
        collection_name: str,
        embedding_dim: int | None = None,
    ) -> bool:
        """Create a new Qdrant collection for a knowledge base.

        Args:
            collection_name: Unique collection name (usually kb_{kb_id})
            embedding_dim: Embedding vector dimension (defaults to config setting)

        Returns:
            True if created, False if already exists
        """
        # Use instance embedding_dim if not overridden
        dim = embedding_dim or self.embedding_dim

        # Check if collection exists
        collections = self.client.get_collections()
        existing_names = [c.name for c in collections.collections]

        if collection_name in existing_names:
            return False

        # Create collection with optimized settings for enterprise multitenancy
        # See: https://qdrant.tech/documentation/guides/multitenancy/
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE,
            ),
            # Store large text payloads on disk to save RAM
            on_disk_payload=True,
            # HNSW config for multitenancy: per-tenant indexes instead of global
            hnsw_config=qdrant_models.HnswConfigDiff(
                payload_m=16,  # Build index per partition (tenant)
                m=16,  # Keep global index for cross-tenant queries
            ),
            # Optimizer settings
            optimizers_config=qdrant_models.OptimizersConfigDiff(
                indexing_threshold=1000,  # Build index after 1000 points
            ),
            # Scalar quantization: 4x memory reduction with ~99% accuracy
            # See: https://qdrant.tech/documentation/guides/quantization/
            quantization_config=qdrant_models.ScalarQuantization(
                scalar=qdrant_models.ScalarQuantizationConfig(
                    type=qdrant_models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,  # Keep quantized vectors in RAM for speed
                ),
            ),
        )

        # Create payload indexes for common filters
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        # Tenant index with is_tenant=True for optimized multitenancy storage
        # This co-locates vectors of the same tenant together on disk
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="tenant_id",
            field_schema=qdrant_models.KeywordIndexParams(
                type=qdrant_models.KeywordIndexType.KEYWORD,
                is_tenant=True,
            ),
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="acl_users",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="acl_groups",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        return True

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    async def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[dict],
    ) -> int:
        """Insert or update document chunks.

        Args:
            collection_name: Target collection
            chunks: List of chunk dicts with:
                - id: Unique chunk ID
                - vector: Embedding vector
                - document_id: Parent document ID
                - chunk_index: Index within document
                - text: Chunk text content
                - metadata: Additional metadata
                - tenant_id: Owning tenant
                - acl_users: List of user IDs with access
                - acl_groups: List of group IDs with access

        Returns:
            Number of chunks upserted
        """
        import logging

        logger = logging.getLogger(__name__)

        if not chunks:
            return 0

        # Debug: log upsert details
        logger.info(
            f"[VectorStore] Upserting {len(chunks)} chunks to collection '{collection_name}'"
        )
        if chunks:
            first = chunks[0]
            logger.info(
                f"[VectorStore] First chunk ID: {first.get('id')}, vector dim: {len(first.get('vector', []))}"
            )

        points = [
            qdrant_models.PointStruct(
                id=chunk.get("id", str(uuid4())),
                vector=chunk["vector"],
                payload={
                    "document_id": chunk["document_id"],
                    "chunk_index": chunk.get("chunk_index", 0),
                    "text": chunk["text"],
                    "metadata": chunk.get("metadata", {}),
                    "tenant_id": chunk["tenant_id"],
                    "acl_users": chunk.get("acl_users", []),
                    "acl_groups": chunk.get("acl_groups", []),
                },
            )
            for chunk in chunks
        ]

        # Batch upserts to avoid timeout on large payloads
        # Each vector is ~12KB (3072 floats * 4 bytes), so 100 points = ~1.2MB
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            logger.info(
                f"[VectorStore] Upserting batch {i // batch_size + 1}/{(len(points) + batch_size - 1) // batch_size} ({len(batch)} points)"
            )
            self.client.upsert(
                collection_name=collection_name,
                points=batch,
            )
            total_upserted += len(batch)

        logger.info(f"[VectorStore] Successfully upserted {total_upserted} points")
        return total_upserted

    async def delete_document_chunks(
        self,
        collection_name: str,
        document_id: str,
    ) -> int:
        """Delete all chunks for a document.

        Returns:
            Number of chunks deleted
        """
        # Get count before deletion
        count_before = self.client.count(
            collection_name=collection_name,
            count_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="document_id",
                        match=qdrant_models.MatchValue(value=document_id),
                    )
                ]
            ),
        ).count

        # Delete by document_id filter
        self.client.delete(
            collection_name=collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="document_id",
                            match=qdrant_models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

        return count_before

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5,
        user_id: str | None = None,
        group_ids: list[str] | None = None,
        tenant_id: str | None = None,
        score_threshold: float = 0.5,
    ) -> list[dict]:
        """Search for similar chunks with access control filtering.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Maximum results
            user_id: Current user ID for ACL filtering
            group_ids: User's group IDs for ACL filtering
            tenant_id: Tenant ID for filtering
            score_threshold: Minimum similarity score

        Returns:
            List of matching chunks with scores
        """
        # Build ACL filter
        filter_conditions = []

        if tenant_id:
            filter_conditions.append(
                qdrant_models.FieldCondition(
                    key="tenant_id",
                    match=qdrant_models.MatchValue(value=tenant_id),
                )
            )

        # ACL: user must be in acl_users OR have a group in acl_groups
        acl_conditions = []
        if user_id:
            acl_conditions.append(
                qdrant_models.FieldCondition(
                    key="acl_users",
                    match=qdrant_models.MatchAny(any=[user_id]),
                )
            )
        if group_ids:
            acl_conditions.append(
                qdrant_models.FieldCondition(
                    key="acl_groups",
                    match=qdrant_models.MatchAny(any=group_ids),
                )
            )

        if acl_conditions:
            filter_conditions.append(qdrant_models.Filter(should=acl_conditions))

        # Combine filters
        query_filter = None
        if filter_conditions:
            query_filter = qdrant_models.Filter(must=filter_conditions)

        # Execute search using query_points (renamed from search in qdrant-client 1.7+)
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "text": point.payload.get("text", ""),
                "document_id": point.payload.get("document_id"),
                "chunk_index": point.payload.get("chunk_index"),
                "metadata": point.payload.get("metadata", {}),
            }
            for point in results.points
        ]

    async def get_collection_info(self, collection_name: str) -> dict | None:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except Exception:
            return None


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create the global VectorStore instance."""
    global _vector_store

    if _vector_store is None:
        settings = get_settings()
        # Configure longer timeout for large document processing
        # Default 5s is too short for batched upserts
        client = QdrantClient(
            url=settings.qdrant_url,
            timeout=60,  # 60 seconds timeout
        )
        _vector_store = VectorStore(client)

    return _vector_store
