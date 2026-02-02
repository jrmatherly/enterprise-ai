"""Semantic caching for LLM responses.

Caches responses based on semantic similarity of prompts to reduce
LLM costs and latency for similar queries.

Adapted from Azure AI-Gateway semantic-caching patterns.
See: MICROSOFT-REPOS-ANALYSIS.md for source patterns.
"""

import hashlib
import json
from datetime import UTC, datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from redis.asyncio import Redis


class SemanticCache:
    """Cache LLM responses based on semantic similarity of prompts.

    Uses Qdrant for embedding similarity search and Redis for response storage.

    Flow:
    1. Generate embedding for user prompt
    2. Search Qdrant for similar cached prompts
    3. If similarity > threshold, return cached response from Redis
    4. Otherwise, call LLM and cache the new response
    """

    def __init__(
        self,
        qdrant: AsyncQdrantClient,
        redis: Redis,
        collection_name: str = "prompt_cache",
        similarity_threshold: float = 0.95,
        default_ttl: int = 3600,
        embedding_size: int = 1536,  # text-embedding-3-small
    ):
        self.qdrant = qdrant
        self.redis = redis
        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl
        self.embedding_size = embedding_size

    async def initialize(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        collections = await self.qdrant.get_collections()
        exists = any(c.name == self.collection_name for c in collections.collections)

        if not exists:
            await self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_size, distance=Distance.COSINE),
            )

    async def get(
        self, prompt: str, embedding: list[float], tenant_id: str, model: str | None = None
    ) -> dict | None:
        """Look up cached response by semantic similarity.

        Args:
            prompt: User's prompt text (for logging/debugging)
            embedding: Embedding vector of the prompt
            tenant_id: Tenant ID for isolation
            model: Optional model filter

        Returns:
            Cached response dict if found, None otherwise
        """
        # Build filter for tenant isolation
        filter_conditions = [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        if model:
            filter_conditions.append(FieldCondition(key="model", match=MatchValue(value=model)))

        results = await self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            query_filter=Filter(must=filter_conditions),
            limit=1,
            score_threshold=self.similarity_threshold,
        )

        if not results:
            return None

        top_result = results[0]

        if top_result.score < self.similarity_threshold:
            return None

        # Get response from Redis
        cache_key = top_result.payload.get("cache_key")
        if not cache_key:
            return None

        cached_json = await self.redis.get(f"llm_cache:{cache_key}")

        if not cached_json:
            # Cache expired in Redis, clean up Qdrant
            await self._delete_point(top_result.id)
            return None

        cached = json.loads(cached_json)
        cached["_cache_hit"] = True
        cached["_similarity_score"] = top_result.score

        return cached

    async def set(
        self,
        prompt: str,
        embedding: list[float],
        response: dict,
        tenant_id: str,
        model: str,
        ttl: int | None = None,
    ) -> str:
        """Cache a response with its embedding for semantic lookup.

        Args:
            prompt: User's prompt text
            embedding: Embedding vector of the prompt
            response: LLM response to cache
            tenant_id: Tenant ID for isolation
            model: Model used for the response
            ttl: Time-to-live in seconds (default: self.default_ttl)

        Returns:
            Cache key for the stored response
        """
        ttl = ttl or self.default_ttl

        # Generate cache key from prompt hash
        cache_key = hashlib.sha256(f"{tenant_id}:{model}:{prompt}".encode()).hexdigest()[:16]

        # Store embedding in Qdrant
        point = PointStruct(
            id=cache_key,
            vector=embedding,
            payload={
                "cache_key": cache_key,
                "tenant_id": tenant_id,
                "model": model,
                "prompt_preview": prompt[:100],
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        await self.qdrant.upsert(collection_name=self.collection_name, points=[point])

        # Store response in Redis with TTL
        response_data = {**response, "_cached_at": datetime.now(UTC).isoformat(), "_model": model}

        await self.redis.setex(f"llm_cache:{cache_key}", ttl, json.dumps(response_data))

        return cache_key

    async def invalidate(self, cache_key: str) -> bool:
        """Invalidate a cached response.

        Args:
            cache_key: The cache key to invalidate

        Returns:
            True if the key existed and was deleted
        """
        # Delete from Redis
        redis_deleted = await self.redis.delete(f"llm_cache:{cache_key}")

        # Delete from Qdrant
        await self._delete_point(cache_key)

        return bool(redis_deleted)

    async def invalidate_tenant(self, tenant_id: str) -> int:
        """Invalidate all cached responses for a tenant.

        Args:
            tenant_id: Tenant ID to invalidate

        Returns:
            Number of entries invalidated
        """
        # Get all cache keys for tenant from Qdrant
        results = await self.qdrant.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
            ),
            limit=1000,
            with_payload=True,
        )

        points, _ = results
        count = 0

        for point in points:
            cache_key = point.payload.get("cache_key")
            if cache_key:
                await self.redis.delete(f"llm_cache:{cache_key}")
                count += 1

        # Delete all points for tenant
        await self.qdrant.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
            ),
        )

        return count

    async def _delete_point(self, point_id: str) -> None:
        """Delete a single point from Qdrant."""
        await self.qdrant.delete(collection_name=self.collection_name, points_selector=[point_id])

    async def get_stats(self, tenant_id: str | None = None) -> dict:
        """Get cache statistics.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            Cache statistics dict
        """
        collection_info = await self.qdrant.get_collection(self.collection_name)

        stats = {
            "total_cached_prompts": collection_info.points_count,
            "collection_name": self.collection_name,
            "similarity_threshold": self.similarity_threshold,
        }

        if tenant_id:
            # Count tenant-specific entries
            results = await self.qdrant.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                ),
            )
            stats["tenant_cached_prompts"] = results.count

        return stats
