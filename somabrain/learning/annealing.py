"""Tau annealing and entropy cap logic for the adaptation engine.

This module handles:
- Tau decay (exponential decay of tau parameter)
- Tau annealing (linear, exponential, step-based annealing)
- Entropy cap enforcement

PERFORMANCE: Uses Rust native functions when available for hot path optimization.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

try:
    from django.conf import settings
except Exception:  # pragma: no cover - optional dependency
    settings = None

from somabrain.learning.tenant_cache import get_tenant_override

# ==================== Rust Bridge ====================
# Use Rust native functions for hot path optimization

try:
    import somabrain_rs as _rs
    RUST_ANNEALING_AVAILABLE = True
    logger.debug("✅ Rust annealing functions loaded")
except ImportError:
    _rs = None
    RUST_ANNEALING_AVAILABLE = False
    logger.debug("⚠️ Rust annealing not available - using Python fallback")


def _rust_apply_tau_annealing(
    tau: float, mode: str, rate: float, step: int, interval: int, tau_min: float
) -> float:
    """Apply tau annealing using Rust native function."""
    if RUST_ANNEALING_AVAILABLE and _rs is not None:
        return _rs.apply_tau_annealing(tau, mode, rate, step, interval, tau_min)
    # Python fallback
    if mode == "linear":
        return max(tau_min, tau - rate)
    elif mode in {"exp", "exponential"}:
        return max(tau_min, tau * math.exp(-rate))
    elif mode == "step":
        if interval > 0 and step % interval == 0 and step > 0:
            return max(tau_min, tau * (1.0 - rate))
    return tau


def _rust_compute_entropy(probs: list[float]) -> float:
    """Compute Shannon entropy using Rust native function."""
    if RUST_ANNEALING_AVAILABLE and _rs is not None:
        return _rs.compute_entropy(probs)
    # Python fallback
    return -sum(p * math.log(p) for p in probs if p > 0)



def get_annealing_config(tenant_id: str, tenant_override: dict | None = None) -> dict:
    """Get tau annealing configuration from settings and tenant overrides.

    Args:
        tenant_id: Tenant identifier
        tenant_override: Optional pre-loaded tenant override dict

    Returns:
        Dict with anneal_mode, anneal_rate, anneal_step_interval, tau_min
    """
    try:
        from somabrain import runtime_config as _rt

        env_mode = getattr(settings, "tau_anneal_mode", None) if settings else None
        env_rate = getattr(settings, "tau_anneal_rate", None) if settings else None
        env_step = (
            getattr(settings, "tau_anneal_step_interval", None) if settings else None
        )
        env_tau_min = getattr(settings, "tau_min", None) if settings else None

        anneal_mode = (
            str(env_mode).strip().lower()
            if env_mode is not None
            else _rt.get_str("tau_anneal_mode", "").strip().lower()
        )
        anneal_rate = (
            float(env_rate)
            if env_rate is not None
            else _rt.get_float("tau_anneal_rate", 0.0)
        )
        anneal_step_interval = (
            int(env_step)
            if env_step is not None
            else int(_rt.get_float("tau_anneal_step_interval", 10))
        )
        tau_min = (
            float(env_tau_min)
            if env_tau_min is not None
            else _rt.get_float("tau_min", 0.05)
        )
    except Exception:
        anneal_mode = ""
        anneal_rate = 0.0
        anneal_step_interval = 10
        tau_min = 0.05

    # Apply tenant-specific overrides
    ov = tenant_override if tenant_override is not None else {}
    if isinstance(ov.get("tau_anneal_mode"), str):
        anneal_mode = str(ov.get("tau_anneal_mode", anneal_mode)).strip().lower()
    if isinstance(ov.get("tau_anneal_rate"), (int, float)):
        anneal_rate = float(ov.get("tau_anneal_rate", anneal_rate))
    if isinstance(ov.get("tau_min"), (int, float)):
        tau_min = float(ov.get("tau_min", tau_min))
    if isinstance(ov.get("tau_step_interval"), (int, float)):
        anneal_step_interval = int(ov.get("tau_step_interval", anneal_step_interval))

    return {
        "anneal_mode": anneal_mode,
        "anneal_rate": anneal_rate,
        "anneal_step_interval": anneal_step_interval,
        "tau_min": tau_min,
    }


def get_decay_config(tenant_id: str, tenant_override: dict | None = None) -> dict:
    """Get tau decay configuration from settings and tenant overrides.

    Args:
        tenant_id: Tenant identifier
        tenant_override: Optional pre-loaded tenant override dict

    Returns:
        Dict with enable_tau_decay, tau_decay_rate
    """
    enable_tau_decay = False
    tau_decay_rate = 0.0
    try:
        from somabrain import runtime_config as _rt

        env_enable = getattr(settings, "tau_decay_enabled", None) if settings else None
        env_rate = getattr(settings, "tau_decay_rate", None) if settings else None
        enable_tau_decay = (
            (str(env_enable).strip().lower() in {"1", "true", "yes", "on"})
            if env_enable is not None
            else _rt.get_bool("tau_decay_enabled", False)
        )
        tau_decay_rate = (
            float(env_rate)
            if env_rate is not None
            else _rt.get_float("tau_decay_rate", 0.0)
        )
    except Exception:
        pass

    ov = tenant_override if tenant_override is not None else {}
    if isinstance(ov.get("tau_decay_rate"), (int, float)):
        tau_decay_rate = float(ov["tau_decay_rate"])

    return {
        "enable_tau_decay": enable_tau_decay,
        "tau_decay_rate": tau_decay_rate,
    }


def apply_tau_annealing(
    current_tau: float,
    tenant_id: str,
    feedback_count: int,
    tenant_override: dict | None = None,
) -> tuple[float, bool]:
    """Apply tau annealing based on configuration.

    Args:
        current_tau: Current tau value
        tenant_id: Tenant identifier
        feedback_count: Number of feedback events (for step-based annealing)
        tenant_override: Optional pre-loaded tenant override dict

    Returns:
        Tuple of (new_tau, was_annealed)
    """
    config = get_annealing_config(tenant_id, tenant_override)
    anneal_mode = config["anneal_mode"]
    anneal_rate = config["anneal_rate"]
    anneal_step_interval = config["anneal_step_interval"]
    tau_min = config["tau_min"]

    if not anneal_mode or anneal_rate <= 0.0:
        return current_tau, False

    old_tau = float(current_tau)
    applied_anneal = False
    new_tau = old_tau

    if anneal_mode in {"exp", "exponential"}:
        # Exponential mode doesn't apply per-feedback annealing
        new_tau = old_tau
    elif anneal_mode == "linear":
        new_tau = old_tau * (1.0 - anneal_rate)
        applied_anneal = True
    elif anneal_mode == "step":
        next_count = feedback_count + 1
        if next_count % max(1, anneal_step_interval) == 0:
            new_tau = old_tau * (1.0 - anneal_rate)
            applied_anneal = True

    if applied_anneal:
        new_tau = max(tau_min, new_tau)
        try:
            from somabrain import metrics as _metrics

            _metrics.tau_anneal_events.labels(tenant_id=tenant_id).inc()
        except Exception:
            pass

    return new_tau, applied_anneal


def apply_tau_decay(
    current_tau: float,
    tenant_id: str,
    tenant_override: dict | None = None,
    skip_if_annealed: bool = True,
    was_annealed: bool = False,
) -> float:
    """Apply tau decay if enabled.

    Args:
        current_tau: Current tau value
        tenant_id: Tenant identifier
        tenant_override: Optional pre-loaded tenant override dict
        skip_if_annealed: Skip decay if annealing was already applied
        was_annealed: Whether annealing was applied this cycle

    Returns:
        New tau value
    """
    if skip_if_annealed and was_annealed:
        return current_tau

    config = get_decay_config(tenant_id, tenant_override)
    enable_tau_decay = config["enable_tau_decay"]
    tau_decay_rate = config["tau_decay_rate"]

    if not enable_tau_decay or tau_decay_rate <= 0:
        return current_tau

    old_tau = float(current_tau)
    new_tau = old_tau * (1.0 - tau_decay_rate)
    new_tau = max(0.05, new_tau)

    try:
        from somabrain import metrics as _metrics

        _metrics.tau_decay_events.labels(tenant_id=tenant_id).inc()
    except Exception:
        pass

    return new_tau


def get_entropy_cap(tenant_id: str) -> float:
    """Get entropy cap configuration.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Entropy cap value (0.0 means disabled)
    """
    try:
        from somabrain import runtime_config as _rt

        env_cap = getattr(settings, "entropy_cap", None) if settings else None
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
) -> None:
    """Check if retrieval weights exceed entropy cap.

    Args:
        alpha, beta, gamma, tau: Retrieval weight values
        tenant_id: Tenant identifier

    Raises:
        RuntimeError: If entropy exceeds configured cap
    """
    entropy_cap = get_entropy_cap(tenant_id)
    if entropy_cap <= 0.0:
        return

    vec = [
        max(1e-9, float(alpha)),
        max(1e-9, float(beta)),
        max(1e-9, float(gamma)),
        max(1e-9, float(tau)),
    ]
    s = sum(vec)
    probs = [v / s for v in vec]

    # Use Rust native entropy computation for hot path
    entropy = _rust_compute_entropy(probs)

    if entropy > entropy_cap:
        try:
            from somabrain import metrics as _metrics

            _metrics.update_learning_retrieval_entropy(tenant_id, entropy)
            _metrics.entropy_cap_events.labels(tenant_id=tenant_id).inc()
        except Exception:
            pass
        raise RuntimeError(
            f"Entropy: {entropy:.4f} exceeds configured cap {entropy_cap:.4f} for tenant {tenant_id}"
        )



# Utility functions for manual tau annealing calculations


def linear_decay(tau_0: float, tau_min: float, alpha: float, t: int) -> float:
    """Linear tau annealing using Rust native function.

    Args:
        tau_0: Initial tau value
        tau_min: Minimum tau value
        alpha: Decay rate
        t: Time step

    Returns:
        Annealed tau value
    """
    if RUST_ANNEALING_AVAILABLE and _rs is not None:
        return _rs.linear_tau_decay(tau_0, tau_min, alpha, t)
    return max(float(tau_min), float(tau_0) - float(alpha) * (int(t) + 1))


def exponential_decay(tau_0: float, gamma: float, t: int) -> float:
    """Exponential tau annealing using Rust native function.

    Args:
        tau_0: Initial tau value
        gamma: Decay factor (0 < gamma < 1)
        t: Time step

    Returns:
        Annealed tau value
    """
    if RUST_ANNEALING_AVAILABLE and _rs is not None:
        return _rs.exponential_tau_decay(tau_0, gamma, t)
    return float(tau_0) * (float(gamma) ** (int(t) + 1))

