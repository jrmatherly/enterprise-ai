"""Embedding service using Azure OpenAI.

Generates vector embeddings for text chunks and queries.
"""

from typing import Optional
import asyncio

from openai import AsyncAzureOpenAI

from src.core.config import get_settings


class Embedder:
    """Azure OpenAI embedding service.
    
    Uses text-embedding-3-small by default for cost-effective embeddings.
    """
    
    DEFAULT_MODEL = "text-embedding-3-small"
    BATCH_SIZE = 100  # Azure limit per request
    
    def __init__(
        self,
        client: AsyncAzureOpenAI,
        model: str = DEFAULT_MODEL,
    ):
        self.client = client
        self.model = model
    
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        # Clean text
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text")
        
        response = await self.client.embeddings.create(
            input=text,
            model=self.model,
        )
        
        return response.data[0].embedding
    
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Clean and filter empty texts
        cleaned = [(i, t.strip()) for i, t in enumerate(texts)]
        non_empty = [(i, t) for i, t in cleaned if t]
        
        if not non_empty:
            raise ValueError("All texts are empty")
        
        all_embeddings = [None] * len(texts)
        
        # Process in batches
        for batch_start in range(0, len(non_empty), self.BATCH_SIZE):
            batch = non_empty[batch_start:batch_start + self.BATCH_SIZE]
            batch_texts = [t for _, t in batch]
            
            response = await self.client.embeddings.create(
                input=batch_texts,
                model=self.model,
            )
            
            # Map embeddings back to original indices
            for j, (original_idx, _) in enumerate(batch):
                all_embeddings[original_idx] = response.data[j].embedding
        
        # Fill empty text positions with zero vectors
        zero_vector = [0.0] * 1536
        for i in range(len(all_embeddings)):
            if all_embeddings[i] is None:
                all_embeddings[i] = zero_vector
        
        return all_embeddings
    
    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query.
        
        Alias for embed_text, but can be extended for query-specific processing.
        """
        return await self.embed_text(query)


# Singleton instance
_embedder: Optional[Embedder] = None


async def get_embedder() -> Embedder:
    """Get or create the global Embedder instance."""
    global _embedder
    
    if _embedder is None:
        settings = get_settings()
        
        # Get embedding endpoint (use eastus by default)
        endpoint = settings.azure_ai_eastus_endpoint
        api_key = settings.azure_ai_eastus_api_key
        
        if not endpoint or not api_key:
            # Try eastus2 as fallback
            endpoint = settings.azure_ai_eastus2_endpoint
            api_key = settings.azure_ai_eastus2_api_key
        
        if not endpoint or not api_key:
            raise RuntimeError(
                "No Azure OpenAI endpoints configured. "
                "Set AZURE_AI_EASTUS_ENDPOINT and AZURE_AI_EASTUS_API_KEY"
            )
        
        client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=endpoint,
        )
        
        _embedder = Embedder(
            client=client,
            model=settings.embedding_model,
        )
    
    return _embedder
