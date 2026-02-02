"""Better-auth JWT validation for FastAPI.

Validates JWT tokens from better-auth (frontend) using JWKS.
This is the proper way to verify sessions between services - no shared secrets needed.

The frontend exposes:
- /api/auth/token - Get a JWT for the current session
- /api/auth/jwks - Public keys for verifying JWTs
"""

import time
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt
from jose.exceptions import JWKError

from src.core.config import get_settings

# JWKS cache
_jwks_cache: dict | None = None
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour


@dataclass
class BetterAuthUser:
    """User info from better-auth JWT."""

    id: str
    email: str
    name: str
    email_verified: bool
    tenant_id: str | None = None
    department: str | None = None
    job_title: str | None = None
    image: str | None = None


@dataclass
class BetterAuthSession:
    """Session info from better-auth JWT."""

    id: str
    user_id: str
    expires_at: int  # Unix timestamp


async def fetch_jwks(force_refresh: bool = False) -> dict:
    """Fetch JWKS from the frontend auth service.

    Caches the JWKS for performance. Force refresh if a key is not found.
    """
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if not force_refresh and _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache

    settings = get_settings()
    # Use internal URL for JWKS fetch (Docker network) if available, otherwise external
    base_url = settings.better_auth_internal_url or settings.better_auth_url
    jwks_url = f"{base_url}/api/auth/jwks"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = now
            return _jwks_cache
    except httpx.HTTPError as e:
        print(f"Error fetching JWKS from {jwks_url}: {e}")
        # Return cached version if available, even if expired
        if _jwks_cache:
            return _jwks_cache
        raise


def get_signing_key(jwks: dict, kid: str | None) -> dict:
    """Get the signing key from JWKS by key ID."""
    keys = jwks.get("keys", [])

    if not keys:
        raise JWKError("No keys in JWKS")

    # If kid specified, find matching key
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise JWKError(f"Key with kid '{kid}' not found in JWKS")

    # Otherwise return the first key
    return keys[0]


async def validate_jwt_token(token: str) -> tuple[BetterAuthSession, BetterAuthUser] | None:
    """Validate a better-auth JWT token and return session + user.

    Args:
        token: The JWT token from Authorization header or cookie

    Returns:
        Tuple of (session, user) if valid, None if invalid/expired
    """
    if not token:
        return None

    settings = get_settings()
    expected_issuer = settings.better_auth_url
    expected_audience = settings.better_auth_url

    try:
        # Get unverified header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Fetch JWKS
        jwks = await fetch_jwks()

        try:
            signing_key = get_signing_key(jwks, kid)
        except JWKError:
            # Key not found, try refreshing JWKS
            jwks = await fetch_jwks(force_refresh=True)
            signing_key = get_signing_key(jwks, kid)

        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["EdDSA", "ES256", "RS256"],  # Support common algorithms
            issuer=expected_issuer,
            audience=expected_audience,
        )

        # Extract user and session from JWT payload
        # better-auth JWT payload structure:
        # { sub: userId, email, name, emailVerified, ... , exp, iat, iss, aud }
        user = BetterAuthUser(
            id=payload.get("sub", payload.get("id", "")),
            email=payload.get("email", ""),
            name=payload.get("name", ""),
            email_verified=payload.get("emailVerified", False),
            tenant_id=payload.get("tenantId"),
            department=payload.get("department"),
            job_title=payload.get("jobTitle"),
            image=payload.get("image"),
        )

        session = BetterAuthSession(
            id=payload.get("sessionId", "jwt-session"),
            user_id=user.id,
            expires_at=payload.get("exp", 0),
        )

        return session, user

    except JWTError as e:
        print(f"JWT validation error: {e}")
        return None
    except Exception as e:
        print(f"Error validating better-auth JWT: {e}")
        return None


def get_bearer_token_from_header(authorization: str | None) -> str | None:
    """Extract the bearer token from Authorization header.

    Args:
        authorization: The Authorization header value

    Returns:
        The token if present and valid format, None otherwise
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def get_session_token_from_cookies(cookies: dict[str, str]) -> str | None:
    """Extract the better-auth session token from cookies.

    better-auth uses 'better-auth.session_token' as the cookie name.
    This is used for browser-based requests where cookies are sent automatically.

    For API calls from the backend, prefer using JWT tokens via Authorization header.
    """
    # Try the standard cookie name
    token = cookies.get("better-auth.session_token")
    if token:
        return token

    # Also try without the prefix (in case of configuration differences)
    return cookies.get("session_token")
