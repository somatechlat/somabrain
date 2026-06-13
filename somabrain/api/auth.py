"""Django Ninja Authentication Handlers

VIBE COMPLIANT: Real implementations only - no placeholders.

This module provides auth handlers. In multi-tenant deployments it re-exports
from the production AAAS auth module. In standalone mode it uses a dedicated
single-tenant token strategy so the API remains protected without requiring
the full AAAS schema.
"""

from __future__ import annotations

from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer

from somabrain.aaas.auth import APIKeyAuth as _APIKeyAuth
from somabrain.aaas.auth import GoogleOAuth, JWTAuth
from somabrain.api.standalone_auth import StandaloneAPIKeyAuth
from somabrain.core.security import legacy_auth as _legacy_auth


# Canonical defense-in-depth auth helpers used by endpoints.
require_auth = _legacy_auth.require_auth
require_admin_auth = _legacy_auth.require_admin_auth


class _AdaptiveAPIKeyAuth(HttpBearer):
    """Dispatches to AAAS API key auth or standalone token auth.

    Standalone mode is detected via ``settings.SOMABRAIN_DEFAULT_TENANT``,
    which the standalone settings module pins to ``"standalone"``. This keeps
    the dispatch explicit and avoids importing deployment-specific modules at
    auth import time.
    """

    def __init__(self) -> None:
        self._standalone = StandaloneAPIKeyAuth()
        self._aaas = _APIKeyAuth()

    def authenticate(
        self, request: HttpRequest, token: str
    ) -> Optional[dict[str, Any]]:
        if getattr(settings, "SOMABRAIN_DEFAULT_TENANT", None) == "standalone":
            return self._standalone.authenticate(request, token)
        return self._aaas.authenticate(request, token)


# Canonical auth handlers
api_key_auth = _AdaptiveAPIKeyAuth()
jwt_auth = JWTAuth()
google_oauth = GoogleOAuth()
