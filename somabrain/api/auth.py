"""Django Ninja Authentication Handlers

VIBE COMPLIANT: Real implementations only - no placeholders.

This module provides auth handlers by re-exporting from the production
aaas.auth module. All auth logic is centralized there.
"""

# Re-export all auth classes from the real implementation
from somabrain.aaas.auth import (
    APIKeyAuth,
    GoogleOAuth,
    JWTAuth,
)

# Singleton instances for backward compatibility
# Use these in routers: auth=api_key_auth or auth=jwt_auth
api_key_auth = APIKeyAuth()
jwt_auth = JWTAuth()
google_oauth = GoogleOAuth()

# Legacy aliases (deprecated - use api_key_auth or jwt_auth)
bearer_auth = api_key_auth  # Changed to support sbk_* API keys
admin_auth = api_key_auth  # API key auth includes admin scope checking
tenant_auth = api_key_auth  # API key auth extracts tenant context
