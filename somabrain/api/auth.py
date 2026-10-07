"""Django Ninja authentication handlers.

The authentication boundary for SomaBrain is a pre-shared bearer token whose
value lives in Vault (VIBE Rule 164) and is read at bootstrap into
``SOMABRAIN_MEMORY_HTTP_TOKEN``. That single token is the trust boundary in
every deployment profile: the agent holds it, SomaBrain verifies it. There is
no second product-identity layer — product auth (JWT/OAuth/API-key product
tables) was removed with the commerce overlay.

``require_auth`` / ``require_admin_auth`` are the defense-in-depth helpers
called inside handlers after Ninja has already authenticated the request.
"""

from __future__ import annotations

from somabrain.api.standalone_auth import StandaloneAPIKeyAuth
from somabrain.core.security import legacy_auth as _legacy_auth

# Defense-in-depth helpers used by endpoints.
require_auth = _legacy_auth.require_auth
require_admin_auth = _legacy_auth.require_admin_auth

# Canonical auth handler used by every route's ``auth=`` argument.
api_key_auth = StandaloneAPIKeyAuth()

__all__ = [
    "api_key_auth",
    "require_auth",
    "require_admin_auth",
]
