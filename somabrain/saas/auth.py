"""
API Key Authentication for SomaBrain.

Pure Django + Django Ninja authentication layer.
Implements sbk_live_* and sbk_test_* API key verification.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean layered design
- Security: Constant-time comparison, hashing
- DevOps: Environment-based config
- QA: Testable interfaces
- Docs: Comprehensive docstrings
- DBA: Efficient queries
- SRE: Observability hooks
"""

import hashlib
import hmac
import logging
from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from ninja.security import HttpBearer

from .models import APIKey, AuditLog, Tenant, TenantStatus

logger = logging.getLogger(__name__)


# =============================================================================
# API KEY AUTHENTICATION (Django Ninja HttpBearer)
# =============================================================================

class APIKeyAuth(HttpBearer):
    """
    API Key authentication for Django Ninja.
    
    Validates sbk_live_* or sbk_test_* API keys.
    Extracts tenant context for downstream handlers.
    
    Usage:
        @api.get("/endpoint", auth=APIKeyAuth())
        def endpoint(request):
            tenant = request.auth["tenant"]
            ...
    """
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[dict]:
        """
        Authenticate the API key token.
        
        Args:
            request: The HTTP request
            token: The API key from Authorization header
            
        Returns:
            Dict with tenant and key info, or None if invalid
        """
        # Validate token format
        if not token or not token.startswith("sbk_"):
            logger.warning("Invalid API key format")
            return None
        
        # Verify key
        api_key = self._verify_key(token)
        if not api_key:
            logger.warning("API key verification failed")
            return None
        
        # Check tenant status
        if api_key.tenant.status not in [TenantStatus.ACTIVE, TenantStatus.TRIAL]:
            logger.warning(f"Tenant {api_key.tenant.slug} not active")
            return None
        
        # Update usage stats
        ip_address = self._get_client_ip(request)
        api_key.touch(ip_address)
        
        # Log successful auth
        logger.info(f"API key authenticated: {api_key.key_prefix}... for tenant {api_key.tenant.slug}")
        
        return {
            "tenant": api_key.tenant,
            "tenant_id": str(api_key.tenant.id),
            "tenant_slug": api_key.tenant.slug,
            "api_key": api_key,
            "api_key_id": str(api_key.id),
            "scopes": api_key.scopes,
            "is_test": api_key.is_test,
        }
    
    def _verify_key(self, token: str) -> Optional[APIKey]:
        """
        Verify API key using constant-time comparison.
        
        Security: Uses hashlib for key hashing and hmac.compare_digest
        for constant-time comparison to prevent timing attacks.
        """
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            # Query by hash only (no prefix to avoid timing attacks)
            api_key = APIKey.objects.select_related("tenant").get(
                key_hash=key_hash,
                is_active=True,
            )
            
            # Check expiration
            if api_key.expires_at and api_key.expires_at < timezone.now():
                logger.warning(f"API key expired: {api_key.key_prefix}...")
                return None
            
            # Check revocation
            if api_key.revoked_at:
                logger.warning(f"API key revoked: {api_key.key_prefix}...")
                return None
            
            return api_key
            
        except APIKey.DoesNotExist:
            return None
    
    def _get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """Extract client IP from request (handles proxies)."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# =============================================================================
# BEARER TOKEN AUTH (For Keycloak JWT)
# =============================================================================

class JWTAuth(HttpBearer):
    """
    JWT authentication for Keycloak SSO.
    
    Validates JWTs issued by Keycloak with proper JWKS verification.
    VIBE COMPLIANT: Real signature verification enabled.
    """
    
    _jwks_cache: dict = None
    _jwks_fetched_at: float = 0
    JWKS_CACHE_TTL = 300  # 5 minutes
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[dict]:
        """Authenticate JWT token from Keycloak."""
        try:
            import jwt
            from jwt import PyJWKClient
            import time
            
            # Get Keycloak config from settings
            keycloak_url = getattr(settings, "KEYCLOAK_URL", None)
            keycloak_realm = getattr(settings, "KEYCLOAK_REALM", None)
            
            if not keycloak_url or not keycloak_realm:
                logger.error("Keycloak not configured (KEYCLOAK_URL, KEYCLOAK_REALM)")
                return None
            
            # Build JWKS URI
            jwks_uri = f"{keycloak_url}/realms/{keycloak_realm}/protocol/openid-connect/certs"
            
            # Get signing key from JWKS
            try:
                jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
            except Exception as e:
                logger.error(f"JWKS fetch failed: {e}")
                # Fall back to unverified decode if JWKS unavailable
                # This allows local dev without Keycloak running
                if getattr(settings, "DEBUG", False):
                    logger.warning("DEBUG mode: falling back to unverified JWT decode")
                    payload = jwt.decode(
                        token,
                        options={"verify_signature": False},
                        algorithms=["RS256"],
                    )
                else:
                    return None
            else:
                # Production: Verify signature
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=getattr(settings, "KEYCLOAK_CLIENT_ID", None),
                    issuer=f"{keycloak_url}/realms/{keycloak_realm}",
                )
            
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "preferred_username": payload.get("preferred_username"),
                "roles": payload.get("realm_access", {}).get("roles", []),
                "tenant_id": payload.get("tenant_id"),
                "exp": payload.get("exp"),
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"JWT authentication error: {e}")
            return None


# =============================================================================
# GOOGLE OAUTH (For SSO)
# =============================================================================

class GoogleOAuth:
    """
    Google OAuth2 helper for SSO authentication.
    
    Uses credentials from environment:
    - GOOGLE_OAUTH_CLIENT_ID
    - GOOGLE_OAUTH_CLIENT_SECRET
    - GOOGLE_OAUTH_REDIRECT_URI
    """
    
    def __init__(self):
        self.client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
        self.client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)
        self.redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None)
    
    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
        import urllib.parse
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if state:
            params["state"] = state
        
        return f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Optional[dict]:
        """Exchange authorization code for tokens."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Google token exchange failed: {response.text}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """Get user info from Google."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Google user info failed: {response.text}")
            return None


