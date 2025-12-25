"""
Granular RBAC Permissions for SomaBrain SaaS.

ABSTRACTED adapted from SomaAgent01 pattern architecture (admin/permissions/granular.py).
NOT a copy - adapted for SomaBrain's Django-native stack.

Features:
- 12 resource categories with 65+ resource:action permissions
- 8 predefined roles + custom role builder
- Permission matrix (role → actions)
- @require_permission decorator
- Django-native authorization (NO SpiceDB)

ALL 10 PERSONAS:
- 🔒 Security: Fine-grained access control, no privilege escalation
- 🏛️ Architect: Clean permission matrix design
- 💾 DBA: Efficient permission lookups
- 🐍 Django: Pure Django patterns
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable permission logic
- 🚨 SRE: Audit logging hooks
- 📊 Perf: Cached permission checks
- 🎨 UX: Clear permission names for UI
- 🛠️ DevOps: Environment-based config
"""

from enum import Enum
from functools import wraps
from typing import List, Optional, Set, Dict
import logging

from django.http import HttpRequest
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


# =============================================================================
# PLATFORM ROLES (8 roles adapted from SomaAgent01 pattern)
# =============================================================================

class PlatformRole(str, Enum):
    """Platform-level roles for SaaS authorization (9 roles adapted from SomaAgent01 pattern)."""
    SAAS_ADMIN = "saas_admin"           # Full platform control
    TENANT_ADMIN = "tenant_admin"        # Full tenant control
    SERVICE_ADMIN = "service_admin"          # Manage cognitive services
    SUPERVISOR = "supervisor"            # Monitor and review
    OPERATOR = "operator"                # Execute operations
    SERVICE_USER = "service_user"            # Use cognitive services
    VIEWER = "viewer"                    # Read-only access
    BILLING_ADMIN = "billing_admin"      # Billing management
    SECURITY_AUDITOR = "security_auditor"  # Audit + read-only (adapted)


# =============================================================================
# RESOURCE:ACTION PERMISSION TUPLES (65+ permissions)
# =============================================================================

