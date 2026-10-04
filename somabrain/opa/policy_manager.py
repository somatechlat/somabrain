"""OPA policy persistence.

The generated Rego policy and its signature are stored under the
``SOMABRAIN_OPA_POLICY_KEY`` / ``SOMABRAIN_OPA_POLICY_SIG_KEY`` Redis keys.
Persistence is part of the fail-closed path: a caller that cannot read back
what it wrote must not treat the update as successful.
"""

from __future__ import annotations

import logging

import redis  # type: ignore[import-untyped]

LOGGER = logging.getLogger("somabrain.opa.policy_manager")


def _redis_client():
    """Return a Redis client from the configured topology URL, or None."""
    from somabrain.infrastructure import get_redis_url

    url = get_redis_url()
    if not url:
        return None
    try:
        return redis.from_url(url)
    except Exception as exc:
        LOGGER.error("Redis client construction failed: %s", exc)
        return None


def _policy_key() -> str:
    from django.conf import settings

    return getattr(settings, "SOMABRAIN_OPA_POLICY_KEY", "soma:opa:policy")


def _sig_key() -> str:
    from django.conf import settings

    return getattr(settings, "SOMABRAIN_OPA_POLICY_SIG_KEY", "soma:opa:policy:sig")


def store_policy(policy: str, signature: str) -> bool:
    """Persist the policy body and its signature. False on any failure."""
    if not policy:
        return False
    client = _redis_client()
    if client is None:
        LOGGER.error("Cannot store OPA policy: Redis unavailable")
        return False
    try:
        pipe = client.pipeline()
        pipe.set(_policy_key(), policy)
        if signature:
            pipe.set(_sig_key(), signature)
        pipe.execute()
        # Read-back: a write that does not persist is a failed store.
        stored = client.get(_policy_key())
        if stored is None:
            LOGGER.error("OPA policy store did not persist")
            return False
        return True
    except Exception as exc:
        LOGGER.error("Failed to store OPA policy: %s", exc)
        return False


def load_policy() -> tuple[str | None, str | None]:
    """Return ``(policy, signature)`` from Redis; both None when absent."""
    client = _redis_client()
    if client is None:
        return None, None
    try:
        policy = client.get(_policy_key())
        sig = client.get(_sig_key())
        if isinstance(policy, bytes):
            policy = policy.decode("utf-8")
        if isinstance(sig, bytes):
            sig = sig.decode("utf-8")
        return policy, sig
    except Exception as exc:
        LOGGER.error("Failed to load OPA policy: %s", exc)
        return None, None
