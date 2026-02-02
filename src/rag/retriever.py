"""RAG Retriever - semantic search with access control.

Combines embedding and vector search for document retrieval.
Includes optional semantic caching.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.core.config import get_settings
from src.db.database import async_session_maker
from src.db.models import KnowledgeBase
from src.rag.embedder import Embedder, get_embedder
from src.rag.vector_store import VectorStore, get_vector_store

if TYPE_CHECKING:
    from src.rag.semantic_cache import SemanticCache

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search."""

    id: str
    text: str
    score: float
    document_id: str
    chunk_index: int
    metadata: dict


class Retriever:
    """Semantic retrieval with access control.

    Coordinates embedding generation and vector search
    with per-user ACL filtering. Optionally uses semantic caching.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        cache: "SemanticCache | None" = None,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.cache = cache
        self._cache_enabled = get_settings().semantic_cache_enabled

    async def retrieve(
        self,
        query: str,
        knowledge_base_ids: list[str],
        user_id: str,
        tenant_id: str,
        group_ids: list[str] | None = None,
        limit: int = 5,
        score_threshold: float = 0.2,
        use_cache: bool = True,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query.

        Args:
            query: User's search query
            knowledge_base_ids: Knowledge bases to search
            user_id: Current user ID for ACL
            tenant_id: Current tenant ID
            group_ids: User's group memberships
            limit: Max chunks per knowledge base
            score_threshold: Minimum similarity score
            use_cache: Whether to use semantic cache

        Returns:
            List of relevant chunks, sorted by score
        """
        if not query.strip():
            return []

        if not knowledge_base_ids:
            return []

        # Check semantic cache first
        f"{','.join(sorted(knowledge_base_ids))}:{user_id}"
        if use_cache and self._cache_enabled and self.cache:
            for kb_id in knowledge_base_ids:
                cached = await self.cache.get(query, kb_id)
                if cached:
                    # Convert cached results back to RetrievedChunk
                    return [
                        RetrievedChunk(
                            id=r.get("id", ""),
                            text=r.get("text", ""),
                            score=r.get("score", 0.0),
                            document_id=r.get("document_id", ""),
                            chunk_index=r.get("chunk_index", 0),
                            metadata=r.get("metadata", {}),
                        )
                        for r in cached
                    ]

        # Generate query embedding
        query_vector = await self.embedder.embed_query(query)

        # Look up collection names from database
        kb_id_to_collection: dict[str, str] = {}
        async with async_session_maker() as db:
            query_stmt = select(KnowledgeBase.id, KnowledgeBase.collection_name).where(
                KnowledgeBase.id.in_(knowledge_base_ids)
            )
            result = await db.execute(query_stmt)
            for kb_id, collection_name in result.all():
                kb_id_to_collection[str(kb_id)] = collection_name

        # Search each knowledge base
        all_results = []

        for kb_id in knowledge_base_ids:
            collection_name = kb_id_to_collection.get(str(kb_id))
            if not collection_name:
                continue

            try:
                results = await self.vector_store.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    user_id=user_id,
                    group_ids=group_ids,
                    tenant_id=tenant_id,
                    score_threshold=score_threshold,
                )

                # Convert to RetrievedChunk objects
                for r in results:
                    all_results.append(
                        RetrievedChunk(
                            id=r["id"],
                            text=r["text"],
                            score=r["score"],
                            document_id=r["document_id"],
                            chunk_index=r["chunk_index"],
                            metadata=r.get("metadata", {}),
                        )
                    )

            except Exception as e:
                # Log error but continue with other KBs
                logger.exception("Error searching KB %s: %s", kb_id, e)
                continue

        # Sort by score and limit total results
        all_results.sort(key=lambda x: x.score, reverse=True)
        final_results = all_results[: limit * 2]  # Return up to 2x the per-KB limit

        # Cache the results
        if use_cache and self._cache_enabled and self.cache and final_results:
            for kb_id in knowledge_base_ids:
                await self.cache.set(
                    query=query,
                    kb_id=kb_id,
                    results=[
                        {
                            "id": r.id,
                            "text": r.text,
                            "score": r.score,
                            "document_id": r.document_id,
                            "chunk_index": r.chunk_index,
                            "metadata": r.metadata,
                        }
                        for r in final_results
                    ],
                    query_embedding=query_vector,
                )

        return final_results

    def format_context(
        self,
        chunks: list[RetrievedChunk],
        max_chars: int = 8000,
    ) -> str:
        """Format retrieved chunks as context for the LLM with citations.

        Args:
            chunks: Retrieved chunks
            max_chars: Maximum context length

        Returns:
            Formatted context string with source references
        """
        if not chunks:
            return ""

        context_parts = []
        citation_refs = []
        total_chars = 0

        for i, chunk in enumerate(chunks, 1):
            # Extract citation metadata
            filename = chunk.metadata.get("filename", "Unknown Document")
            chunk_idx = chunk.chunk_index

            # Build citation reference
            citation_refs.append(f"[{i}] {filename} (Section {chunk_idx + 1})")

            # Format chunk with source marker
            chunk_text = f"[{i}] {chunk.text}\n"

            if total_chars + len(chunk_text) > max_chars:
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        # Build final context with citation legend at the end
        context = "\n".join(context_parts)
        citations = "\n".join(citation_refs[: len(context_parts)])

        return f"{context}\n\n---\nSources:\n{citations}"

    def build_rag_prompt(
        self,
        user_message: str,
        context: str,
    ) -> str:
        """Build a RAG-enhanced prompt.

        Args:
            user_message: User's original message
            context: Retrieved context

        Returns:
            Enhanced prompt with context
        """
        if not context:
            return user_message

        return f"""Use the following context to help answer the question.
If the context doesn't contain relevant information, say so and answer based on your general knowledge.

Context:
{context}

Question: {user_message}"""


# Singleton instance
_retriever: Retriever | None = None


async def get_retriever() -> Retriever:
    """Get or create the global Retriever instance."""
    global _retriever

    if _retriever is None:
        settings = get_settings()
        vector_store = get_vector_store()
        embedder = await get_embedder()

        # Initialize cache if enabled
        cache = None
        if settings.semantic_cache_enabled:
            try:
                from src.rag.semantic_cache import get_semantic_cache

                cache = await get_semantic_cache()
            except Exception as e:
                print(f"Failed to initialize semantic cache: {e}")

        _retriever = Retriever(vector_store, embedder, cache)

    return _retriever