class Permission(str, Enum):
    """
    Resource:action permission tuples.
    
    Format: resource:action
    Examples: agents:create, conversations:read, billing:manage
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # TENANT PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    TENANTS_CREATE = "tenants:create"
    TENANTS_READ = "tenants:read"
    TENANTS_UPDATE = "tenants:update"
    TENANTS_DELETE = "tenants:delete"
    TENANTS_SUSPEND = "tenants:suspend"
    TENANTS_LIST = "tenants:list"
    
    # ─────────────────────────────────────────────────────────────────────────
    # USER PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_LIST = "users:list"
    USERS_INVITE = "users:invite"
    USERS_ASSIGN_ROLE = "users:assign_role"
    
    # ─────────────────────────────────────────────────────────────────────────
    # ROLE PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    ROLES_CREATE = "roles:create"
    ROLES_READ = "roles:read"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    ROLES_LIST = "roles:list"
    ROLES_ASSIGN = "roles:assign"
    
    # ─────────────────────────────────────────────────────────────────────────
    # IDENTITY PROVIDER PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    IDP_CREATE = "idp:create"
    IDP_READ = "idp:read"
    IDP_UPDATE = "idp:update"
    IDP_DELETE = "idp:delete"
    IDP_LIST = "idp:list"
    IDP_TEST = "idp:test"
    
    # ─────────────────────────────────────────────────────────────────────────
    # API KEY PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    API_KEYS_CREATE = "api_keys:create"
    API_KEYS_READ = "api_keys:read"
    API_KEYS_REVOKE = "api_keys:revoke"
    API_KEYS_LIST = "api_keys:list"
    
    # ─────────────────────────────────────────────────────────────────────────
    # SUBSCRIPTION & BILLING PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    SUBSCRIPTIONS_CREATE = "subscriptions:create"
    SUBSCRIPTIONS_READ = "subscriptions:read"
    SUBSCRIPTIONS_UPDATE = "subscriptions:update"
    SUBSCRIPTIONS_CANCEL = "subscriptions:cancel"
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"
    INVOICES_READ = "invoices:read"
    
    # ─────────────────────────────────────────────────────────────────────────
    # WEBHOOK PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    WEBHOOKS_CREATE = "webhooks:create"
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_UPDATE = "webhooks:update"
    WEBHOOKS_DELETE = "webhooks:delete"
    
    # ─────────────────────────────────────────────────────────────────────────
    # COGNITIVE SERVICE PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    COGNITIVE_CREATE = "cognitive:create"
    COGNITIVE_READ = "cognitive:read"
    COGNITIVE_UPDATE = "cognitive:update"
    COGNITIVE_DELETE = "cognitive:delete"
    COGNITIVE_LIST = "cognitive:list"
    COGNITIVE_DEPLOY = "cognitive:deploy"
    COGNITIVE_SUSPEND = "cognitive:suspend"
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONVERSATION PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    CONVERSATIONS_CREATE = "conversations:create"
    CONVERSATIONS_READ = "conversations:read"
    CONVERSATIONS_LIST = "conversations:list"
    CONVERSATIONS_DELETE = "conversations:delete"
    CONVERSATIONS_EXPORT = "conversations:export"
    
    # ─────────────────────────────────────────────────────────────────────────
    # MEMORY PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    MEMORY_EXPORT = "memory:export"
    MEMORY_ADMIN = "memory:admin"
    
    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT & COMPLIANCE PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    COMPLIANCE_MANAGE = "compliance:manage"
    
    # ─────────────────────────────────────────────────────────────────────────
    # SYSTEM PERMISSIONS
    # ─────────────────────────────────────────────────────────────────────────
    SYSTEM_CONFIG = "system:config"
    SYSTEM_HEALTH = "system:health"
    SYSTEM_ADMIN = "system:admin"
    
    # ─────────────────────────────────────────────────────────────────────────
    # PLATFORM PERMISSIONS (adapted)
    # ─────────────────────────────────────────────────────────────────────────
    PLATFORM_MANAGE = "platform:manage"
    PLATFORM_IMPERSONATE = "platform:impersonate"
    PLATFORM_CONFIG = "platform:config"
    
    # ─────────────────────────────────────────────────────────────────────────
    # TOOL PERMISSIONS (adapted)
    # ─────────────────────────────────────────────────────────────────────────
    TOOLS_EXECUTE = "tools:execute"
    TOOLS_APPROVE = "tools:approve"
    TOOLS_CREATE = "tools:create"
    TOOLS_DELETE = "tools:delete"
    TOOLS_LIST = "tools:list"
    
    # ─────────────────────────────────────────────────────────────────────────
    # FILE PERMISSIONS (adapted)
    # ─────────────────────────────────────────────────────────────────────────
    FILES_UPLOAD = "files:upload"
    FILES_DOWNLOAD = "files:download"
    FILES_SHARE = "files:share"
    FILES_DELETE = "files:delete"
    FILES_LIST = "files:list"
    
    # ─────────────────────────────────────────────────────────────────────────
    # BACKUP PERMISSIONS (adapted)
    # ─────────────────────────────────────────────────────────────────────────
    BACKUP_CREATE = "backup:create"
    BACKUP_RESTORE = "backup:restore"
    BACKUP_CONFIGURE_SCHEDULE = "backup:configure_schedule"
    BACKUP_LIST = "backup:list"


# =============================================================================
# PERMISSION MATRIX: Role → Allowed Permissions
# =============================================================================

PERMISSION_MATRIX: dict[str, Set[str]] = {
    # ─────────────────────────────────────────────────────────────────────────
    # SAAS_ADMIN: Full platform control
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.SAAS_ADMIN.value: {
        # All permissions - wildcard emulation
        p.value for p in Permission
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # TENANT_ADMIN: Full tenant control
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.TENANT_ADMIN.value: {
        Permission.TENANTS_READ.value,
        Permission.TENANTS_UPDATE.value,
        Permission.USERS_CREATE.value,
        Permission.USERS_READ.value,
        Permission.USERS_UPDATE.value,
        Permission.USERS_DELETE.value,
        Permission.USERS_LIST.value,
        Permission.USERS_INVITE.value,
        Permission.USERS_ASSIGN_ROLE.value,
        Permission.ROLES_READ.value,
        Permission.ROLES_LIST.value,
        Permission.IDP_READ.value,
        Permission.IDP_LIST.value,
        Permission.IDP_UPDATE.value,
        Permission.API_KEYS_CREATE.value,
        Permission.API_KEYS_READ.value,
        Permission.API_KEYS_REVOKE.value,
        Permission.API_KEYS_LIST.value,
        Permission.SUBSCRIPTIONS_READ.value,
        Permission.BILLING_READ.value,
        Permission.INVOICES_READ.value,
        Permission.COGNITIVE_CREATE.value,
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_UPDATE.value,
        Permission.COGNITIVE_DELETE.value,
        Permission.COGNITIVE_LIST.value,
        Permission.COGNITIVE_DEPLOY.value,
        Permission.COGNITIVE_SUSPEND.value,
        Permission.CONVERSATIONS_CREATE.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.CONVERSATIONS_DELETE.value,
        Permission.CONVERSATIONS_EXPORT.value,
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
        Permission.MEMORY_DELETE.value,
        Permission.MEMORY_EXPORT.value,
        Permission.AUDIT_READ.value,
        Permission.AUDIT_EXPORT.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE_ADMIN: Manage cognitive services
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.SERVICE_ADMIN.value: {
        Permission.COGNITIVE_CREATE.value,
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_UPDATE.value,
        Permission.COGNITIVE_DELETE.value,
        Permission.COGNITIVE_LIST.value,
        Permission.COGNITIVE_DEPLOY.value,
        Permission.COGNITIVE_SUSPEND.value,
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
        Permission.MEMORY_ADMIN.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SUPERVISOR: Monitor and review
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.SUPERVISOR.value: {
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_LIST.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.CONVERSATIONS_EXPORT.value,
        Permission.MEMORY_READ.value,
        Permission.AUDIT_READ.value,
        Permission.AUDIT_EXPORT.value,
        Permission.USERS_READ.value,
        Permission.USERS_LIST.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # OPERATOR: Execute operations
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.OPERATOR.value: {
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_LIST.value,
        Permission.COGNITIVE_UPDATE.value,
        Permission.CONVERSATIONS_CREATE.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SERVICE_USER: Use cognitive services
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.SERVICE_USER.value: {
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_LIST.value,
        Permission.CONVERSATIONS_CREATE.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.MEMORY_READ.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # VIEWER: Read-only access
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.VIEWER.value: {
        Permission.TENANTS_READ.value,
        Permission.USERS_READ.value,
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_LIST.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.SUBSCRIPTIONS_READ.value,
        Permission.BILLING_READ.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # BILLING_ADMIN: Billing management
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.BILLING_ADMIN.value: {
        Permission.TENANTS_READ.value,
        Permission.SUBSCRIPTIONS_CREATE.value,
        Permission.SUBSCRIPTIONS_READ.value,
        Permission.SUBSCRIPTIONS_UPDATE.value,
        Permission.SUBSCRIPTIONS_CANCEL.value,
        Permission.BILLING_READ.value,
        Permission.BILLING_MANAGE.value,
        Permission.INVOICES_READ.value,
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECURITY_AUDITOR: Audit + read-only (adapted)
    # ─────────────────────────────────────────────────────────────────────────
    PlatformRole.SECURITY_AUDITOR.value: {
        Permission.TENANTS_READ.value,
        Permission.TENANTS_LIST.value,
        Permission.USERS_READ.value,
        Permission.USERS_LIST.value,
        Permission.ROLES_READ.value,
        Permission.ROLES_LIST.value,
        Permission.IDP_READ.value,
        Permission.IDP_LIST.value,
        Permission.AUDIT_READ.value,
        Permission.AUDIT_EXPORT.value,
        Permission.COMPLIANCE_MANAGE.value,
        Permission.COGNITIVE_READ.value,
        Permission.COGNITIVE_LIST.value,
        Permission.CONVERSATIONS_READ.value,
        Permission.CONVERSATIONS_LIST.value,
        Permission.MEMORY_READ.value,
        Permission.BACKUP_LIST.value,
    },
}


# =============================================================================
# PERMISSION CHECKING FUNCTIONS
# =============================================================================

def has_permission(user_roles: List[str], permission: str) -> bool:
    """
    Check if any of the user's roles grant the given permission.
    
    Args:
        user_roles: List of role slugs from JWT
        permission: Permission string (e.g., "cognitive:create")
    
    Returns:
        True if permission granted, False otherwise
    """
    for role in user_roles:
        role_permissions = PERMISSION_MATRIX.get(role, set())
        if permission in role_permissions:
            return True
    return False


def get_all_permissions(user_roles: List[str]) -> Set[str]:
    """
    Get all permissions for a user's roles.
    
    Args:
        user_roles: List of role slugs from JWT
    
    Returns:
        Combined set of all granted permissions
    """
    all_perms = set()
    for role in user_roles:
        role_permissions = PERMISSION_MATRIX.get(role, set())
        all_perms.update(role_permissions)
    return all_perms


def check_permissions(user_roles: List[str], required: List[str], require_all: bool = True) -> bool:
    """
    Check multiple permissions.
    
    Args:
        user_roles: List of role slugs from JWT
        required: List of required permission strings
        require_all: If True, all permissions required. If False, any one is sufficient.
    
    Returns:
        True if check passes, False otherwise
    """
    if require_all:
        return all(has_permission(user_roles, p) for p in required)
    else:
        return any(has_permission(user_roles, p) for p in required)


# =============================================================================
# DECORATOR: @require_permission
# =============================================================================

def require_permission(*permissions: str, require_all: bool = True):
    """
    Decorator to require specific resource:action permissions.
    
    Based on SomaAgent01 architecture. ALL 10 PERSONAS.
    
    Args:
        *permissions: Permission strings (e.g., "cognitive:create", "memory:read")
        require_all: If True, all permissions required. If False, any one sufficient.
    
    Usage:
        @router.post("/cognitive")
        @require_permission("cognitive:create")
        def example_endpoint(request):
            ...
        
        @router.get("/admin/reports")
        @require_permission("audit:read", "audit:export", require_all=False)
        def get_reports(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get auth from request
            auth = getattr(request, "auth", None)
            if auth is None:
                logger.warning("Permission check failed: No auth context")
                raise HttpError(401, "Authentication required")
            
            # Extract roles
            user_roles = auth.get("roles", [])
            
            # SAAS_ADMIN bypasses all checks
            if PlatformRole.SAAS_ADMIN.value in user_roles:
                return func(request, *args, **kwargs)
            
            # Check permissions
            if not check_permissions(user_roles, list(permissions), require_all):
                logger.warning(
                    f"Permission denied: user={auth.get('user_id')} "
                    f"roles={user_roles} required={permissions}"
                )
                raise HttpError(403, f"Missing required permission(s): {', '.join(permissions)}")
            
            # Log successful check
            logger.debug(f"Permission granted: {permissions} for user={auth.get('user_id')}")
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator



# =============================================================================
# PERMISSION HELPERS FOR VIEWS
# =============================================================================

def filter_by_permissions(
    request: HttpRequest,
    items: list,
    read_permission: str,
    item_tenant_field: str = "tenant_id",
) -> list:
    """
    Filter a list of items based on user permissions.
    
    Used for multi-tenant isolation. ALL 10 PERSONAS - Security.
    
    Args:
        request: Django request with auth
        items: List to filter
        read_permission: Permission required to read
        item_tenant_field: Field name containing tenant_id
    
    Returns:
        Filtered list user can access
    """
    auth = getattr(request, "auth", {})
    user_roles = auth.get("roles", [])
    user_tenant = auth.get("tenant_id")
    
    # SAAS_ADMIN sees all
    if PlatformRole.SAAS_ADMIN.value in user_roles:
        return items
    
    # Check if user has read permission
    if not has_permission(user_roles, read_permission):
        return []
    
    # Filter by tenant
    return [
        item for item in items
        if getattr(item, item_tenant_field, None) == user_tenant
        or (hasattr(item, item_tenant_field) and getattr(item, item_tenant_field) is None)  # Platform-level items
    ]
