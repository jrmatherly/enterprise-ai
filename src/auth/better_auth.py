"""Better-auth session validation for FastAPI.

Validates session cookies from better-auth (frontend) and extracts user info.
"""

from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import async_session_maker


@dataclass
class BetterAuthUser:
    """User info from better-auth session."""
    id: str
    email: str
    name: str
    email_verified: bool
    tenant_id: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    image: Optional[str] = None


@dataclass  
class BetterAuthSession:
    """Session info from better-auth."""
    id: str
    user_id: str
    token: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


async def validate_session_token(token: str) -> Optional[tuple[BetterAuthSession, BetterAuthUser]]:
    """Validate a better-auth session token and return session + user.
    
    Args:
        token: The session token from the cookie
        
    Returns:
        Tuple of (session, user) if valid, None if invalid/expired
    """
    if not token:
        return None
    
    async with async_session_maker() as db:
        try:
            # Query session and user in one go
            # Note: better-auth uses camelCase column names
            query = text("""
                SELECT 
                    s.id as session_id,
                    s."userId" as user_id,
                    s.token,
                    s."expiresAt" as expires_at,
                    s."ipAddress" as ip_address,
                    s."userAgent" as user_agent,
                    u.id as u_id,
                    u.email,
                    u.name,
                    u."emailVerified" as email_verified,
                    u."tenantId" as tenant_id,
                    u.department,
                    u."jobTitle" as job_title,
                    u.image
                FROM session s
                JOIN "user" u ON s."userId" = u.id
                WHERE s.token = :token
            """)
            
            result = await db.execute(query, {"token": token})
            row = result.fetchone()
            
            if not row:
                return None
            
            # Check if session is expired
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                return None
            
            session = BetterAuthSession(
                id=row.session_id,
                user_id=row.user_id,
                token=row.token,
                expires_at=expires_at,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
            )
            
            user = BetterAuthUser(
                id=row.u_id,
                email=row.email,
                name=row.name,
                email_verified=row.email_verified,
                tenant_id=row.tenant_id,
                department=row.department,
                job_title=row.job_title,
                image=row.image,
            )
            
            return session, user
            
        except Exception as e:
            print(f"Error validating better-auth session: {e}")
            return None


def get_session_token_from_cookies(cookies: dict[str, str]) -> Optional[str]:
    """Extract the better-auth session token from cookies.
    
    better-auth typically uses 'better-auth.session_token' as the cookie name.
    """
    # Try the standard cookie name
    token = cookies.get("better-auth.session_token")
    if token:
        return token
    
    # Also try without the prefix (in case of configuration differences)
    token = cookies.get("session_token")
    if token:
        return token
    
    return None
