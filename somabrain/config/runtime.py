from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


_RUNTIME_OVERRIDES_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "..",
        "data",
        "runtime_overrides.json",
    )
)


def _ensure_parent_dir(path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass


def _mode_name() -> str:
    try:
        from somabrain.modes import mode_config  # type: ignore

        mc = mode_config()
        return str(getattr(mc, "name", "full-local") or "full-local")
    except Exception:
        return "full-local"


def _defaults_for_mode(mode: str) -> Dict[str, Any]:
    # Conservative defaults aligned with current codebase behavior.
    base = {
        # Memory weighting tunables
        "memory_enable_weighting": False,
        "memory_phase_priors": "",
        "memory_quality_exp": 1.0,
        # Learning/annealing
        "tau_decay_enabled": True,
        "tau_decay_rate": 0.02,
        "tau_anneal_mode": "",  # "exp"|"linear"|"step"
        "tau_anneal_rate": 0.0,
        "tau_anneal_step_interval": 10,
        "tau_min": 0.05,
        # Entropy capping
        "entropy_cap_enabled": True,
        "entropy_cap": 1.2,
        # Cog/predictor composite + compatibility
        "cog_composite": True,
        "soma_compat": False,
        # Predictor update periods (seconds)
        "state_update_period": 0.5,
        "agent_update_period": 0.7,
        "action_update_period": 0.9,
        # Model versions
        "state_model_ver": "v1",
        "agent_model_ver": "v1",
        "action_model_ver": "v1",
        # Integrator normalization/consistency (metrics-facing)
        "fusion_normalization_enabled": True,
        "drift_detection_enabled": False,
        "integrator_enforce_conf": True,
        "integrator_alpha": 2.0,
        "integrator_alpha_min": 0.1,
        "integrator_alpha_max": 5.0,
        "integrator_target_regret": 0.15,
        "integrator_alpha_eta": 0.05,
        "shadow_ratio": 0.0,
    }
    # For prod, keep the same defaults; overrides are ignored in prod.
    return base


def _load_overrides() -> Dict[str, Any]:
    # Only apply overrides in full-local mode
    if _mode_name() != "full-local":
        return {}
    path = _RUNTIME_OVERRIDES_PATH
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict):
                return {str(k): v for k, v in data.items()}
    except Exception:
        return {}
    return {}


def _merged() -> Dict[str, Any]:
    defaults = _defaults_for_mode(_mode_name())
    ov = _load_overrides()
    if not ov:
        return defaults
    merged = dict(defaults)
    for k, v in ov.items():
        merged[k] = v
    return merged


def get(key: str, default: Optional[Any] = None) -> Any:
    return _merged().get(key, default)


def get_bool(key: str, default: bool = False) -> bool:
    try:
        val = _merged().get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return default
    return default


def get_float(key: str, default: float = 0.0) -> float:
    try:
        val = _merged().get(key, default)
        return float(val)
    except Exception:
        return default


def get_str(key: str, default: str = "") -> str:
    try:
        val = _merged().get(key, default)
        return str(val)
    except Exception:
        return default


def set_overrides(updates: Dict[str, Any]) -> None:
    """Persist overrides to the runtime overrides file (local mode only).

    In prod mode, this still writes for developer convenience but lookups will
    ignore overrides. Caller should treat this as a local dev tool.
    """
    if not isinstance(updates, dict):
        return
    data: Dict[str, Any] = {}
    try:
        if os.path.exists(_RUNTIME_OVERRIDES_PATH):
            with open(_RUNTIME_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                cur = json.load(f) or {}
                if isinstance(cur, dict):
                    data.update(cur)
    except Exception:
        data = {}
    data.update({str(k): v for k, v in updates.items()})
    try:
        _ensure_parent_dir(_RUNTIME_OVERRIDES_PATH)
        with open(_RUNTIME_OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except Exception:
        pass