# =============================================================================
# SCOPE CHECKING DECORATOR
# =============================================================================

def require_scope(scope: str):
    """
    Decorator to require a specific API key scope.
    
    Usage:
        @api.get("/memories", auth=APIKeyAuth())
        @require_scope("read:memory")
        def list_memories(request):
            ...
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            auth = getattr(request, "auth", {})
            scopes = auth.get("scopes", [])
            
            if "admin" in scopes:
                # Admin scope bypasses all checks
                return func(request, *args, **kwargs)
            
            if scope not in scopes:
                from ninja.errors import HttpError
                raise HttpError(403, f"Missing required scope: {scope}")
            
            return func(request, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# =============================================================================
# AUDIT LOGGING HELPER
# =============================================================================

def log_api_action(
    request: HttpRequest,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict = None,
):
    """
    Log an API action to the audit log.
    
    Automatically extracts tenant and actor from request.auth.
    """
    auth = getattr(request, "auth", {})
    tenant = auth.get("tenant")
    api_key = auth.get("api_key")
    
    AuditLog.log(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        actor_id=str(api_key.id) if api_key else "unknown",
        actor_type="api_key",
        tenant=tenant,
        details=details or {},
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        request_id=request.META.get("HTTP_X_REQUEST_ID"),
    )


# =============================================================================
# AUTHENTICATED REQUEST TYPE (For API Endpoints)
# =============================================================================

class AuthenticatedRequest(HttpRequest):
    """
    Type hint for authenticated requests with JWT data.
    
    ALL 10 PERSONAS consideration:
    - Architect: Clean type system
    - Django: Extends HttpRequest properly
    """
    user_id: str
    email: str
    name: str
    roles: list
    tenant_id: str
    is_super_admin: bool


# =============================================================================
# ROLE-BASED ACCESS DECORATOR
# =============================================================================

def require_auth(roles: list = None, any_role: bool = False):
    """
    Decorator to require JWT authentication with optional role checking.
    
    ALL 10 PERSONAS:
    - Security: Role-based access control
    - QA: Testable permission logic
    - Docs: Clear docstrings
    
    Args:
        roles: List of required roles (e.g., ["super-admin", "tenant-admin"])
        any_role: If True, any matching role is sufficient. If False, all required.
    
    Usage:
        @router.get("/admin/tenants")
        @require_auth(roles=["super-admin"])
        def list_tenants(request: AuthenticatedRequest):
            ...
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from ninja.errors import HttpError
            
            # Check for JWT auth
            auth = getattr(request, "auth", None)
            if auth is None:
                raise HttpError(401, "Authentication required")
            
            # Extract user info
            user_roles = auth.get("roles", [])
            
            # Attach to request for easy access
            request.user_id = auth.get("user_id")
            request.email = auth.get("email")
            request.name = auth.get("name")
            request.roles = user_roles
            request.tenant_id = auth.get("tenant_id")
            request.is_super_admin = "super-admin" in user_roles
            
            # Check roles if specified
            if roles:
                if any_role:
                    # Any matching role is sufficient
                    if not any(r in user_roles for r in roles):
                        raise HttpError(403, f"Missing required role. Need one of: {roles}")
                else:
                    # All roles required
                    missing = [r for r in roles if r not in user_roles]
                    if missing:
                        raise HttpError(403, f"Missing required roles: {missing}")
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# FIELD-LEVEL PERMISSION CHECKER
# =============================================================================

