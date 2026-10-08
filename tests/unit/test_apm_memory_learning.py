"""APM-1 behavioural tests: memory events move AdaptationEngine weights.

No source-grep. RED/GREEN proves the brain learns from interactions.
``no_django``: engine is constructed with explicit weights (no BrainSetting).
"""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.no_django

from somabrain.learning.adaptation.engine import AdaptationEngine
from somabrain.learning.adaptation.types import RetrievalWeights
from somabrain.learning.config import UtilityWeights
from somabrain.learning.memory_events import (
    apply_memory_event,
    signal_for_event,
)
from somabrain.math.contracts import MEMORY_EVENT_SIGNALS


def _engine() -> AdaptationEngine:
    return AdaptationEngine(
        retrieval=RetrievalWeights(1.0, 0.3, 0.5, 0.7),
        utility=UtilityWeights(),
        learning_rate=0.1,
        max_history=16,
        tenant_id="t-apm-test",
        enable_dynamic_lr=False,
    )


class TestMemoryEventSignals:
    def test_signal_table_has_signed_miss(self):
        assert MEMORY_EVENT_SIGNALS["recall_hit"] > 0
        assert MEMORY_EVENT_SIGNALS["recall_miss"] < 0
        assert MEMORY_EVENT_SIGNALS["promote_success"] > 0

    def test_nan_utility_rejected(self):
        assert signal_for_event("recall_hit", utility=float("nan")) is None

    def test_signal_clamped(self):
        s = signal_for_event("recall_hit", utility=99.0)
        assert s is not None and s <= 1.0


class TestApplyMemoryEvent:
    def test_recall_hit_moves_alpha_up(self):
        eng = _engine()
        before = eng.alpha
        ok = eng.apply_memory_event("recall_hit")
        assert ok is True
        assert eng.alpha > before

    def test_recall_miss_moves_alpha_down(self):
        eng = _engine()
        # first push alpha up so there is room to fall
        eng.apply_memory_event("recall_hit")
        before = eng.alpha
        ok = eng.apply_memory_event("recall_miss")
        assert ok is True
        assert eng.alpha < before

    def test_promote_success_learns(self):
        eng = _engine()
        before = eng.alpha
        assert eng.apply_memory_event("promote_success") is True
        assert eng.alpha != before

    def test_nan_event_does_not_poison(self):
        eng = _engine()
        before = eng.alpha
        assert eng.apply_memory_event("recall_hit", utility=float("nan")) is False
        assert eng.alpha == before
        assert math.isfinite(eng.alpha)

    def test_module_hook_isolated_per_tenant(self):
        a = apply_memory_event("recall_hit", tenant_id="iso-a")
        b = apply_memory_event("recall_miss", tenant_id="iso-b")
        assert a is True and b is True
        # tenants must not share one engine object
        from somabrain.learning import memory_events as me

        assert me._ENGINE_CACHE.get("iso-a") is not me._ENGINE_CACHE.get("iso-b")

    def test_feedback_still_works(self):
        eng = _engine()
        before = eng.alpha
        assert eng.apply_feedback(1.0) is True
        assert eng.alpha != before


class TestBoundsAndFinite:
    def test_projection_after_many_hits(self):
        eng = _engine()
        for _ in range(200):
            eng.apply_memory_event("recall_hit")
        assert math.isfinite(eng.alpha)
        assert eng.alpha <= 5.0 + 1e-9

    def test_weight_delta_nonfinite_is_zero(self):
        from somabrain.learning.adaptation.utils import weight_delta

        assert weight_delta(0.1, 1.0, float("nan")) == 0.0
        assert weight_delta(0.1, 1.0, 1.0) != 0.0
