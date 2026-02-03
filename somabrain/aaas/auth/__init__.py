from .core import APIKeyAuth, AuthenticatedRequest, MultiAuth, log_api_action
from .oauth import JWTAuth, GoogleOAuth
from .permissions import require_auth, require_scope, FieldPermissionChecker

api_key_or_jwt = MultiAuth([APIKeyAuth, JWTAuth])

__all__ = [
    "APIKeyAuth",
    "AuthenticatedRequest",
    "MultiAuth",
    "log_api_action",
    "JWTAuth",
    "GoogleOAuth",
    "require_auth",
    "require_scope",
    "FieldPermissionChecker",
    "api_key_or_jwt",
]