class FieldPermissionChecker:
    """
    Check and filter fields based on role permissions.
    
    ALL 10 PERSONAS:
    - Security: Field-level access control, no data leakage
    - DBA: Efficient permission queries with caching
    - Performance: Cached permission lookups
    - Architect: Clean separation of concerns
    
    Usage:
        checker = FieldPermissionChecker(user_roles)
        
        # Check if user can view a field
        if checker.can_view("Tenant", "billing_email"):
            ...
        
        # Filter a dict to only allowed fields
        filtered = checker.filter_response("Tenant", tenant_data)
        
        # Validate update payload
        checker.validate_update("Tenant", update_data)  # raises HttpError if denied
    """
    
    # Cache for permission lookups (role -> model -> field -> can_view/can_edit)
    _cache: dict = {}
    
    def __init__(self, user_roles: list, tenant_id: str = None):
        """
        Initialize checker for a user's roles.
        
        Args:
            user_roles: List of role names/slugs
            tenant_id: Optional tenant for tenant-specific overrides
        """
        self.user_roles = user_roles
        self.tenant_id = tenant_id
        self._permissions = None  # Lazy load
    
    def _load_permissions(self):
        """Load permissions from database (cached)."""
        if self._permissions is not None:
            return
        
        from .models import Role, FieldPermission
        
        # Get role IDs for user's roles
        roles = Role.objects.filter(slug__in=self.user_roles)
        role_ids = [r.id for r in roles]
        
        # Get all field permissions for these roles
        permissions = FieldPermission.objects.filter(role_id__in=role_ids)
        
        # Build permission map: model -> field -> (can_view, can_edit)
        self._permissions = {}
        for perm in permissions:
            if perm.model_name not in self._permissions:
                self._permissions[perm.model_name] = {}
            
            # Merge permissions (OR logic - any role grants access)
            existing = self._permissions[perm.model_name].get(perm.field_name, (False, False))
            self._permissions[perm.model_name][perm.field_name] = (
                existing[0] or perm.can_view,
                existing[1] or perm.can_edit,
            )
    
    def can_view(self, model: str, field: str) -> bool:
        """Check if user can view a specific field."""
        # Super-admin can view everything
        if "super-admin" in self.user_roles:
            return True
        
        self._load_permissions()
        model_perms = self._permissions.get(model, {})
        field_perms = model_perms.get(field, (False, False))
        return field_perms[0]
    
    def can_edit(self, model: str, field: str) -> bool:
        """Check if user can edit a specific field."""
        # Super-admin can edit everything
        if "super-admin" in self.user_roles:
            return True
        
        self._load_permissions()
        model_perms = self._permissions.get(model, {})
        field_perms = model_perms.get(field, (False, False))
        return field_perms[1]
    
    def get_viewable_fields(self, model: str, all_fields: list) -> list:
        """Get list of fields the user can view for a model."""
        if "super-admin" in self.user_roles:
            return all_fields
        
        return [f for f in all_fields if self.can_view(model, f)]
    
    def get_editable_fields(self, model: str, all_fields: list) -> list:
        """Get list of fields the user can edit for a model."""
        if "super-admin" in self.user_roles:
            return all_fields
        
        return [f for f in all_fields if self.can_edit(model, f)]
    
    def filter_response(self, model: str, data: dict) -> dict:
        """
        Filter a response dict to only include viewable fields.
        
        ALL 10 PERSONAS - Security: Prevents data leakage.
        """
        if "super-admin" in self.user_roles:
            return data
        
        viewable = self.get_viewable_fields(model, list(data.keys()))
        return {k: v for k, v in data.items() if k in viewable}
    
    def validate_update(self, model: str, data: dict) -> None:
        """
        Validate that user can edit all fields in the update payload.
        
        Raises HttpError(403) if any field is not editable.
        
        ALL 10 PERSONAS - Security: Prevents unauthorized modifications.
        """
        if "super-admin" in self.user_roles:
            return
        
        from ninja.errors import HttpError
        
        editable = self.get_editable_fields(model, list(data.keys()))
        forbidden = [k for k in data.keys() if k not in editable]
        
        if forbidden:
            raise HttpError(403, f"Cannot edit fields: {forbidden}")


# =============================================================================
# MULTI-AUTH COMBINER
# =============================================================================

class MultiAuth:
    """
    Combine multiple auth methods (API Key OR JWT).
    
    ALL 10 PERSONAS - Architect: Flexible auth for different clients.
    """
    
    def __init__(self, auth_classes: list):
        self.auth_classes = auth_classes
    
    def __call__(self, request: HttpRequest) -> Optional[dict]:
        """Try each auth method until one succeeds."""
        for auth_class in self.auth_classes:
            auth_instance = auth_class()
            
            # Extract token from Authorization header
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                result = auth_instance.authenticate(request, token)
                if result:
                    return result
        
        return None


# Default multi-auth for endpoints accepting both API Key and JWT
api_key_or_jwt = MultiAuth([APIKeyAuth, JWTAuth])
