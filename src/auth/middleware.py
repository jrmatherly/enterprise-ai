"""Authentication middleware for FastAPI.

Extracts and validates JWTs from requests, setting user context.
"""

from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.auth.oidc import validate_token, OIDCValidationError, UserClaims
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
        
        # In development mode, allow bypass with X-Dev-Bypass header or no auth
        if settings.environment == "development":
            # Dev user with valid UUIDs for database compatibility
            dev_user = UserClaims(
                sub="00000000-0000-0000-0000-000000000001",  # Valid UUID
                email="dev@example.com",
                name="Developer",
                roles=["OrgAdmin"],  # Full access in dev mode
                tenant_id="00000000-0000-0000-0000-000000000000",  # Valid UUID
                groups=[],
                raw_claims={},
            )
            
            # Check for explicit dev bypass header
            if request.headers.get("X-Dev-Bypass") == "true":
                request.state.user = dev_user
                return await call_next(request)
            
            # Check for placeholder values that indicate unconfigured auth
            is_placeholder = (
                not settings.azure_tenant_id or 
                settings.azure_tenant_id == "tenant-id" or
                settings.azure_tenant_id.startswith("<")
            )
            if is_placeholder:
                request.state.user = dev_user
                return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Use: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        
        # Validate token
        try:
            user_claims = await validate_token(token)
            request.state.user = user_claims
        except OIDCValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)


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
