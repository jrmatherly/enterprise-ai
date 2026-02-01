"""Token-based rate limiting using Redis.

Adapted from Azure AI-Gateway patterns for on-premise deployment.
See: MICROSOFT-REPOS-ANALYSIS.md for source patterns.
"""

from datetime import datetime
from typing import Optional

from redis.asyncio import Redis


class TokenRateLimiter:
    """Per-tenant token rate limiting with sliding window.
    
    Implements TPM (tokens per minute) limiting similar to
    Azure API Management's azure-openai-token-limit policy.
    """
    
    def __init__(
        self,
        redis: Redis,
        default_tpm: int = 100000,
        window_seconds: int = 60
    ):
        self.redis = redis
        self.default_tpm = default_tpm
        self.window_seconds = window_seconds
    
    async def check_and_consume(
        self,
        tenant_id: str,
        tokens: int
    ) -> tuple[bool, int, int]:
        """Check if tokens can be consumed and consume them.
        
        Args:
            tenant_id: Unique tenant identifier
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, remaining_tokens, reset_seconds)
        """
        now = datetime.utcnow()
        minute_key = f"tpm:{tenant_id}:{now.strftime('%Y%m%d%H%M')}"
        
        # Get current usage and limit in pipeline
        pipe = self.redis.pipeline()
        pipe.get(minute_key)
        pipe.hget("tenant:limits:tpm", tenant_id)
        current_raw, limit_raw = await pipe.execute()
        
        current = int(current_raw) if current_raw else 0
        limit = int(limit_raw) if limit_raw else self.default_tpm
        
        # Check if within limit
        if current + tokens > limit:
            remaining = max(0, limit - current)
            reset_seconds = self.window_seconds - now.second
            return False, remaining, reset_seconds
        
        # Consume tokens atomically
        pipe = self.redis.pipeline()
        pipe.incrby(minute_key, tokens)
        pipe.expire(minute_key, self.window_seconds + 10)  # Small buffer
        new_total, _ = await pipe.execute()
        
        remaining = max(0, limit - new_total)
        reset_seconds = self.window_seconds - now.second
        
        return True, remaining, reset_seconds
    
    async def get_usage(self, tenant_id: str) -> dict:
        """Get current usage stats for a tenant."""
        now = datetime.utcnow()
        minute_key = f"tpm:{tenant_id}:{now.strftime('%Y%m%d%H%M')}"
        
        pipe = self.redis.pipeline()
        pipe.get(minute_key)
        pipe.hget("tenant:limits:tpm", tenant_id)
        current_raw, limit_raw = await pipe.execute()
        
        current = int(current_raw) if current_raw else 0
        limit = int(limit_raw) if limit_raw else self.default_tpm
        
        return {
            "tenant_id": tenant_id,
            "current_tokens": current,
            "limit_tokens": limit,
            "remaining_tokens": max(0, limit - current),
            "reset_at": now.replace(second=0, microsecond=0).isoformat() + "Z"
        }
    
    async def set_tenant_limit(self, tenant_id: str, tpm_limit: int) -> None:
        """Set or update a tenant's TPM limit."""
        await self.redis.hset("tenant:limits:tpm", tenant_id, str(tpm_limit))
    
    async def get_tenant_limit(self, tenant_id: str) -> int:
        """Get a tenant's TPM limit."""
        limit_raw = await self.redis.hget("tenant:limits:tpm", tenant_id)
        return int(limit_raw) if limit_raw else self.default_tpm


class RequestRateLimiter:
    """Per-tenant request rate limiting (RPM).
    
    Simpler than token limiting - just counts requests per minute.
    """
    
    def __init__(
        self,
        redis: Redis,
        default_rpm: int = 60,
        window_seconds: int = 60
    ):
        self.redis = redis
        self.default_rpm = default_rpm
        self.window_seconds = window_seconds
    
    async def check_and_increment(self, tenant_id: str) -> tuple[bool, int]:
        """Check if request is allowed and increment counter.
        
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        now = datetime.utcnow()
        minute_key = f"rpm:{tenant_id}:{now.strftime('%Y%m%d%H%M')}"
        
        # Get limit
        limit_raw = await self.redis.hget("tenant:limits:rpm", tenant_id)
        limit = int(limit_raw) if limit_raw else self.default_rpm
        
        # Increment and check
        pipe = self.redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, self.window_seconds + 10)
        current, _ = await pipe.execute()
        
        allowed = current <= limit
        remaining = max(0, limit - current)
        
        return allowed, remaining
