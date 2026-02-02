"""Role-Based Access Control (RBAC) implementation.

Adapted from Microsoft's active-directory-aspnetcore-webapp patterns.
See: MICROSOFT-REPOS-ANALYSIS.md for source patterns.
"""

from collections.abc import Callable
from enum import Enum
from functools import wraps

from fastapi import HTTPException, Request, status

from src.auth.oidc import UserClaims


class AppRole(str, Enum):
    """Application roles aligned with enterprise hierarchy.

    Maps to EntraID/Keycloak role claims.
    """

    ORG_ADMIN = "OrgAdmin"  # Full platform administration
    DEPT_ADMIN = "DeptAdmin"  # Department-level administration
    TEAM_LEAD = "TeamLead"  # Team management capabilities
    USER = "User"  # Standard user access
    READ_ONLY = "ReadOnly"  # View-only access


class Permission(str, Enum):
    """Granular permissions for authorization checks."""

    # Organization level
    MANAGE_ORG_KB = "manage_org_kb"  # Manage org knowledge base
    MANAGE_ORG_SETTINGS = "manage_org_settings"  # Org configuration
    VIEW_AUDIT_LOGS = "view_audit_logs"  # View audit trail
    MANAGE_USERS = "manage_users"  # User administration

    # Department level
    MANAGE_DEPT_KB = "manage_dept_kb"  # Manage dept knowledge base
    MANAGE_DEPT_TOOLS = "manage_dept_tools"  # Configure dept tools

    # User level
    UPLOAD_DOCS = "upload_docs"  # Upload personal documents
    QUERY_KB = "query_kb"  # Query knowledge bases
    USE_AGENT = "use_agent"  # Use AI agent
    MANAGE_PERSONAL_KB = "manage_personal_kb"  # Manage own knowledge base

    # Tool management
    MANAGE_TOOLS = "manage_tools"  # Manage tool allowlist
    REGISTER_MCP = "register_mcp"  # Register MCP servers


# Role to permissions mapping
ROLE_PERMISSIONS: dict[AppRole, list[Permission]] = {
    AppRole.ORG_ADMIN: list(Permission),  # All permissions
    AppRole.DEPT_ADMIN: [
        Permission.MANAGE_DEPT_KB,
        Permission.MANAGE_DEPT_TOOLS,
        Permission.UPLOAD_DOCS,
        Permission.QUERY_KB,
        Permission.USE_AGENT,
        Permission.MANAGE_PERSONAL_KB,
    ],
    AppRole.TEAM_LEAD: [
        Permission.UPLOAD_DOCS,
        Permission.QUERY_KB,
        Permission.USE_AGENT,
        Permission.MANAGE_PERSONAL_KB,
    ],
    AppRole.USER: [
        Permission.UPLOAD_DOCS,
        Permission.QUERY_KB,
        Permission.USE_AGENT,
        Permission.MANAGE_PERSONAL_KB,
    ],
    AppRole.READ_ONLY: [
        Permission.QUERY_KB,
    ],
}


def get_user_permissions(roles: list[str]) -> set[Permission]:
    """Get all permissions for a list of roles.

    Args:
        roles: List of role names from JWT claims

    Returns:
        Set of all permissions granted by these roles
    """
    permissions: set[Permission] = set()

    for role_name in roles:
        try:
            role = AppRole(role_name)
            role_perms = ROLE_PERMISSIONS.get(role, [])
            permissions.update(role_perms)
        except ValueError:
            # Unknown role, skip
            continue

    return permissions


def _extract_roles(user: UserClaims | dict | None) -> list[str]:
    """Extract roles from a user object (UserClaims or dict).

    Args:
        user: UserClaims dataclass, dict, or None

    Returns:
        List of role names
    """
    if user is None:
        return []
    if isinstance(user, UserClaims):
        return user.roles
    if isinstance(user, dict):
        return user.get("roles", [])
    return []


def has_permission(user_roles: list[str], required: Permission) -> bool:
    """Check if user has a specific permission.

    Args:
        user_roles: List of role names from JWT claims
        required: Permission to check for

    Returns:
        True if user has the permission
    """
    permissions = get_user_permissions(user_roles)
    return required in permissions


def has_any_permission(user_roles: list[str], required: list[Permission]) -> bool:
    """Check if user has any of the specified permissions."""
    permissions = get_user_permissions(user_roles)
    return any(p in permissions for p in required)


def has_all_permissions(user_roles: list[str], required: list[Permission]) -> bool:
    """Check if user has all of the specified permissions."""
    permissions = get_user_permissions(user_roles)
    return all(p in permissions for p in required)


class PermissionChecker:
    """Dependency for FastAPI to check permissions."""

    def __init__(self, required: Permission):
        self.required = required

    async def __call__(self, request: Request) -> bool:
        """Check permission, raise HTTPException if denied."""
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        user_roles = _extract_roles(user)

        if not has_permission(user_roles, self.required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.required.value}",
            )

        return True


def require_permission(permission: Permission) -> Callable:
    """Decorator to require a specific permission.

    Usage:
        @router.get("/admin/users")
        @require_permission(Permission.MANAGE_USERS)
        async def list_users(request: Request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args or kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request not found in handler",
                )

            user = getattr(request.state, "user", None)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )

            user_roles = _extract_roles(user)

            if not has_permission(user_roles, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission.value}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission) -> Callable:
    """Decorator to require any of the specified permissions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request not found in handler",
                )

            user = getattr(request.state, "user", None)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )

            user_roles = _extract_roles(user)

            if not has_any_permission(user_roles, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {[p.value for p in permissions]}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
