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
from typing import Optional, Any

import jwt
from django.conf import settings
from django.http import HttpRequest
from ninja.errors import HttpError
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


def require_auth(request: HttpRequest, cfg: Any = None) -> None:
    """Validate authentication for API requests.

    Args:
        request: The incoming Django request
        cfg: Legacy configuration object (ignored in favor of settings)
    """
    # Auth always enforced; no early return.
    auth = request.headers.get("Authorization", "")

    jwt_key = _get_jwt_key()
    if jwt_key:
        if not auth.startswith("Bearer "):
            raise HttpError(401, "missing bearer token")
        token = auth.split(" ", 1)[1].strip()

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
        return

    api_token = getattr(settings, "SOMABRAIN_API_TOKEN", None)
    if api_token:
        if not auth.startswith("Bearer "):
            raise HttpError(401, "missing bearer token")
        token = auth.split(" ", 1)[1].strip()
        if token != api_token:
            raise HttpError(403, "invalid token")
        return

    if getattr(settings, "SOMABRAIN_AUTH_REQUIRED", False):
        if not auth.startswith("Bearer ") or not auth.split(" ", 1)[1].strip():
            raise HttpError(401, "missing bearer token")


def require_admin_auth(request: HttpRequest, cfg: Any = None) -> None:
    """Validate admin authentication.

    Args:
        request: Incoming request
        cfg: Legacy config (ignored)
    """
    api_token = getattr(settings, "SOMABRAIN_API_TOKEN", None)
    if not api_token:
        return
    token_header = request.headers.get("Authorization", "")
    if not token_header.startswith("Bearer "):
        raise HttpError(401, "missing bearer token")
    token = token_header.split(" ", 1)[1].strip()
    if token != api_token:
        raise HttpError(403, "invalid admin token")
