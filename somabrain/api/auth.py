"""Django Ninja Authentication Handlers

VIBE COMPLIANT: Real implementations only - no placeholders.

This module provides auth handlers by re-exporting from the production
aaas.auth module. All auth logic is centralized there.
"""

# Re-export all auth classes from the real implementation
from somabrain.aaas.auth import APIKeyAuth, GoogleOAuth, JWTAuth

# Canonical auth handlers
api_key_auth = APIKeyAuth()
jwt_auth = JWTAuth()
google_oauth = GoogleOAuth()
