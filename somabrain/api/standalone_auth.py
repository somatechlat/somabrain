"""Bearer-token authentication for SomaBrain.

SomaBrain is an HTTP + containers service that the agent calls. The trust
boundary is a pre-shared bearer token: its value lives in Vault (VIBE Rule 164)
and is read at bootstrap into ``SOMABRAIN_MEMORY_HTTP_TOKEN`` — the same secret
the SFM backend uses, so the in-cluster trust boundary stays one credential.

This is **not** an auth bypass. It is the authentication boundary: any request
that does not present exactly the configured token is rejected, and a request
presenting nothing is rejected too.
"""

from __future__ import annotations

from typing import Any

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
    ) -> dict[str, Any] | None:
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
