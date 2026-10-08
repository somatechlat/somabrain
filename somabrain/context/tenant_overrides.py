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
    """Load per-tenant overrides from DB/Django only (no files).

    Authority order (Operator: NO FILE PRESETS):
    1. BrainSetting rows (DB, administrable)
    2. Django settings ``LEARNING_TENANTS_OVERRIDES`` (JSON string)

    File paths are ignored if present — settings must be DB or Django.
    """
    overrides: dict[str, dict[str, Any]] = {}

    try:
        from somabrain.brain_settings.models import BrainSetting

        # Administrable per-tenant knobs already live on BrainSetting.
        # Group learnable keys that context/learning cares about.
        for key in (
            "retrieval_alpha",
            "retrieval_beta",
            "retrieval_gamma",
            "retrieval_tau",
            "entropy_cap",
            "adapt_lr",
            "density_target",
            "density_floor",
            "density_weight",
        ):
            try:
                value = BrainSetting.get(key, None)
            except Exception:
                continue
            if value is None:
                continue
            bucket = overrides.setdefault("default", {})
            bucket[key] = value
    except Exception:
        pass

    raw = ""
    try:
        raw = str(getattr(settings, "LEARNING_TENANTS_OVERRIDES", "") or "").strip()
    except Exception:
        raw = ""
    if raw:
        try:
            import json as _json

            data = _json.loads(raw)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        overrides[str(k)] = {**overrides.get(str(k), {}), **v}
        except Exception:
            pass

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
