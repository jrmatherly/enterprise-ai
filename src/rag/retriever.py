"""RAG Retriever - semantic search with access control.

Combines embedding and vector search for document retrieval.
"""

from dataclasses import dataclass
from typing import Optional

from src.rag.vector_store import VectorStore, get_vector_store
from src.rag.embedder import Embedder, get_embedder


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
    with per-user ACL filtering.
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
    
    async def retrieve(
        self,
        query: str,
        knowledge_base_ids: list[str],
        user_id: str,
        tenant_id: str,
        group_ids: Optional[list[str]] = None,
        limit: int = 5,
        score_threshold: float = 0.5,
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
            
        Returns:
            List of relevant chunks, sorted by score
        """
        if not query.strip():
            return []
        
        if not knowledge_base_ids:
            return []
        
        # Generate query embedding
        query_vector = await self.embedder.embed_query(query)
        
        # Search each knowledge base
        all_results = []
        
        for kb_id in knowledge_base_ids:
            collection_name = f"kb_{kb_id}"
            
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
                    all_results.append(RetrievedChunk(
                        id=r["id"],
                        text=r["text"],
                        score=r["score"],
                        document_id=r["document_id"],
                        chunk_index=r["chunk_index"],
                        metadata=r.get("metadata", {}),
                    ))
                    
            except Exception as e:
                # Log error but continue with other KBs
                print(f"Error searching {collection_name}: {e}")
                continue
        
        # Sort by score and limit total results
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:limit * 2]  # Return up to 2x the per-KB limit
    
    def format_context(
        self,
        chunks: list[RetrievedChunk],
        max_chars: int = 8000,
    ) -> str:
        """Format retrieved chunks as context for the LLM.
        
        Args:
            chunks: Retrieved chunks
            max_chars: Maximum context length
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = f"[Source {i}]\n{chunk.text}\n"
            
            if total_chars + len(chunk_text) > max_chars:
                break
                
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n".join(context_parts)
    
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
_retriever: Optional[Retriever] = None


async def get_retriever() -> Retriever:
    """Get or create the global Retriever instance."""
    global _retriever
    
    if _retriever is None:
        vector_store = get_vector_store()
        embedder = await get_embedder()
        _retriever = Retriever(vector_store, embedder)
    
    return _retriever
