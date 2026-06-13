"""Standalone authentication strategy for single-tenant Docker deployments.

The production AAAS auth layer validates API keys against the ``aaas_api_keys``
table. In standalone mode the stack is intentionally single-tenant and the
AAAS billing/rate-limiting middleware is disabled, but the API still needs a
real authentication boundary. This class provides that boundary by verifying a
pre-shared bearer token configured in Vault/environment at bootstrap time.

This is **not** an auth bypass; it is the canonical auth strategy for the
standalone deployment profile.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer


class StandaloneAPIKeyAuth(HttpBearer):
    """Bearer-token authentication for the standalone single-tenant profile.

    Validates the ``Authorization: Bearer <token>`` header against the
    configured ``SOMABRAIN_MEMORY_HTTP_TOKEN``. The token is seeded into Vault
    during standalone bootstrap and is the same secret the SFM backend uses,
    keeping the in-cluster trust boundary simple and consistent.
    """

    def authenticate(
        self, request: HttpRequest, token: str
    ) -> Optional[Dict[str, Any]]:
        expected = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", "")
        if not expected or token != expected:
            return None
        tenant_id = getattr(settings, "SOMABRAIN_DEFAULT_TENANT", "standalone")
        return {
            "tenant": None,
            "tenant_id": tenant_id,
            "tenant_slug": tenant_id,
            "api_key": None,
            "api_key_id": "",
            "scopes": ["memory:read", "memory:write", "admin:read"],
            "is_test": False,
        }
