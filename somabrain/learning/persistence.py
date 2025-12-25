"""Redis state persistence for the adaptation engine.

This module handles persisting and loading adaptation state to/from Redis
for per-tenant state management.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis import Redis

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.infrastructure import get_redis_url


def get_redis() -> "Redis | None":
    """Get Redis client for per-tenant state persistence.

    Strict mode: requires real Redis (SOMABRAIN_REDIS_URL).
    Returns None if Redis is not available or not required.
    """
    require_backends = (
        getattr(settings, "require_external_backends", False) if settings else False
    )
    require_backends = str(require_backends).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if require_backends:
        try:
            redis_url = get_redis_url()
            if redis_url:
                redis_url = redis_url.strip()
            import redis

            if redis_url:
                return redis.from_url(redis_url)
            redis_host = getattr(settings, "redis_host", None) if settings else None
            redis_port = getattr(settings, "redis_port", None) if settings else None
            redis_db = getattr(settings, "redis_db", 0) if settings else 0
            if redis_host and redis_port:
                return redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
        except Exception:
            pass
    return None


def is_persistence_enabled() -> bool:
    """Check if learning state persistence is enabled."""
    _persist_enabled = False
    try:
        from somabrain import runtime_config as _rt

        _persist_enabled = _rt.get_bool("learning_state_persistence", False)
    except Exception:
        pass
    if not _persist_enabled:
        if settings:
            _persist_enabled = str(
                getattr(settings, "enable_learning_state_persistence", "")
            ).strip().lower() in {"1", "true", "yes", "on"}
    return _persist_enabled


def persist_state(
    redis_client: "Redis | None",
    tenant_id: str,
    retrieval: dict[str, float],
    utility: dict[str, float],
    feedback_count: int,
    learning_rate: float,
    ttl_seconds: int = 7 * 24 * 3600,
) -> None:
    """Persist adaptation state to Redis.

    Args:
        redis_client: Redis client instance (or None to skip)
        tenant_id: Tenant identifier
        retrieval: Retrieval weights dict with alpha, beta, gamma, tau
        utility: Utility weights dict with lambda_, mu, nu
        feedback_count: Number of feedback events processed
        learning_rate: Current learning rate
        ttl_seconds: Time-to-live for the state key (default 7 days)
    """
    if not redis_client:
        return
    state_key = f"adaptation:state:{tenant_id}"
    state_data = json.dumps(
        {
            "retrieval": {
                "alpha": float(retrieval.get("alpha", 1.0)),
                "beta": float(retrieval.get("beta", 0.2)),
                "gamma": float(retrieval.get("gamma", 0.1)),
                "tau": float(retrieval.get("tau", 0.7)),
            },
            "utility": {
                "lambda_": float(utility.get("lambda_", 1.0)),
                "mu": float(utility.get("mu", 0.1)),
                "nu": float(utility.get("nu", 0.05)),
            },
            "feedback_count": int(feedback_count),
            "learning_rate": float(learning_rate),
        }
    )
    redis_client.setex(state_key, ttl_seconds, state_data)


def load_state(redis_client: "Redis | None", tenant_id: str) -> dict[str, Any] | None:
    """Load adaptation state from Redis.

    Args:
        redis_client: Redis client instance (or None)
        tenant_id: Tenant identifier

    Returns:
        State dict with retrieval, utility, feedback_count, learning_rate
        or None if not found/error
    """
    if not redis_client:
        return None
    state_key = f"adaptation:state:{tenant_id}"
    state_data = redis_client.get(state_key)
    if not state_data:
        return None
    try:
        return json.loads(state_data)
    except Exception:
        return None
