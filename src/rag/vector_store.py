"""Qdrant vector store client.

Manages Qdrant collections for document embeddings.
"""

from typing import Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, VectorParams, PayloadSchemaType

from src.core.config import get_settings


class VectorStore:
    """Qdrant vector store for RAG embeddings.
    
    Each knowledge base has its own collection with:
    - Vector embeddings (1536 dims for text-embedding-3-small)
    - Payload: document_id, chunk_index, text, metadata, ACL
    """
    
    EMBEDDING_DIMENSION = 1536  # text-embedding-3-small
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    async def create_collection(
        self,
        collection_name: str,
        embedding_dim: int = EMBEDDING_DIMENSION,
    ) -> bool:
        """Create a new Qdrant collection for a knowledge base.
        
        Args:
            collection_name: Unique collection name (usually kb_{kb_id})
            embedding_dim: Embedding vector dimension
            
        Returns:
            True if created, False if already exists
        """
        # Check if collection exists
        collections = self.client.get_collections()
        existing_names = [c.name for c in collections.collections]
        
        if collection_name in existing_names:
            return False
        
        # Create collection with optimized settings
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE,
            ),
            # Enable payload indexing for filtering
            optimizers_config=qdrant_models.OptimizersConfigDiff(
                indexing_threshold=1000,  # Build index after 1000 points
            ),
        )
        
        # Create payload indexes for common filters
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="tenant_id",
            field_schema=PayloadSchemaType.KEYWORD,
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
        if not chunks:
            return 0
        
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
        
        self.client.upsert(
            collection_name=collection_name,
            points=points,
        )
        
        return len(points)
    
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
        user_id: Optional[str] = None,
        group_ids: Optional[list[str]] = None,
        tenant_id: Optional[str] = None,
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
            filter_conditions.append(
                qdrant_models.Filter(should=acl_conditions)
            )
        
        # Combine filters
        query_filter = None
        if filter_conditions:
            query_filter = qdrant_models.Filter(must=filter_conditions)
        
        # Execute search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
        )
        
        return [
            {
                "id": str(result.id),
                "score": result.score,
                "text": result.payload.get("text", ""),
                "document_id": result.payload.get("document_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "metadata": result.payload.get("metadata", {}),
            }
            for result in results
        ]
    
    async def get_collection_info(self, collection_name: str) -> Optional[dict]:
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
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global VectorStore instance."""
    global _vector_store
    
    if _vector_store is None:
        settings = get_settings()
        client = QdrantClient(url=settings.qdrant_url)
        _vector_store = VectorStore(client)
    
    return _vector_store
