"""Per-tenant configuration overrides for context building.

Extracted from context/builder.py per monolithic-decomposition spec.
Provides tenant-specific learning parameter overrides.
"""

from __future__ import annotations

import os
from typing import Any

from django.conf import settings

from somabrain.settings.resolve import require_tenant


def load_tenant_overrides() -> dict[str, dict[str, Any]]:
    """Load per-tenant overrides from YAML/JSON or env JSON string.

    Reads from:
    1. SOMABRAIN_LEARNING_TENANTS_FILE (YAML or JSON file)
    2. LEARNING_TENANTS_OVERRIDES (JSON string in env)

    Returns:
        Dict mapping tenant IDs to their override configurations
    """
    path = settings.SOMABRAIN_LEARNING_TENANTS_FILE
    overrides: dict[str, dict[str, Any]] = {}

    if path and os.path.exists(path):
        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                overrides = {
                    str(k): (v or {}) for k, v in data.items() if isinstance(v, dict)
                }
        except Exception:
            try:
                import json as _json

                with open(path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                if isinstance(data, dict):
                    overrides = {
                        str(k): (v or {})
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
            except Exception:
                overrides = {}

    if not overrides:
        raw = settings.LEARNING_TENANTS_OVERRIDES.strip()
        if raw:
            try:
                import json as _json

                data = _json.loads(raw)
                if isinstance(data, dict):
                    overrides = {
                        str(k): (v or {})
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
            except Exception:
                overrides = {}

    return overrides


def get_entropy_cap_for_tenant(
    tenant_id: str,
    cache: dict[str, dict[str, Any]] | None = None,
) -> float | None:
    """Read entropy_cap from tenant overrides.

    Args:
        tenant_id: Tenant identifier
        cache: Optional cache dict to store/retrieve overrides

    Returns:
        Entropy cap value if configured, None otherwise

    T-5: the lookup key is the real tenant. A missing tenant raises
    (``require_tenant``) instead of reading another partition's overrides.
    """
    t = require_tenant(tenant_id)

    if cache is not None:
        ov = cache.get(t)
        if ov is None:
            ov = load_tenant_overrides().get(t, {})
            cache[t] = ov
    else:
        ov = load_tenant_overrides().get(t, {})

    cap = ov.get("entropy_cap") if isinstance(ov, dict) else None

    try:
        return float(cap) if cap is not None else None
    except Exception:
        return None


def get_tenant_retrieval_weights(
    tenant_id: str,
    cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float] | None:
    """Get per-tenant retrieval weight overrides.

    Args:
        tenant_id: Tenant identifier
        cache: Optional cache dict to store/retrieve overrides

    Returns:
        Dict with alpha, beta, gamma, tau overrides if configured

    T-5: the lookup key is the real tenant. A missing tenant raises
    (``require_tenant``) instead of reading another partition's overrides.
    """
    t = require_tenant(tenant_id)

    if cache is not None:
        ov = cache.get(t)
        if ov is None:
            ov = load_tenant_overrides().get(t, {})
            cache[t] = ov
    else:
        ov = load_tenant_overrides().get(t, {})

    if not isinstance(ov, dict):
        return None

    weights = {}
    for key in ("alpha", "beta", "gamma", "tau"):
        if key in ov:
            try:
                weights[key] = float(ov[key])
            except Exception:
                pass

    return weights if weights else None


def get_tenant_decay_params(
    tenant_id: str,
    cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float] | None:
    """Get per-tenant temporal decay parameter overrides.

    Args:
        tenant_id: Tenant identifier
        cache: Optional cache dict to store/retrieve overrides

    Returns:
        Dict with recency_half_life, recency_sharpness, recency_floor overrides

    T-5: the lookup key is the real tenant. A missing tenant raises
    (``require_tenant``) instead of reading another partition's overrides.
    """
    t = require_tenant(tenant_id)

    if cache is not None:
        ov = cache.get(t)
        if ov is None:
            ov = load_tenant_overrides().get(t, {})
            cache[t] = ov
    else:
        ov = load_tenant_overrides().get(t, {})

    if not isinstance(ov, dict):
        return None

    params = {}
    for key in ("recency_half_life", "recency_sharpness", "recency_floor"):
        if key in ov:
            try:
                params[key] = float(ov[key])
            except Exception:
                pass

    return params if params else None
