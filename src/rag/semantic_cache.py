"""Semantic caching for RAG queries.

Caches query results based on semantic similarity to avoid
redundant embedding/search operations.
"""

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import redis.asyncio as redis
import numpy as np

from src.core.config import get_settings
from src.rag.embedder import Embedder, get_embedder


@dataclass
class CacheEntry:
    """A cached query result."""
    query: str
    query_embedding: list[float]
    results: list[dict]
    created_at: str
    hits: int = 0


class SemanticCache:
    """Semantic cache using Redis and embedding similarity.
    
    Stores query embeddings and results in Redis. When a new query
    comes in, computes its embedding and checks if any cached query
    is semantically similar (cosine similarity > threshold).
    
    Cache key structure:
    - sem_cache:{kb_id}:queries -> Hash of query_hash -> CacheEntry JSON
    - sem_cache:{kb_id}:embeddings -> Hash of query_hash -> embedding bytes
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        embedder: Embedder,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        max_entries_per_kb: int = 1000,
    ):
        self.redis = redis_client
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_entries_per_kb = max_entries_per_kb
    
    def _query_key(self, kb_id: str) -> str:
        """Get Redis key for query cache."""
        return f"sem_cache:{kb_id}:queries"
    
    def _embedding_key(self, kb_id: str) -> str:
        """Get Redis key for embeddings."""
        return f"sem_cache:{kb_id}:embeddings"
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for exact query matching."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    
    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot / (norm_a * norm_b))
    
    async def get(
        self,
        query: str,
        kb_id: str,
    ) -> Optional[list[dict]]:
        """Check cache for semantically similar query.
        
        Args:
            query: Search query
            kb_id: Knowledge base ID
            
        Returns:
            Cached results if similar query found, None otherwise
        """
        query_key = self._query_key(kb_id)
        embedding_key = self._embedding_key(kb_id)
        
        # First check for exact match
        query_hash = self._hash_query(query)
        cached = await self.redis.hget(query_key, query_hash)
        
        if cached:
            entry = json.loads(cached)
            # Update hit count
            entry["hits"] = entry.get("hits", 0) + 1
            await self.redis.hset(query_key, query_hash, json.dumps(entry))
            return entry["results"]
        
        # Generate embedding for semantic comparison
        try:
            query_embedding = await self.embedder.embed_query(query)
        except Exception:
            return None
        
        # Get all cached embeddings
        all_embeddings = await self.redis.hgetall(embedding_key)
        
        if not all_embeddings:
            return None
        
        # Find most similar cached query
        best_match = None
        best_similarity = 0.0
        
        for cached_hash, emb_bytes in all_embeddings.items():
            cached_embedding = json.loads(emb_bytes)
            similarity = self._cosine_similarity(query_embedding, cached_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cached_hash.decode() if isinstance(cached_hash, bytes) else cached_hash
        
        # Check if similarity exceeds threshold
        if best_similarity >= self.similarity_threshold and best_match:
            cached = await self.redis.hget(query_key, best_match)
            if cached:
                entry = json.loads(cached)
                # Update hit count
                entry["hits"] = entry.get("hits", 0) + 1
                await self.redis.hset(query_key, best_match, json.dumps(entry))
                return entry["results"]
        
        return None
    
    async def set(
        self,
        query: str,
        kb_id: str,
        results: list[dict],
        query_embedding: Optional[list[float]] = None,
    ) -> None:
        """Cache query results.
        
        Args:
            query: Search query
            kb_id: Knowledge base ID  
            results: Search results to cache
            query_embedding: Pre-computed embedding (optional)
        """
        query_key = self._query_key(kb_id)
        embedding_key = self._embedding_key(kb_id)
        query_hash = self._hash_query(query)
        
        # Get embedding if not provided
        if query_embedding is None:
            try:
                query_embedding = await self.embedder.embed_query(query)
            except Exception:
                return
        
        # Create cache entry
        entry = {
            "query": query,
            "results": results,
            "created_at": datetime.utcnow().isoformat(),
            "hits": 0,
        }
        
        # Store entry and embedding
        await self.redis.hset(query_key, query_hash, json.dumps(entry))
        await self.redis.hset(embedding_key, query_hash, json.dumps(query_embedding))
        
        # Set TTL on the hash keys
        await self.redis.expire(query_key, self.ttl_seconds)
        await self.redis.expire(embedding_key, self.ttl_seconds)
        
        # Enforce max entries limit
        await self._enforce_limit(kb_id)
    
    async def _enforce_limit(self, kb_id: str) -> None:
        """Remove oldest entries if limit exceeded."""
        query_key = self._query_key(kb_id)
        embedding_key = self._embedding_key(kb_id)
        
        count = await self.redis.hlen(query_key)
        
        if count <= self.max_entries_per_kb:
            return
        
        # Get all entries and sort by created_at
        all_entries = await self.redis.hgetall(query_key)
        entries_with_time = []
        
        for hash_key, entry_json in all_entries.items():
            entry = json.loads(entry_json)
            entries_with_time.append((
                hash_key.decode() if isinstance(hash_key, bytes) else hash_key,
                entry.get("created_at", "")
            ))
        
        # Sort by time and remove oldest
        entries_with_time.sort(key=lambda x: x[1])
        to_remove = entries_with_time[:count - self.max_entries_per_kb]
        
        for hash_key, _ in to_remove:
            await self.redis.hdel(query_key, hash_key)
            await self.redis.hdel(embedding_key, hash_key)
    
    async def invalidate(self, kb_id: str) -> None:
        """Invalidate all cache entries for a knowledge base."""
        await self.redis.delete(self._query_key(kb_id))
        await self.redis.delete(self._embedding_key(kb_id))
    
    async def get_stats(self, kb_id: str) -> dict:
        """Get cache statistics for a knowledge base."""
        query_key = self._query_key(kb_id)
        
        count = await self.redis.hlen(query_key)
        
        total_hits = 0
        if count > 0:
            all_entries = await self.redis.hgetall(query_key)
            for entry_json in all_entries.values():
                entry = json.loads(entry_json)
                total_hits += entry.get("hits", 0)
        
        return {
            "kb_id": kb_id,
            "entry_count": count,
            "total_hits": total_hits,
            "max_entries": self.max_entries_per_kb,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold,
        }


# Singleton instance
_semantic_cache: Optional[SemanticCache] = None


async def get_semantic_cache() -> SemanticCache:
    """Get or create the global SemanticCache instance."""
    global _semantic_cache
    
    if _semantic_cache is None:
        settings = get_settings()
        redis_client = redis.from_url(settings.redis_url)
        embedder = await get_embedder()
        
        _semantic_cache = SemanticCache(
            redis_client=redis_client,
            embedder=embedder,
            similarity_threshold=settings.semantic_cache_threshold,
            ttl_seconds=settings.semantic_cache_ttl,
        )
    
    return _semantic_cache
