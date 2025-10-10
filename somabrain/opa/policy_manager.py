"""Utilities to store and retrieve OPA policy and its signature in Redis.

The manager uses the same Redis connection pattern as ``ConstitutionEngine``.
Keys used:
- ``soma:opa:policy`` – the Rego policy text.
- ``soma:opa:policy:sig`` – hex signature of the policy.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from common.utils import RedisCache

try:  # pragma: no cover - optional dependency
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover
    shared_settings = None  # type: ignore

LOGGER = logging.getLogger("somabrain.opa.policy_manager")


def _resolve_redis_url() -> str:
    env_url = os.getenv("SOMA_REDIS_URL") or os.getenv("SOMABRAIN_REDIS_URL")
    if env_url:
        return env_url
    if shared_settings is not None:
        try:
            return str(getattr(shared_settings, "redis_url", "redis://127.0.0.1:6379/0"))
        except Exception:
            return "redis://127.0.0.1:6379/0"
    return "redis://127.0.0.1:6379/0"


def _redis_cache() -> Optional[RedisCache]:
    try:
        return RedisCache(_resolve_redis_url(), namespace="")
    except Exception as exc:
        LOGGER.debug("Redis cache unavailable in policy manager: %s", exc)
        return None


_POLICY_KEY = os.getenv("SOMA_OPA_POLICY_KEY", "soma:opa:policy")
_SIG_KEY = os.getenv("SOMA_OPA_POLICY_SIG_KEY", f"{_POLICY_KEY}:sig")


def store_policy(policy: str, signature: Optional[str] = None) -> bool:
    """Store ``policy`` and optional ``signature`` in Redis.

    Returns ``True`` on success, ``False`` otherwise.
    """
    cache = _redis_cache()
    if cache is None:
        LOGGER.warning("Redis unavailable – cannot store OPA policy")
        return False
    try:
        cache.set(_POLICY_KEY, policy)
        if signature:
            cache.set(_SIG_KEY, signature)
        return True
    except Exception as e:
        LOGGER.error("Failed to store OPA policy in Redis: %s", e)
        return False


def load_policy() -> Tuple[Optional[str], Optional[str]]:
    """Load the stored policy and signature from Redis.

    Returns ``(policy, signature)`` where each may be ``None`` if missing.
    """
    cache = _redis_cache()
    if cache is None:
        return None, None
    try:
        policy = cache.get(_POLICY_KEY)
        sig = cache.get(_SIG_KEY)
        policy_str = str(policy) if policy is not None else None
        sig_str = str(sig) if sig is not None else None
        return policy_str, sig_str
    except Exception as e:
        LOGGER.error("Failed to load OPA policy from Redis: %s", e)
        return None, None


__all__ = ["store_policy", "load_policy"]
