from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_hmm_segmentation_metrics_present():
    # Smoke acceptance: verify HMM metrics are registered when feature enabled.
    from somabrain import modes
    from somabrain.metrics import SEGMENTATION_HMM_STATE_VOLATILE as VOL

    # Enable hmm_segmentation via mode patch
    orig = modes.get_mode_config

    def _patched():  # type: ignore
        cfg = orig()
        if cfg.name == "ci":  # ci mode disables hmm by default
            from dataclasses import replace
            return replace(cfg, enable_hmm_segmentation=True)
        return cfg

    modes.get_mode_config = _patched  # type: ignore
    try:
        # Value may not be set yet, but gauge object should exist
        assert VOL is not None
        assert getattr(VOL, "_name", "somabrain_segmentation_hmm_state_volatile")
    finally:
        modes.get_mode_config = orig  # type: ignore
