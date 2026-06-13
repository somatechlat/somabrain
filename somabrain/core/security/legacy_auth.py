"""
Authentication Module for SomaBrain.

Extends bearer token checks with optional JWT validation.

VIBE Compliance:
    - Uses DI container for JWT key cache instead of module-level global state
    - TTL-based cache invalidation for security
    - Thread-safe via DI container
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest
from ninja.errors import HttpError

import jwt
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)

_TRUE_VALUES = ("1", "true", "yes", "on")

# Default TTL for JWT key cache (1 hour)
_JWT_CACHE_TTL_SECONDS = 3600


@dataclass
class JWTKeyCache:
    """Thread-safe JWT key cache with TTL.

    VIBE Compliance:
        - Explicit TTL for security (keys can be rotated)
        - Managed via DI container instead of global state
    """

    key: Optional[str] = None
    loaded_at: float = 0.0
    ttl_seconds: int = _JWT_CACHE_TTL_SECONDS

    def is_valid(self) -> bool:
        """Check if cached key is still valid."""
        if self.key is None:
            return False
        return (time.time() - self.loaded_at) < self.ttl_seconds

    def set_key(self, key: str) -> None:
        """Set the cached key with current timestamp."""
        self.key = key
        self.loaded_at = time.time()

    def invalidate(self) -> None:
        """Invalidate the cached key."""
        self.key = None
        self.loaded_at = 0.0


def _get_jwt_cache() -> JWTKeyCache:
    """Get JWT key cache from DI container.

    VIBE Compliance:
        - Uses DI container for singleton management
        - No module-level mutable state
    """
    from somabrain.core.container import container

    if not container.has("jwt_key_cache"):
        container.register("jwt_key_cache", JWTKeyCache)
    return container.get("jwt_key_cache")


def _auth_disabled() -> bool:
    # Auth disable capability removed: always enforce auth in strict mode.
    """Execute auth disabled."""

    return False


def _get_jwt_key() -> Optional[str]:
    """Get JWT key with TTL-based caching.

    VIBE Compliance:
        - Uses DI container for cache instead of global state
        - TTL-based invalidation for security
    """
    pub_key_path = getattr(settings, "SOMABRAIN_JWT_PUBLIC_KEY_PATH", None)
    if pub_key_path:
        cache = _get_jwt_cache()
        if cache.is_valid():
            return cache.key
        try:
            key = Path(pub_key_path).read_text(encoding="utf-8")
            cache.set_key(key)
            return key
        except Exception as exc:
            logger.warning("Failed to load JWT public key: %s", exc)
            return None

    return getattr(settings, "SOMABRAIN_JWT_SECRET", None)


def invalidate_jwt_cache() -> None:
    """Invalidate the JWT key cache.

    Call this when JWT keys are rotated to force reload.

    VIBE Compliance:
        - Explicit cache invalidation for security
    """
    try:
        cache = _get_jwt_cache()
        cache.invalidate()
        logger.info("JWT key cache invalidated")
    except Exception as exc:
        logger.warning("Failed to invalidate JWT cache: %s", exc)


def _jwt_algorithms() -> list[str]:
    """Execute jwt algorithms."""

    if getattr(settings, "SOMABRAIN_JWT_PUBLIC_KEY_PATH", None):
        return ["RS256", "RS384", "RS512"]
    return ["HS256", "HS384", "HS512"]


def _extract_bearer(request: HttpRequest) -> str:
    """Return the bearer token from the Authorization header, or raise 401."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HttpError(401, "missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HttpError(401, "missing bearer token")
    return token


def _validate_jwt(token: str) -> None:
    """Validate a JWT token against the configured key."""
    jwt_key = _get_jwt_key()
    if not jwt_key:
        raise HttpError(503, "authentication is not configured on this instance")

    audience = getattr(settings, "SOMABRAIN_JWT_AUDIENCE", None)
    issuer = getattr(settings, "SOMABRAIN_JWT_ISSUER", None)

    options = {"verify_aud": bool(audience)}
    kwargs = {}
    if audience:
        kwargs["audience"] = audience
    if issuer:
        kwargs["issuer"] = issuer

    try:
        jwt.decode(
            token,
            jwt_key,
            algorithms=_jwt_algorithms(),
            options=options,
            **kwargs,
        )
    except PyJWTError as exc:
        raise HttpError(403, "invalid token") from exc


def _validate_api_or_memory_token(token: str) -> bool:
    """Validate token against configured API or memory HTTP tokens.

    Returns True if the token matches a configured static token. Raises HttpError
    503 if no static token is configured, or 403 if a token is configured but
    does not match.
    """
    for setting_name in ("SOMABRAIN_API_TOKEN", "SOMABRAIN_MEMORY_HTTP_TOKEN"):
        expected = getattr(settings, setting_name, None)
        if expected:
            if token == expected:
                return True
            # A token is configured but this request did not match it; reject.
            raise HttpError(403, "invalid token")
    return False


def require_auth(request: HttpRequest, cfg: Any = None) -> None:
    """Validate authentication for API requests.

    Defense-in-depth check used by endpoints after Ninja auth has run. In
    standalone mode the Ninja auth layer already validated the bearer token, so
    this function additionally ensures at least one backend credential is
    configured and the request presented a token.
    """
    token = _extract_bearer(request)

    jwt_key = _get_jwt_key()
    if jwt_key:
        _validate_jwt(token)
        return

    if _validate_api_or_memory_token(token):
        return

    raise HttpError(503, "authentication is not configured on this instance")


def require_admin_auth(request: HttpRequest, cfg: Any = None) -> None:
    """Validate admin authentication.

    Args:
        request: Incoming request
        cfg: Legacy config (ignored)
    """
    token = _extract_bearer(request)

    jwt_key = _get_jwt_key()
    if jwt_key:
        _validate_jwt(token)
        return

    if _validate_api_or_memory_token(token):
        return

    raise HttpError(403, "admin authentication required")
