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

try:
    import redis
except Exception:  # pragma: no cover – optional dependency
    redis = None

LOGGER = logging.getLogger("somabrain.opa.policy_manager")


def _connect_redis() -> Optional[object]:
    """Create a Redis client using environment variables.

    Returns ``None`` if Redis is unavailable.
    """
    if redis is None:
        return None
    url = os.getenv("SOMA_REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        return redis.Redis.from_url(url, socket_connect_timeout=2)
    except Exception as e:
        LOGGER.debug("Redis connection failed in policy manager: %s", e)
        return None


_POLICY_KEY = os.getenv("SOMA_OPA_POLICY_KEY", "soma:opa:policy")
_SIG_KEY = os.getenv("SOMA_OPA_POLICY_SIG_KEY", f"{_POLICY_KEY}:sig")


def store_policy(policy: str, signature: Optional[str] = None) -> bool:
    """Store ``policy`` and optional ``signature`` in Redis.

    Returns ``True`` on success, ``False`` otherwise.
    """
    client = _connect_redis()
    if client is None:
        LOGGER.warning("Redis unavailable – cannot store OPA policy")
        return False
    try:
        client.set(_POLICY_KEY, policy)
        if signature:
            client.set(_SIG_KEY, signature)
        return True
    except Exception as e:
        LOGGER.error("Failed to store OPA policy in Redis: %s", e)
        return False


def load_policy() -> Tuple[Optional[str], Optional[str]]:
    """Load the stored policy and signature from Redis.

    Returns ``(policy, signature)`` where each may be ``None`` if missing.
    """
    client = _connect_redis()
    if client is None:
        return None, None
    try:
        policy = client.get(_POLICY_KEY)
        sig = client.get(_SIG_KEY)
        # Decode bytes to str if present
        policy_str = (
            policy.decode("utf-8") if isinstance(policy, (bytes, bytearray)) else None
        )
        sig_str = sig.decode("utf-8") if isinstance(sig, (bytes, bytearray)) else None
        return policy_str, sig_str
    except Exception as e:
        LOGGER.error("Failed to load OPA policy from Redis: %s", e)
        return None, None


__all__ = ["store_policy", "load_policy"]
