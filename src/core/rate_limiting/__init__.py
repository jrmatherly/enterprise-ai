"""Rate limiting package.

Provides token and request rate limiting using Redis.
"""

from typing import Optional

import redis.asyncio as redis

from src.core.config import get_settings
from src.core.rate_limiting.token_limiter import (
    TokenRateLimiter,
    RequestRateLimiter,
)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit_type: str, limit: int, remaining: int, retry_after: int):
        self.limit_type = limit_type
        self.limit = limit
        self.remaining = remaining
        self.retry_after = retry_after
        super().__init__(f"{limit_type} rate limit exceeded. Retry after {retry_after}s")


class CombinedRateLimiter:
    """Combined TPM and RPM rate limiter.
    
    Wraps TokenRateLimiter and RequestRateLimiter for convenience.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        default_tpm: int = 100000,
        default_rpm: int = 60,
    ):
        self.token_limiter = TokenRateLimiter(redis_client, default_tpm)
        self.request_limiter = RequestRateLimiter(redis_client, default_rpm)
    
    async def check_request_limit(self, tenant_id: str) -> tuple[bool, int]:
        """Check and increment request count. Raises RateLimitExceeded if exceeded."""
        from datetime import datetime
        
        allowed, remaining = await self.request_limiter.check_and_increment(tenant_id)
        
        if not allowed:
            raise RateLimitExceeded(
                limit_type="RPM",
                limit=self.request_limiter.default_rpm,
                remaining=0,
                retry_after=60 - datetime.utcnow().second,
            )
        
        return allowed, remaining
    
    async def check_and_consume_tokens(
        self,
        tenant_id: str,
        tokens: int,
    ) -> tuple[bool, int, int]:
        """Check and consume tokens. Raises RateLimitExceeded if exceeded."""
        allowed, remaining, reset_seconds = await self.token_limiter.check_and_consume(
            tenant_id, tokens
        )
        
        if not allowed:
            raise RateLimitExceeded(
                limit_type="TPM",
                limit=await self.token_limiter.get_tenant_limit(tenant_id),
                remaining=remaining,
                retry_after=reset_seconds,
            )
        
        return allowed, remaining, reset_seconds
    
    async def record_tokens(self, tenant_id: str, tokens: int) -> tuple[int, int]:
        """Record token usage after LLM response."""
        allowed, remaining, _ = await self.token_limiter.check_and_consume(tenant_id, tokens)
        limit = await self.token_limiter.get_tenant_limit(tenant_id)
        current = limit - remaining
        return current, limit
    
    async def get_usage(self, tenant_id: str) -> dict:
        """Get current usage stats for a tenant."""
        token_usage = await self.token_limiter.get_usage(tenant_id)
        
        # Get request usage too
        from datetime import datetime
        now = datetime.utcnow()
        minute_key = f"rpm:{tenant_id}:{now.strftime('%Y%m%d%H%M')}"
        
        current_requests = await self.request_limiter.redis.get(minute_key)
        current_requests = int(current_requests) if current_requests else 0
        rpm_limit = self.request_limiter.default_rpm
        
        return {
            "tokens": {
                "used": token_usage["current_tokens"],
                "limit": token_usage["limit_tokens"],
                "remaining": token_usage["remaining_tokens"],
            },
            "requests": {
                "used": current_requests,
                "limit": rpm_limit,
                "remaining": max(0, rpm_limit - current_requests),
            },
        }


# Global rate limiter instance
_rate_limiter: Optional[CombinedRateLimiter] = None


async def get_rate_limiter() -> CombinedRateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        settings = get_settings()
        redis_client = redis.from_url(settings.redis_url)
        _rate_limiter = CombinedRateLimiter(
            redis_client=redis_client,
            default_tpm=settings.default_tpm_limit,
            default_rpm=settings.default_rpm_limit,
        )
    
    return _rate_limiter


__all__ = [
    "TokenRateLimiter",
    "RequestRateLimiter", 
    "CombinedRateLimiter",
    "RateLimitExceeded",
    "get_rate_limiter",
]
