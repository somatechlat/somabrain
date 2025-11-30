from __future__ import annotations
import logging
from typing import Optional, Tuple
from common.utils import RedisCache
from somabrain.infrastructure import get_redis_url
from common.logging import logger

"""Utilities to store and retrieve OPA policy and its signature in Redis.

The manager uses the same Redis connection pattern as ``ConstitutionEngine``.
Keys used:
    pass
- ``soma:opa:policy`` – the Rego policy text.
- ``soma:opa:policy:sig`` – hex signature of the policy.
"""





LOGGER = logging.getLogger("somabrain.opa.policy_manager")


def _resolve_redis_url() -> Optional[str]:
    return get_redis_url()


def _redis_cache() -> Optional[RedisCache]:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        url = _resolve_redis_url()
        if not url:
            LOGGER.debug("Redis URL not configured for OPA policy manager")
            return None
        return RedisCache(url, namespace="")
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise


_POLICY_KEY = settings.opa_policy_key
_SIG_KEY = settings.opa_policy_sig_key


def store_policy(policy: str, signature: Optional[str] = None) -> bool:
    """Store ``policy`` and optional ``signature`` in Redis.

    Returns ``True`` on success, ``False`` otherwise.
    """
    cache = _redis_cache()
    if cache is None:
        LOGGER.warning("Redis unavailable – cannot store OPA policy")
        return False
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        cache.set(_POLICY_KEY, policy)
        if signature:
            cache.set(_SIG_KEY, signature)
        return True
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise


def load_policy() -> Tuple[Optional[str], Optional[str]]:
    """Load the stored policy and signature from Redis.

    Returns ``(policy, signature)`` where each may be ``None`` if missing.
    """
    cache = _redis_cache()
    if cache is None:
        return None, None
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        policy = cache.get(_POLICY_KEY)
        sig = cache.get(_SIG_KEY)
        policy_str = str(policy) if policy is not None else None
        sig_str = str(sig) if sig is not None else None
        return policy_str, sig_str
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise


__all__ = ["store_policy", "load_policy"]
