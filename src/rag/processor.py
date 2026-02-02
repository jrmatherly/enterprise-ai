"""Document processor for RAG ingestion.

Handles document extraction, chunking, embedding, and storage.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, uuid5

from src.rag.chunking import get_chunker
from src.rag.embedder import Embedder, get_embedder
from src.rag.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of document processing."""

    success: bool
    document_id: str
    chunk_count: int
    error: str | None = None
    processing_time_ms: int = 0


class DocumentProcessor:
    """Processes documents for RAG ingestion.

    Pipeline:
    1. Extract text from document
    2. Split into chunks
    3. Generate embeddings
    4. Store in vector database
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        chunking_strategy: str = "paragraph",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.chunker = get_chunker(
            strategy=chunking_strategy,
            max_chunk_size=chunk_size,
        )
        self.chunking_strategy = chunking_strategy

    async def process_text(
        self,
        text: str,
        document_id: str,
        collection_name: str,
        tenant_id: str,
        acl_users: list[str] | None = None,
        acl_groups: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ProcessingResult:
        """Process raw text for a document.

        Args:
            text: Document text content
            document_id: Document ID in database
            collection_name: Qdrant collection name (from KnowledgeBase.collection_name)
            tenant_id: Owning tenant
            acl_users: User IDs with read access
            acl_groups: Group IDs with read access
            metadata: Additional metadata to store

        Returns:
            ProcessingResult with status and chunk count
        """
        start_time = datetime.now(UTC)
        logger.info(
            f"[Processor] Starting document processing: doc_id={document_id}, collection={collection_name}"
        )

        try:
            # 1. Chunk the document
            logger.debug(f"[Processor] Chunking document, text length: {len(text)}")
            chunks = self.chunker.chunk(text, metadata)

            if not chunks:
                logger.warning(f"[Processor] No chunks generated for document {document_id}")
                return ProcessingResult(
                    success=False,
                    document_id=document_id,
                    chunk_count=0,
                    error="No chunks generated from document",
                )

            logger.info(f"[Processor] Generated {len(chunks)} chunks")

            # 2. Generate embeddings for all chunks
            logger.info(f"[Processor] Generating embeddings for {len(chunks)} chunks...")
            chunk_texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_texts(chunk_texts)
            logger.info("[Processor] Embeddings generated successfully")

            # 3. Prepare chunks for storage
            vector_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
                # Generate deterministic UUID for chunk (document_id + chunk_index)
                # This ensures idempotent re-processing
                chunk_id = str(uuid5(NAMESPACE_DNS, f"{document_id}:{i}"))
                vector_chunks.append(
                    {
                        "id": chunk_id,
                        "vector": embedding,
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk.text,
                        "tenant_id": tenant_id,
                        "acl_users": acl_users or [],
                        "acl_groups": acl_groups or [],
                        "metadata": {
                            **(metadata or {}),
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                        },
                    }
                )

            # 4. Store in vector database
            logger.info(
                f"[Processor] Upserting {len(vector_chunks)} chunks to Qdrant collection '{collection_name}'"
            )
            await self.vector_store.upsert_chunks(collection_name, vector_chunks)
            logger.info("[Processor] Successfully stored chunks in Qdrant")

            end_time = datetime.now(UTC)
            processing_time = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"[Processor] Document processed successfully in {processing_time}ms: {len(vector_chunks)} chunks"
            )
            return ProcessingResult(
                success=True,
                document_id=document_id,
                chunk_count=len(vector_chunks),
                processing_time_ms=processing_time,
            )

        except Exception as e:
            end_time = datetime.now(UTC)
            processing_time = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"[Processor] Document processing failed: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                document_id=document_id,
                chunk_count=0,
                error=str(e),
                processing_time_ms=processing_time,
            )

    async def delete_document(
        self,
        document_id: str,
        collection_name: str,
    ) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID
            collection_name: Qdrant collection name (from KnowledgeBase.collection_name)

        Returns:
            Number of chunks deleted
        """
        return await self.vector_store.delete_document_chunks(collection_name, document_id)

    @staticmethod
    def compute_content_hash(content: bytes) -> str:
        """Compute SHA-256 hash for content deduplication."""
        return hashlib.sha256(content).hexdigest()


# Singleton instance
_processor: DocumentProcessor | None = None


async def get_processor() -> DocumentProcessor:
    """Get or create the global DocumentProcessor instance."""
    global _processor

    if _processor is None:
        vector_store = get_vector_store()
        embedder = await get_embedder()
        _processor = DocumentProcessor(vector_store, embedder)

    return _processor
