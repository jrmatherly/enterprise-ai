"""Authentication middleware for FastAPI.

Supports multiple authentication methods (in priority order):
1. X-Dev-Bypass header (development only, requires explicit opt-in)
2. Bearer JWT token (from better-auth or EntraID)
3. better-auth session cookies (browser requests)

SECURITY NOTE: Dev bypass requires BOTH:
  - ENVIRONMENT=development
  - DEV_BYPASS_ENABLED=true
This prevents accidental bypass in misconfigured environments.
"""

import logging
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.auth.better_auth import (
    get_bearer_token_from_header,
    get_session_token_from_cookies,
    validate_jwt_token,
)
from src.auth.oidc import OIDCValidationError, UserClaims, validate_token
from src.core.config import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health/live",
    "/health/ready",
    "/health/startup",
    "/metrics",
}


def is_public_path(path: str) -> bool:
    """Check if a path is public (no auth required)."""
    # Exact matches
    if path in PUBLIC_PATHS:
        return True

    # Prefix matches for static assets, etc.
    public_prefixes = ("/static/", "/assets/")
    return any(path.startswith(prefix) for prefix in public_prefixes)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens and sets user context.

    Authentication methods (checked in order):
    1. X-Dev-Bypass header (development only) - immediate dev user
    2. Authorization: Bearer <token> - JWT from better-auth or EntraID
    3. better-auth session cookie - for browser requests

    For authenticated requests, sets request.state.user with UserClaims.
    For public paths, skips authentication.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through auth middleware."""
        settings = get_settings()

        # Skip auth for public paths
        if is_public_path(request.url.path):
            return await call_next(request)

        # 1. Check for explicit dev bypass header (requires BOTH conditions)
        # SECURITY: This is a defense-in-depth approach - both must be true:
        #   - environment == "development" (prevent prod bypass)
        #   - dev_bypass_enabled == True (explicit opt-in required)
        dev_bypass_allowed = (
            settings.environment == "development"
            and settings.dev_bypass_enabled is True  # Explicit True check, not truthy
        )

        if dev_bypass_allowed and request.headers.get("X-Dev-Bypass") == "true":
            dev_user = UserClaims(
                sub="00000000-0000-0000-0000-000000000001",
                email="dev@example.com",
                name="Developer",
                roles=["OrgAdmin"],
                tenant_id="00000000-0000-0000-0000-000000000000",
                groups=[],
                raw_claims={},
            )
            # AUDIT: Log all dev bypass usage for security review
            logger.warning(
                "DEV BYPASS ACTIVATED - request authenticated via X-Dev-Bypass header",
                extra={
                    "security_event": "dev_bypass",
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            request.state.user = dev_user
            return await call_next(request)

        # 2. Try Bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        bearer_token = get_bearer_token_from_header(auth_header)

        if bearer_token:
            # First try better-auth JWT validation via JWKS
            result = await validate_jwt_token(bearer_token)
            if result:
                _session, user = result
                request.state.user = UserClaims(
                    sub=user.id,
                    email=user.email,
                    name=user.name,
                    roles=["User"],
                    tenant_id=user.tenant_id or "default",
                    groups=[],
                    raw_claims={
                        "department": user.department,
                        "job_title": user.job_title,
                        "email_verified": user.email_verified,
                    },
                )
                return await call_next(request)

            # Fall back to EntraID JWT validation
            try:
                user_claims = await validate_token(bearer_token)
                request.state.user = user_claims
                return await call_next(request)
            except OIDCValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e),
                    headers={"WWW-Authenticate": "Bearer"},
                ) from None

        # 3. Try better-auth session cookie (browser requests)
        # Note: For API calls, prefer using JWT via Authorization header
        cookies = dict(request.cookies)
        session_token = get_session_token_from_cookies(cookies)

        if session_token:
            # Session tokens may be JWTs (from cookie cache) or raw tokens
            # Try JWT validation first
            result = await validate_jwt_token(session_token)
            if result:
                _session, user = result
                request.state.user = UserClaims(
                    sub=user.id,
                    email=user.email,
                    name=user.name,
                    roles=["User"],
                    tenant_id=user.tenant_id or "default",
                    groups=[],
                    raw_claims={
                        "department": user.department,
                        "job_title": user.job_title,
                        "email_verified": user.email_verified,
                    },
                )
                return await call_next(request)

        # SECURITY: No silent fallback - all requests must authenticate explicitly.
        # In dev mode, use X-Dev-Bypass header if DEV_BYPASS_ENABLED=true.
        # This prevents accidental privilege escalation from misconfiguration.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization header or session cookie.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


async def get_current_user(request: Request) -> UserClaims:
    """FastAPI dependency to get the current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: UserClaims = Depends(get_current_user)):
            return {"user_id": user.sub}
    """
    user = getattr(request.state, "user", None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(request: Request) -> UserClaims | None:
    """FastAPI dependency to get the current user if authenticated.

    Returns None if not authenticated (for optional auth endpoints).
    """
    return getattr(request.state, "user", None)
