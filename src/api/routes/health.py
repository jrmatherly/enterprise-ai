"""Health check endpoints for Kubernetes probes."""

from datetime import UTC, datetime

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.core.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    checks: dict | None = None


# Startup state
_startup_complete = False


def set_startup_complete():
    """Mark startup as complete."""
    global _startup_complete
    _startup_complete = True


async def check_redis() -> tuple[bool, str]:
    """Check Redis connectivity."""
    settings = get_settings()
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        await client.aclose()
        return True, "healthy"
    except Exception as e:
        return False, f"unhealthy: {e!s}"


async def check_qdrant() -> tuple[bool, str]:
    """Check Qdrant connectivity."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.qdrant_url}/readyz", timeout=5.0)
            if response.status_code == 200:
                return True, "healthy"
            return False, f"unhealthy: status {response.status_code}"
    except Exception as e:
        return False, f"unhealthy: {e!s}"


async def check_langfuse() -> tuple[bool, str]:
    """Check Langfuse connectivity."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.langfuse_host}/api/public/health", timeout=5.0)
            if response.status_code == 200:
                return True, "healthy"
            return False, f"unhealthy: status {response.status_code}"
    except Exception as e:
        return False, f"unhealthy: {e!s}"


@router.get("/health/live", response_model=HealthResponse)
async def liveness():
    """Kubernetes liveness probe.

    Returns 200 if the process is alive.
    Used to determine if the container should be restarted.
    """
    settings = get_settings()

    return HealthResponse(
        status="alive", timestamp=datetime.now(UTC).isoformat() + "Z", version=settings.app_version
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness():
    """Kubernetes readiness probe.

    Returns 200 if the service is ready to accept traffic.
    Checks critical dependencies.
    """
    settings = get_settings()

    checks = {}
    all_healthy = True

    # Check Redis
    redis_ok, redis_status = await check_redis()
    checks["redis"] = redis_status
    if not redis_ok:
        all_healthy = False

    # Check Qdrant
    qdrant_ok, qdrant_status = await check_qdrant()
    checks["qdrant"] = qdrant_status
    if not qdrant_ok:
        all_healthy = False

    # Check Langfuse (non-critical - service can work without it)
    _langfuse_ok, langfuse_status = await check_langfuse()
    checks["langfuse"] = langfuse_status
    # Don't fail readiness for Langfuse

    if not all_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "checks": checks},
        )

    return HealthResponse(
        status="ready",
        timestamp=datetime.now(UTC).isoformat() + "Z",
        version=settings.app_version,
        checks=checks,
    )


@router.get("/health/startup", response_model=HealthResponse)
async def startup():
    """Kubernetes startup probe.

    Returns 200 once initialization is complete.
    Allows for slow-starting containers.
    """
    settings = get_settings()

    if not _startup_complete:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "starting", "message": "Initialization in progress"},
        )

    return HealthResponse(
        status="started",
        timestamp=datetime.now(UTC).isoformat() + "Z",
        version=settings.app_version,
    )
