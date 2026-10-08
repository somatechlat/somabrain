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

from somabrain.core.infrastructure_defs import get_redis_url


def _settings_get(name: str, default=None):
    """Safe getattr(settings, name) — LazySettings is truthy when unconfigured."""
    if settings is None:
        return default
    try:
        return getattr(settings, name)
    except Exception:
        return default


def get_redis() -> Redis | None:
    """Get Redis client for per-tenant state persistence.

    Strict mode: requires real Redis (SOMABRAIN_REDIS_URL).
    Returns None if Redis is not available or not required.
    """
    require_backends = _settings_get("REQUIRE_EXTERNAL_BACKENDS", False)
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
            redis_host = _settings_get("REDIS_HOST", None)
            redis_port = _settings_get("REDIS_PORT", None)
            redis_db = _settings_get("REDIS_DB", 0)
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
        _persist_enabled = str(
            _settings_get("ENABLE_LEARNING_STATE_PERSISTENCE", False)
        ).strip().lower() in {"1", "true", "yes", "on"}
    return _persist_enabled


def persist_state(
    redis_client: Redis | None,
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
    from somabrain.brain_settings.models import BRAIN_DEFAULTS
    from somabrain.learning.config import UtilityWeights

    _u = UtilityWeights()
    # Retrieval fallbacks: BrainSetting BRAIN_DEFAULTS (single declaration).
    _alpha = float(retrieval.get("alpha", BRAIN_DEFAULTS["retrieval_alpha"]["v"]))
    _beta = float(retrieval.get("beta", BRAIN_DEFAULTS["retrieval_beta"]["v"]))
    _gamma = float(retrieval.get("gamma", BRAIN_DEFAULTS["retrieval_gamma"]["v"]))
    _tau = float(retrieval.get("tau", BRAIN_DEFAULTS["retrieval_tau"]["v"]))
    state_key = f"adaptation:state:{tenant_id}"
    state_data = json.dumps(
        {
            "retrieval": {
                "alpha": _alpha,
                "beta": _beta,
                "gamma": _gamma,
                "tau": _tau,
            },
            "utility": {
                "lambda_": float(utility.get("lambda_", _u.lambda_)),
                "mu": float(utility.get("mu", _u.mu)),
                "nu": float(utility.get("nu", _u.nu)),
            },
            "feedback_count": int(feedback_count),
            "learning_rate": float(learning_rate),
        }
    )
    redis_client.setex(state_key, ttl_seconds, state_data)


def load_state(redis_client: Redis | None, tenant_id: str) -> dict[str, Any] | None:
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
