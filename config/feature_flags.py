"""
Feature flags view derived from central modes.

This module exposes a stable API for the Features router and tooling while
delegating the source of truth to `somabrain.modes`. Environment-variable based
flags are removed; optional local overrides are persisted in a JSON file and
applied only in `full-local` mode.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

from somabrain.modes import mode_config, feature_enabled


class FeatureFlags:
    """Computed feature flag status.

    Source of truth: `somabrain.modes`. Optional local overrides are stored in
    ``SOMABRAIN_FEATURE_OVERRIDES`` JSON with shape {"disabled": [keys...]}
    and are effective only in `full-local` mode.
    """

    KEYS: List[str] = [
        "hmm_segmentation",
        "fusion_normalization",
        "calibration",
        "consistency_checks",
        "drift_detection",
        "auto_rollback",
    ]

    @staticmethod
    def _load_overrides() -> List[str]:
        path = os.getenv("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
        try:
            p = Path(path)
            if not p.exists():
                return []
            data = json.loads(p.read_text(encoding="utf-8"))
            disabled = data.get("disabled")
            if isinstance(disabled, list):
                return [str(x).strip().lower() for x in disabled]
        except Exception:
            pass
        return []

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        cfg = mode_config()
        disabled = cls._load_overrides() if cfg.name == "full-local" else []

        def resolved(k: str) -> bool:
            # map UI keys -> feature_enabled keys
            mapping = {
                "hmm_segmentation": "hmm_segmentation",
                "fusion_normalization": "fusion_normalization",
                "calibration": "calibration",
                "consistency_checks": "consistency_checks",
                "drift_detection": "drift",
                "auto_rollback": "auto_rollback",
            }
            fk = mapping.get(k, k)
            val = feature_enabled(fk)
            return val and (k not in disabled)

        return {k: resolved(k) for k in cls.KEYS}

    @classmethod
    def set_overrides(cls, disabled: List[str]) -> None:
        """Persist disabled keys to overrides file (full-local only)."""
        cfg = mode_config()
        if cfg.name != "full-local":
            # ignore in prod
            return
        path = os.getenv("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({"disabled": list(disabled)}, indent=2), encoding="utf-8"
            )
        except Exception:
            pass
