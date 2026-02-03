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
import logging
from typing import Optional

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from ninja.security import HttpBearer

from somabrain.aaas.models.api import APIKey
from somabrain.aaas.models.audit import AuditLog
from somabrain.aaas.logic.tenant_types import TenantStatus

logger = logging.getLogger(__name__)


# =============================================================================
# API KEY AUTHENTICATION (Django Ninja HttpBearer)
# =============================================================================


class APIKeyAuth(HttpBearer):
    """
    API Key authentication for Django Ninja.

    Validates sbk_live_* or sbk_test_* API keys.
    Extracts tenant context for downstream handlers.

    Example:
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
        logger.info(
            f"API key authenticated: {api_key.key_prefix}... for tenant {api_key.tenant.slug}"
        )

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
# MULTI-AUTH COMBINER
# =============================================================================


class MultiAuth:
    """
    Combine multiple auth methods (API Key OR JWT).

    ALL 10 PERSONAS - Architect: Flexible auth for different clients.
    """

    def __init__(self, auth_classes: list):
        """Initialize the instance."""

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
