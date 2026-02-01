"""Authentication middleware for FastAPI.

Supports multiple authentication methods:
1. X-Dev-Bypass header (development only)
2. better-auth session cookies (frontend SSO)
3. Bearer JWT tokens (EntraID direct)
"""

from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.auth.oidc import validate_token, OIDCValidationError, UserClaims
from src.auth.better_auth import validate_session_token, get_session_token_from_cookies
from src.core.config import get_settings


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
    
    For authenticated requests, sets request.state.user with UserClaims.
    For public paths, skips authentication.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through auth middleware."""
        settings = get_settings()
        
        # Skip auth for public paths
        if is_public_path(request.url.path):
            return await call_next(request)
        
        # Dev user for fallback in development mode
        dev_user = UserClaims(
            sub="00000000-0000-0000-0000-000000000001",
            email="dev@example.com",
            name="Developer",
            roles=["OrgAdmin"],
            tenant_id="00000000-0000-0000-0000-000000000000",
            groups=[],
            raw_claims={},
        )
        
        # Check for explicit dev bypass header first (highest priority in dev)
        if settings.environment == "development":
            if request.headers.get("X-Dev-Bypass") == "true":
                request.state.user = dev_user
                return await call_next(request)
        
        # Try better-auth session cookie (from frontend SSO)
        cookies = dict(request.cookies)
        session_token = get_session_token_from_cookies(cookies)
        
        if session_token:
            result = await validate_session_token(session_token)
            if result:
                session, user = result
                # Convert better-auth user to UserClaims format
                request.state.user = UserClaims(
                    sub=user.id,  # Use better-auth user ID
                    email=user.email,
                    name=user.name,
                    roles=["User"],  # Default role, can be enhanced
                    tenant_id=user.tenant_id or "default",
                    groups=[],
                    raw_claims={
                        "department": user.department,
                        "job_title": user.job_title,
                        "email_verified": user.email_verified,
                    },
                )
                return await call_next(request)
        
        # Try Bearer token (EntraID JWT)
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            # Parse Bearer token
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                
                # Validate token
                try:
                    user_claims = await validate_token(token)
                    request.state.user = user_claims
                    return await call_next(request)
                except OIDCValidationError as e:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=str(e),
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        
        # In development mode, fall back to dev user if no other auth provided
        if settings.environment == "development":
            request.state.user = dev_user
            return await call_next(request)
        
        # No valid authentication found (production)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide session cookie or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


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


async def get_optional_user(request: Request) -> Optional[UserClaims]:
    """FastAPI dependency to get the current user if authenticated.
    
    Returns None if not authenticated (for optional auth endpoints).
    """
    return getattr(request.state, "user", None)
