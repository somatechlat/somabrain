"""ONE tau anneal law + entropy cap over mixture weights.

Tau schedule (the only one — DEBT-009 FIXED, W3):
    τ ← max(TAU_FLOOR, τ · TAU_DECAY_FACTOR)

The same closed form lives in ``somabrain.math.contracts.anneal_tau`` and is
mirrored by ``somabrain_rs.anneal_tau``.  Callers apply it once per
``TAU_INTERVAL`` seconds (``somabrain.tasks.temperature_anneal``).

Entropy cap (DEBT-010 FIXED, W3): sharpening operates on mixture weights
(α, β, γ) only.  τ is a temperature, not a mass, and is never an input to —
nor an output of — entropy sharpening.
"""

from __future__ import annotations

import logging

from somabrain.math.contracts import (
    TAU_DECAY_FACTOR,
    TAU_FLOOR,
    TAU_INTERVAL,
    anneal_tau,
    entropy_of,
    sharpen_mixture_weights,
)

logger = logging.getLogger(__name__)

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.learning.tenant_cache import get_tenant_override

__all__ = [
    "TAU_DECAY_FACTOR",
    "TAU_FLOOR",
    "TAU_INTERVAL",
    "anneal_tau",
    "apply_tau_annealing",
    "check_entropy_cap",
    "entropy_of",
    "get_entropy_cap",
    "sharpen_mixture_weights",
]


def apply_tau_annealing(current_tau: float) -> float:
    """Apply one geometric anneal step (THE schedule).

    ``τ ← max(TAU_FLOOR, τ · TAU_DECAY_FACTOR)``

    Frequency is the caller's concern (the background task fires every
    ``TAU_INTERVAL`` seconds).  There is no linear/exponential/step mode.
    """
    return anneal_tau(current_tau, TAU_DECAY_FACTOR, TAU_FLOOR)


def get_entropy_cap(tenant_id: str) -> float:
    """Get entropy cap configuration.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Entropy cap value (0.0 means disabled)
    """
    try:
        from somabrain import runtime_config as _rt

        env_cap = getattr(settings, "SOMABRAIN_ENTROPY_CAP", None) if settings else None
        entropy_cap = (
            float(env_cap) if env_cap is not None else _rt.get_float("entropy_cap", 0.0)
        )
    except Exception:
        entropy_cap = 0.0

    ov = get_tenant_override(tenant_id)
    if isinstance(ov.get("entropy_cap"), (int, float)):
        entropy_cap = float(ov["entropy_cap"])

    return entropy_cap


def check_entropy_cap(
    alpha: float,
    beta: float,
    gamma: float,
    tau: float,
    tenant_id: str,
) -> tuple[float, float, float, float, bool]:
    """Entropy-cap the mixture weights (α, β, γ).  τ is returned unchanged.

    τ is a temperature, not a mixture weight.  Folding it into the entropy
    vector used to rescale the annealed temperature (DEBT-010).  The vector
    is therefore ``(α, β, γ)`` only.

    Args:
        alpha, beta, gamma: Mixture weights (semantic / graph / temporal).
        tau: Retrieval temperature — passed through untouched.
        tenant_id: Tenant identifier

    Returns:
        ``(alpha, beta, gamma, tau, was_sharpened)``.
    """
    entropy_cap = get_entropy_cap(tenant_id)
    if entropy_cap <= 0.0:
        return alpha, beta, gamma, tau, False

    try:
        from somabrain.brain_settings.models import BrainSetting

        sharpen_rate = float(BrainSetting.get("entropy_sharpen_rate", tenant_id))
        final_sharpen = float(BrainSetting.get("entropy_final_sharpen", tenant_id))
    except Exception:
        try:
            from django.conf import settings as dj_settings

            sharpen_rate = float(getattr(dj_settings, "SOMABRAIN_ENTROPY_SHARPEN_RATE", 0.8))
            final_sharpen = float(getattr(dj_settings, "SOMABRAIN_ENTROPY_FINAL_SHARPEN", 0.05))
        except Exception:
            sharpen_rate = 0.8
            final_sharpen = 0.05

    sharpened, was_sharpened = sharpen_mixture_weights(
        [alpha, beta, gamma],
        entropy_cap,
        sharpen_rate=sharpen_rate,
        final_sharpen=final_sharpen,
    )
    if not was_sharpened:
        return alpha, beta, gamma, tau, False

    h = entropy_of(sharpened)
    logger.warning(
        "Entropy cap exceeded for tenant %s (H=%.4f > cap=%.4f). "
        "Sharpened mixture weights toward dominant component. tau unchanged.",
        tenant_id,
        h,
        entropy_cap,
    )
    try:
        from somabrain import metrics as _metrics

        _metrics.update_learning_retrieval_entropy(tenant_id, h)
        _metrics.entropy_cap_events.labels(tenant_id=tenant_id).inc()
    except Exception:
        pass

    return sharpened[0], sharpened[1], sharpened[2], float(tau), True
