"""FastAPI dependency injection.

Provides common dependencies for API routes.
"""

from typing import Annotated, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user, get_optional_user
from src.auth.oidc import UserClaims
from src.auth.rbac import Permission, has_permission, PermissionChecker
from src.db.database import get_db
from src.db.repository import SessionRepository, MessageRepository, UsageRepository
from src.agent.runtime import AgentRuntime, get_runtime
from src.core.config import Settings, get_settings
from src.core.rate_limiting import CombinedRateLimiter, get_rate_limiter


# Type aliases for cleaner signatures
CurrentUser = Annotated[UserClaims, Depends(get_current_user)]
OptionalUser = Annotated[Optional[UserClaims], Depends(get_optional_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
Runtime = Annotated[AgentRuntime, Depends(get_runtime)]
RateLimiter = Annotated[CombinedRateLimiter, Depends(get_rate_limiter)]
AppSettings = Annotated[Settings, Depends(get_settings)]


# Repository dependencies
async def get_session_repo(db: DB) -> SessionRepository:
    """Get session repository."""
    return SessionRepository(db)


async def get_message_repo(db: DB) -> MessageRepository:
    """Get message repository."""
    return MessageRepository(db)


async def get_usage_repo(db: DB) -> UsageRepository:
    """Get usage repository."""
    return UsageRepository(db)


SessionRepo = Annotated[SessionRepository, Depends(get_session_repo)]
MessageRepo = Annotated[MessageRepository, Depends(get_message_repo)]
UsageRepo = Annotated[UsageRepository, Depends(get_usage_repo)]


# Permission dependencies
RequireManageOrgKB = Depends(PermissionChecker(Permission.MANAGE_ORG_KB))
RequireManageDeptKB = Depends(PermissionChecker(Permission.MANAGE_DEPT_KB))
RequireUploadDocs = Depends(PermissionChecker(Permission.UPLOAD_DOCS))
RequireQueryKB = Depends(PermissionChecker(Permission.QUERY_KB))
RequireUseAgent = Depends(PermissionChecker(Permission.USE_AGENT))
RequireManageUsers = Depends(PermissionChecker(Permission.MANAGE_USERS))
RequireViewAuditLogs = Depends(PermissionChecker(Permission.VIEW_AUDIT_LOGS))
