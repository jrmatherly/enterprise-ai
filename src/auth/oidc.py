"""OIDC token validation for Microsoft Entra ID.

Validates JWT tokens from Entra ID and extracts user claims.
"""

import time
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt
from jose.backends import RSAKey

from src.core.config import get_settings


@dataclass
class UserClaims:
    """Extracted claims from a validated JWT."""

    sub: str  # Subject (user ID)
    email: str
    name: str | None
    roles: list[str]
    tenant_id: str
    groups: list[str]
    raw_claims: dict


class OIDCValidationError(Exception):
    """Raised when token validation fails."""



class EntraIDValidator:
    """Validates JWTs from Microsoft Entra ID.

    Implements OIDC discovery and JWKS caching for efficient validation.
    """

    def __init__(self):
        settings = get_settings()
        self.tenant_id = settings.azure_tenant_id
        self.client_id = settings.azure_client_id

        # OIDC endpoints
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

        # JWKS cache
        self._jwks_cache: dict | None = None
        self._jwks_cache_time: float = 0
        self._jwks_cache_ttl: int = 3600  # 1 hour

    async def _fetch_jwks(self) -> dict:
        """Fetch JWKS from Entra ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def _get_jwks(self) -> dict:
        """Get JWKS with caching."""
        now = time.time()

        if self._jwks_cache is None or (now - self._jwks_cache_time) > self._jwks_cache_ttl:
            self._jwks_cache = await self._fetch_jwks()
            self._jwks_cache_time = now

        return self._jwks_cache

    def _get_signing_key(self, jwks: dict, kid: str) -> RSAKey:
        """Get the signing key for a given key ID."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        raise OIDCValidationError(f"Key ID '{kid}' not found in JWKS")

    async def validate_token(self, token: str) -> UserClaims:
        """Validate a JWT and extract user claims.

        Args:
            token: The JWT access token

        Returns:
            UserClaims with extracted information

        Raises:
            OIDCValidationError: If token is invalid
        """
        try:
            # Get unverified header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise OIDCValidationError("Token missing key ID (kid)")

            # Fetch JWKS and get signing key
            jwks = await self._get_jwks()
            signing_key = self._get_signing_key(jwks, kid)

            # Validate and decode token
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            # Extract user claims
            return UserClaims(
                sub=claims.get("sub", claims.get("oid", "")),
                email=claims.get("email", claims.get("preferred_username", "")),
                name=claims.get("name"),
                roles=claims.get("roles", []),
                tenant_id=claims.get("tid", self.tenant_id),
                groups=claims.get("groups", []),
                raw_claims=claims,
            )

        except JWTError as e:
            raise OIDCValidationError(f"Token validation failed: {e!s}") from None
        except httpx.HTTPError as e:
            raise OIDCValidationError(f"Failed to fetch JWKS: {e!s}") from None


# Singleton instance
_validator: EntraIDValidator | None = None


def get_validator() -> EntraIDValidator:
    """Get or create the Entra ID validator singleton."""
    global _validator
    if _validator is None:
        _validator = EntraIDValidator()
    return _validator


async def validate_token(token: str) -> UserClaims:
    """Convenience function to validate a token.

    Args:
        token: The JWT access token

    Returns:
        UserClaims with extracted information
    """
    validator = get_validator()
    return await validator.validate_token(token)
