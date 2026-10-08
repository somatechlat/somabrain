"""BrainSetting admin API surface — registry + bounds (behavioural)."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
pytestmark = pytest.mark.no_django
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _unit_settings import configure_unit_settings
configure_unit_settings()
import django
if not django.apps.apps.ready:
    django.setup()

from somabrain.brain_settings.models import BRAIN_DEFAULTS


class TestBrainSettingAdminSurface:
    def test_registry_has_prune_and_learnable(self):
        assert "memory_decay_rate" in BRAIN_DEFAULTS
        assert "wm_prune_threshold" in BRAIN_DEFAULTS
        assert BRAIN_DEFAULTS["adapt_lr"].get("learnable") is True

    def test_prune_bounds(self):
        meta = BRAIN_DEFAULTS["memory_decay_rate"]
        assert meta["min"] == 0.0 and meta["max"] == 0.5

    def test_use_hrr_default_true(self):
        assert BRAIN_DEFAULTS["use_hrr"]["v"] is True
