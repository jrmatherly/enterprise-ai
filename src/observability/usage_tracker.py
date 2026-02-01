"""LLM usage tracking for FinOps and cost attribution.

Tracks token usage, costs, and latency metrics for:
- Cost attribution per tenant
- Showback/chargeback reporting
- Performance monitoring
- Budget enforcement

Adapted from Azure AI-Gateway FinOps patterns.
See: MICROSOFT-REPOS-ANALYSIS.md for source patterns.
"""

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Optional

from langfuse import Langfuse
from prometheus_client import Counter, Histogram, Gauge


# Prometheus Metrics
TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "Total tokens consumed",
    ["tenant_id", "model", "token_type"]  # token_type: input, output
)

COST_TOTAL = Counter(
    "ai_cost_usd_total",
    "Total cost in USD",
    ["tenant_id", "model"]
)

REQUEST_LATENCY = Histogram(
    "ai_request_duration_seconds",
    "Request latency in seconds",
    ["tenant_id", "model", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

CACHE_HIT_TOTAL = Counter(
    "ai_cache_hits_total",
    "Total cache hits",
    ["tenant_id", "model"]
)

CACHE_MISS_TOTAL = Counter(
    "ai_cache_misses_total",
    "Total cache misses",
    ["tenant_id", "model"]
)

ACTIVE_REQUESTS = Gauge(
    "ai_active_requests",
    "Currently active LLM requests",
    ["model"]
)


@dataclass
class ModelPricing:
    """Pricing per 1K tokens for a model."""
    input_per_1k: float
    output_per_1k: float


# Model pricing (as of 2026-01)
MODEL_PRICING: dict[str, ModelPricing] = {
    # Azure OpenAI
    "gpt-4o": ModelPricing(input_per_1k=0.0025, output_per_1k=0.01),
    "gpt-4o-mini": ModelPricing(input_per_1k=0.00015, output_per_1k=0.0006),
    "gpt-4-turbo": ModelPricing(input_per_1k=0.01, output_per_1k=0.03),
    "gpt-3.5-turbo": ModelPricing(input_per_1k=0.0005, output_per_1k=0.0015),
    
    # Claude via Azure
    "claude-3-5-sonnet": ModelPricing(input_per_1k=0.003, output_per_1k=0.015),
    "claude-3-haiku": ModelPricing(input_per_1k=0.00025, output_per_1k=0.00125),
    
    # Embeddings
    "text-embedding-3-small": ModelPricing(input_per_1k=0.00002, output_per_1k=0.0),
    "text-embedding-3-large": ModelPricing(input_per_1k=0.00013, output_per_1k=0.0),
}


@dataclass
class UsageRecord:
    """Record of a single LLM usage event."""
    tenant_id: str
    user_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    cache_hit: bool
    trace_id: str
    timestamp: datetime


class UsageTracker:
    """Track LLM usage for FinOps and observability.
    
    Integrates with:
    - Prometheus for metrics
    - Langfuse for detailed tracing
    - Internal storage for reporting
    """
    
    def __init__(
        self,
        langfuse: Optional[Langfuse] = None,
        custom_pricing: Optional[dict[str, ModelPricing]] = None
    ):
        self.langfuse = langfuse
        self.pricing = {**MODEL_PRICING, **(custom_pricing or {})}
    
    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate cost in USD for token usage."""
        pricing = self.pricing.get(model)
        
        if not pricing:
            # Unknown model, estimate based on gpt-4o pricing
            pricing = self.pricing["gpt-4o"]
        
        input_cost = (prompt_tokens / 1000) * pricing.input_per_1k
        output_cost = (completion_tokens / 1000) * pricing.output_per_1k
        
        return input_cost + output_cost
    
    async def track(
        self,
        tenant_id: str,
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        trace_id: str,
        cache_hit: bool = False,
        metadata: Optional[dict] = None
    ) -> UsageRecord:
        """Track a usage event and emit metrics.
        
        Args:
            tenant_id: Tenant identifier for cost attribution
            user_id: User who made the request
            model: Model name/deployment used
            prompt_tokens: Input token count
            completion_tokens: Output token count
            latency_ms: Request latency in milliseconds
            trace_id: Distributed trace ID
            cache_hit: Whether response came from cache
            metadata: Additional context
            
        Returns:
            UsageRecord with calculated cost
        """
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        # Prometheus metrics
        TOKENS_TOTAL.labels(tenant_id, model, "input").inc(prompt_tokens)
        TOKENS_TOTAL.labels(tenant_id, model, "output").inc(completion_tokens)
        COST_TOTAL.labels(tenant_id, model).inc(cost_usd)
        REQUEST_LATENCY.labels(tenant_id, model, "chat").observe(latency_ms / 1000)
        
        if cache_hit:
            CACHE_HIT_TOTAL.labels(tenant_id, model).inc()
        else:
            CACHE_MISS_TOTAL.labels(tenant_id, model).inc()
        
        # Langfuse trace
        if self.langfuse:
            self.langfuse.generation(
                trace_id=trace_id,
                name="llm_call",
                model=model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                metadata={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "cache_hit": cache_hit,
                    **(metadata or {})
                }
            )
        
        return UsageRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            cache_hit=cache_hit,
            trace_id=trace_id,
            timestamp=datetime.utcnow()
        )
    
    @asynccontextmanager
    async def track_request(
        self,
        model: str,
        tenant_id: Optional[str] = None
    ) -> AsyncGenerator[None, None]:
        """Context manager to track request duration.
        
        Usage:
            async with tracker.track_request("gpt-4o", "tenant-123"):
                response = await call_llm(...)
        """
        ACTIVE_REQUESTS.labels(model).inc()
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            ACTIVE_REQUESTS.labels(model).dec()
            
            if tenant_id:
                REQUEST_LATENCY.labels(tenant_id, model, "chat").observe(duration)


class TenantBudgetTracker:
    """Track and enforce per-tenant budgets.
    
    Integrates with rate limiting to enforce budget caps.
    """
    
    def __init__(self, redis):
        self.redis = redis
    
    async def get_monthly_usage(self, tenant_id: str) -> dict:
        """Get current month's usage for a tenant."""
        month_key = datetime.utcnow().strftime("%Y%m")
        
        keys = [
            f"budget:{tenant_id}:{month_key}:tokens",
            f"budget:{tenant_id}:{month_key}:cost",
            f"budget:{tenant_id}:{month_key}:requests"
        ]
        
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(key)
        
        values = await pipe.execute()
        
        return {
            "month": month_key,
            "tenant_id": tenant_id,
            "total_tokens": int(values[0] or 0),
            "total_cost_usd": float(values[1] or 0),
            "total_requests": int(values[2] or 0)
        }
    
    async def record_usage(
        self,
        tenant_id: str,
        tokens: int,
        cost_usd: float
    ) -> None:
        """Record usage against monthly budget."""
        month_key = datetime.utcnow().strftime("%Y%m")
        
        pipe = self.redis.pipeline()
        pipe.incrbyfloat(f"budget:{tenant_id}:{month_key}:tokens", tokens)
        pipe.incrbyfloat(f"budget:{tenant_id}:{month_key}:cost", cost_usd)
        pipe.incr(f"budget:{tenant_id}:{month_key}:requests")
        
        # Set expiry for next month + buffer
        for key in [
            f"budget:{tenant_id}:{month_key}:tokens",
            f"budget:{tenant_id}:{month_key}:cost",
            f"budget:{tenant_id}:{month_key}:requests"
        ]:
            pipe.expire(key, 60 * 60 * 24 * 35)  # 35 days
        
        await pipe.execute()
    
    async def check_budget(
        self,
        tenant_id: str,
        budget_limit_usd: float
    ) -> tuple[bool, float]:
        """Check if tenant is within budget.
        
        Returns:
            Tuple of (within_budget, remaining_budget_usd)
        """
        usage = await self.get_monthly_usage(tenant_id)
        remaining = budget_limit_usd - usage["total_cost_usd"]
        
        return remaining > 0, max(0, remaining)
