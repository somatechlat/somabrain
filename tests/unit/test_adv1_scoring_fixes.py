"""ADV-1 critical: single recency, NaN fail-closed, no s=1.0 force, H4 copies.

Behavioural acceptance (W5c):
- recency applied once (scorer.score(age_seconds=...); never post-multiplied)
- NaN age → floor (never 1.0)
- NaN score → 0.0 (never 1.0)
- traits never force salience to 1.0
- PersonalityStore.get returns a copy, not the live store object

Production imports only. Marked ``no_django``.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np
import pytest

pytestmark = pytest.mark.no_django


def _configure_settings() -> None:
    from django.conf import settings as dj_settings

    if dj_settings.configured:
        return
    from somabrain.math.contracts import NEURO_BOUNDS

    dj_settings.configure(
        **{
            "SOMABRAIN_EMOTION_DECAY_RATE": 0.0,
            "SOMABRAIN_SALIENCE_W_NOVELTY": 0.6,
            "SOMABRAIN_SALIENCE_W_ERROR": 0.4,
            "SOMABRAIN_SALIENCE_THRESHOLD_STORE": 0.5,
            "SOMABRAIN_SALIENCE_THRESHOLD_ACT": 0.7,
            "SOMABRAIN_SALIENCE_HYSTERESIS": 0.1,
            "SOMABRAIN_USE_SOFT_SALIENCE": False,
            "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE": 0.1,
            "SOMABRAIN_SALIENCE_METHOD": "dense",
            "SOMABRAIN_SALIENCE_FD_WEIGHT": 0.0,
            "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR": 0.9,
            "SOMABRAIN_NEURO_DOPAMINE_BASE": NEURO_BOUNDS["dopamine"][0]
            + 0.2
            * (NEURO_BOUNDS["dopamine"][1] - NEURO_BOUNDS["dopamine"][0]),
            "SOMABRAIN_NEURO_SEROTONIN_BASE": 0.5,
            "SOMABRAIN_NEURO_NORAD_BASE": 0.0,
            "SOMABRAIN_NEURO_ACETYL_BASE": 0.0,
            # somabrain.sleep reads these at class-body evaluation time.
            "SLEEP_K0": 100,
            "SLEEP_T0": 1.0,
            "SLEEP_TAU0": 0.1,
            "SLEEP_ETA0": 0.01,
            "SLEEP_LAMBDA0": 0.5,
            "SLEEP_B0": 1.0,
            "SLEEP_K_MIN": 1,
            "SLEEP_T_MIN": 0.01,
            "SLEEP_ALPHA_K": 0.1,
            "SLEEP_ALPHA_T": 0.1,
            "SLEEP_ALPHA_TAU": 0.1,
            "SLEEP_ALPHA_ETA": 0.1,
            "SLEEP_BETA_B": 0.1,
        }
    )


_configure_settings()

from somabrain.admin.cognitive.personality import PersonalityStore  # noqa: E402
from somabrain.admin.core.learning.scoring import UnifiedScorer  # noqa: E402
from somabrain.math.recency import (  # noqa: E402
    recency_features,
    stretched_exponential_recency,
)
from somabrain.memory.client.ranking import _rescore_and_rank_hits  # noqa: E402
from somabrain.memory.client.types import RecallHit  # noqa: E402
from somabrain.schemas import PersonalityState  # noqa: E402

_SCALE = 60.0
_SHARPNESS = 1.2
_FLOOR = 0.05
_CAP = 1000.0


class _Cfg:
    SOMABRAIN_WM_RECENCY_TIME_SCALE = _SCALE
    SOMABRAIN_WM_RECENCY_MAX_STEPS = _CAP
    SOMABRAIN_RECENCY_SHARPNESS = _SHARPNESS
    SOMABRAIN_RECENCY_FLOOR = _FLOOR
    recall_density_margin_target = 0.2
    recall_density_margin_floor = 0.6
    recall_density_margin_weight = 0.35


class _Embedder:
    def embed(self, text: str) -> np.ndarray:
        return np.ones(8, dtype=float)


class _FixedScoreScorer:
    """Returns a constant score that already includes any recency once."""

    def __init__(self, value: float) -> None:
        self.value = float(value)
        self.seen_ages: list[float | None] = []

    def score(self, query, candidate, *, age_seconds=None, cosine=None) -> float:
        self.seen_ages.append(age_seconds)
        return self.value


class TestSingleRecencyApplication:
    """C1: recency lives inside scorer.score(age_seconds=...), once."""

    def test_old_hit_keeps_scorer_score_not_squared_recency(self) -> None:
        now = datetime.now(UTC).timestamp()
        hit = RecallHit(
            payload={"text": "alpha beta", "timestamp": now - 3600.0},
            score=1.0,
        )
        scorer = _FixedScoreScorer(0.8)
        ranked = _rescore_and_rank_hits(
            _Cfg(), scorer, _Embedder(), [hit], "alpha beta"
        )
        # One recency application lives in the scorer. A second post-multiply
        # would shrink this to 0.8 * R(3600) ≈ 0.8 * floor.
        assert ranked[0].score == pytest.approx(0.8, abs=1e-9)
        # The scorer was given the age so it can apply recency once.
        assert scorer.seen_ages and scorer.seen_ages[0] == pytest.approx(3600.0)

    def test_old_hit_differs_from_double_apply(self) -> None:
        now = datetime.now(UTC).timestamp()
        age = 3600.0
        hit = RecallHit(
            payload={"text": "alpha beta", "timestamp": now - age},
            score=1.0,
        )
        scorer = _FixedScoreScorer(0.8)
        ranked = _rescore_and_rank_hits(
            _Cfg(), scorer, _Embedder(), [hit], "alpha beta"
        )
        _, boost = recency_features(
            age, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR, cap=_CAP
        )
        assert boost < 1.0
        # Double-apply would be 0.8 * boost; single-apply is 0.8.
        assert ranked[0].score != pytest.approx(0.8 * boost, abs=1e-9)
        assert ranked[0].score == pytest.approx(0.8, abs=1e-9)

    def test_fresh_hit_unchanged(self) -> None:
        now = datetime.now(UTC).timestamp()
        hit = RecallHit(
            payload={"text": "alpha beta", "timestamp": now},
            score=1.0,
        )
        scorer = _FixedScoreScorer(0.5)
        ranked = _rescore_and_rank_hits(
            _Cfg(), scorer, _Embedder(), [hit], "alpha beta"
        )
        assert ranked[0].score == pytest.approx(0.5, abs=1e-9)


class TestNanAgeIsFloor:
    """C4: NaN age must return floor, never 1.0."""

    def test_nan_age_returns_floor(self) -> None:
        got = stretched_exponential_recency(
            float("nan"), scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
        )
        assert got == pytest.approx(_FLOOR)
        assert got != 1.0

    def test_nan_age_features_boost_is_floor(self) -> None:
        steps, boost = recency_features(
            float("nan"),
            scale=_SCALE,
            sharpness=_SHARPNESS,
            floor=_FLOOR,
            cap=_CAP,
        )
        assert boost == pytest.approx(_FLOOR)
        assert boost != 1.0
        # Stale-consistent: steps saturate at cap rather than going NaN.
        assert steps == pytest.approx(_CAP)
        assert math.isfinite(steps)

    def test_zero_age_still_one(self) -> None:
        assert (
            stretched_exponential_recency(
                0.0, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
            )
            == 1.0
        )

    def test_positive_infinite_age_is_floor(self) -> None:
        got = stretched_exponential_recency(
            float("inf"), scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
        )
        assert got == pytest.approx(_FLOOR)


class TestNanScoreIsZero:
    """C5: a NaN total must return 0.0, never 1.0."""

    def test_unified_scorer_nan_total_is_zero(self) -> None:
        scorer = UnifiedScorer(
            w_cosine=0.6,
            w_fd=0.25,
            w_recency=0.15,
            weight_min=0.0,
            weight_max=1.0,
            recency_scale=_SCALE,
            recency_sharpness=_SHARPNESS,
            recency_floor=_FLOOR,
            fd_backend=None,
        )
        v = np.ones(8)
        got = scorer.score(v, v, age_seconds=0.0, cosine=float("nan"))
        assert got == 0.0
        assert math.isfinite(got)

    def test_unified_scorer_finite_total_still_clamped(self) -> None:
        scorer = UnifiedScorer(
            w_cosine=0.6,
            w_fd=0.25,
            w_recency=0.15,
            weight_min=0.0,
            weight_max=1.0,
            recency_scale=_SCALE,
            recency_sharpness=_SHARPNESS,
            recency_floor=_FLOOR,
            fd_backend=None,
        )
        v = np.ones(8)
        assert scorer.score(v, v, age_seconds=0.0, cosine=1.0) == pytest.approx(
            1.0, abs=1e-9
        )

    def test_rescore_nan_scorer_output_is_zero(self) -> None:
        now = datetime.now(UTC).timestamp()
        hit = RecallHit(
            payload={"text": "alpha beta", "timestamp": now},
            score=1.0,
        )
        scorer = _FixedScoreScorer(float("nan"))
        ranked = _rescore_and_rank_hits(
            _Cfg(), scorer, _Embedder(), [hit], "alpha beta"
        )
        assert ranked[0].score == 0.0
        assert math.isfinite(ranked[0].score)


class TestNoSalienceForce:
    """C2/C3: traits must never force salience to 1.0."""

    def test_eval_step_never_writes_s_eq_one(self) -> None:
        import inspect

        from somabrain.services.cognitive_loop_service import eval_step

        src = inspect.getsource(eval_step)
        assert "s = 1.0" not in src
        assert "s=1.0" not in src
        assert "salience = 1.0" not in src

    def test_traits_present_yields_amygdala_salience_not_one(self, monkeypatch) -> None:
        import types

        from somabrain.runtime.neuromodulators import NeuromodState
        from somabrain.services import cognitive_loop_service as cls
        from somabrain.sleep import SleepState, SleepStateManager

        monkeypatch.setattr(
            cls,
            "get_cognitive_loop_state",
            lambda: SimpleNamespace(
                get_sleep_state=lambda _t: SleepState.ACTIVE,
                bu_publisher=None,
            ),
        )
        monkeypatch.setattr(
            SleepStateManager,
            "compute_parameters",
            lambda self, state, tenant_id="default": {
                "K": 1,
                "t": 1.0,
                "tau": 1.0,
                "eta": 0.5,
                "lambda": 1.0,
                "B": 1.0,
            },
        )

        class _Neuromods:
            def get_state(self, _tenant):
                return NeuromodState(
                    dopamine=0.4,
                    serotonin=0.5,
                    noradrenaline=0.0,
                    acetylcholine=0.0,
                )

        class _Predictor:
            def predict_and_compare(self, _prev, _cur):
                return types.SimpleNamespace(
                    predicted_vec=np.ones(4),
                    actual_vec=np.ones(4),
                    error=0.2,
                )

        class _Amygdala:
            def score(self, novelty, pred_error, nm, wm_vec, affect_boost=0.0):
                return 0.42

            def gates(self, s, nm, temperature_scale=1.0, threshold_offset=0.0):
                return True, True

        store = PersonalityStore()
        store.set(PersonalityState(traits={"dopamine": 0.9, "openness": 1.0}), "t")

        out = cls.eval_step(
            novelty=0.3,
            wm_vec=np.ones(4),
            cfg=SimpleNamespace(),
            predictor=_Predictor(),
            neuromods=_Neuromods(),
            personality_store=store,
            supervisor=None,
            amygdala=_Amygdala(),
            tenant_id="t",
            previous_focus_vec=np.ones(4),
        )
        # Salience comes from the amygdala, not a traits shortcut.
        assert out["salience"] == pytest.approx(0.42)
        assert out["salience"] != 1.0


class TestPersonalityGetCopy:
    """H4: PersonalityStore.get must return a copy, not the live object."""

    def test_get_returns_independent_copies(self) -> None:
        store = PersonalityStore()
        first = store.get("acme")
        second = store.get("acme")
        assert first is not second
        assert first == second

    def test_mutating_returned_traits_does_not_touch_store(self) -> None:
        store = PersonalityStore()
        got = store.get("acme")
        got.traits["poison"] = 1.0
        again = store.get("acme")
        assert "poison" not in again.traits

    def test_set_and_update_also_return_copies(self) -> None:
        store = PersonalityStore()
        stored = store.set(PersonalityState(traits={"dopamine": 0.5}), "acme")
        stored.traits["poison"] = 1.0
        assert "poison" not in store.get("acme").traits

        updated = store.update_traits({"serotonin": 0.7}, "acme")
        updated.traits["poison"] = 2.0
        assert "poison" not in store.get("acme").traits
        assert store.get("acme").traits.get("serotonin") == 0.7

    def test_get_requires_tenant(self) -> None:
        store = PersonalityStore()
        with pytest.raises(ValueError):
            store.get("")
