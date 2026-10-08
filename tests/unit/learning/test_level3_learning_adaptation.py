"""Level 3 — learning / adaptation behavioural tests.

Production implementations only (no mocks, no source greps):
- ``somabrain.learning.adaptation.engine.AdaptationEngine``
- ``somabrain.adaptive.core.AdaptiveParameter`` / homeostatic law
- ``somabrain.math.contracts`` (ADAPT_GAINS / ADAPT_BOUNDS / anneal_tau)
- ``somabrain.bootstrap.singletons.get_neuromodulators`` (DA → lr_scale)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _unit_settings import configure_unit_settings  # noqa: E402

configure_unit_settings()

from somabrain.adaptive.core import (  # noqa: E402
    AdaptiveParameter,
    PerformanceMetrics,
)
from somabrain.bootstrap.singletons import get_neuromodulators  # noqa: E402
from somabrain.learning.adaptation.engine import AdaptationEngine  # noqa: E402
from somabrain.learning.adaptation.types import RetrievalWeights  # noqa: E402
from somabrain.learning.adaptation.utils import weight_delta  # noqa: E402
from somabrain.learning.config import (  # noqa: E402
    AdaptationConstraints,
    AdaptationGains,
    UtilityWeights,
)
from somabrain.math.contracts import (  # noqa: E402
    ADAPT_BOUNDS,
    ADAPT_GAINS,
    NEURO_BOUNDS,
    TAU_FLOOR,
    anneal_tau,
)
from somabrain.runtime.neuromodulators import (  # noqa: E402
    AdaptiveNeuromodulators,
    NeuromodState,
)


def _engine(tenant: str, *, dynamic: bool = True) -> AdaptationEngine:
    return AdaptationEngine(
        retrieval=RetrievalWeights(1.0, 0.2, 0.1, 0.7),
        utility=UtilityWeights(lambda_=1.0, mu=0.1, nu=0.05),
        learning_rate=0.05,
        max_history=8,
        constraints=AdaptationConstraints.from_settings(),
        tenant_id=tenant,
        enable_dynamic_lr=dynamic,
        gains=AdaptationGains.from_settings(),
    )


# ---------------------------------------------------------------------------
# DA → lr_scale (singleton store, not a fresh empty container)
# ---------------------------------------------------------------------------


class TestDopamineLearningRateScale:
    def test_lr_scale_follows_stored_dopamine(self) -> None:
        tenant = "l3_da_scale"
        store = get_neuromodulators()
        engine = _engine(tenant)

        store.set_state(tenant, NeuromodState(dopamine=0.8))
        engine._update_learning_rate()
        lr_high = engine.learning_rate

        store.set_state(tenant, NeuromodState(dopamine=0.2))
        engine._update_learning_rate()
        lr_low = engine.learning_rate

        # lr = base_lr · clamp(0.5 + dopamine, 0.5, 1.2)
        assert lr_high == pytest.approx(0.05 * 1.2)
        assert lr_low == pytest.approx(0.05 * 0.7)
        assert lr_high > lr_low

    def test_reads_process_wide_singleton(self) -> None:
        tenant = "l3_da_singleton"
        store = get_neuromodulators()
        engine = _engine(tenant)
        store.set_state(tenant, NeuromodState(dopamine=0.31))
        assert engine._get_dopamine_level() == pytest.approx(0.31)
        assert get_neuromodulators() is store


# ---------------------------------------------------------------------------
# Homeostatic law m ← Π(m + η(δ − m)); fall after failure; no saturation
# ---------------------------------------------------------------------------


class TestHomeostaticLaw:
    def test_exact_mean_reverting_update(self) -> None:
        p = AdaptiveParameter(
            "t", initial_value=0.4, min_value=0.0, max_value=1.0, learning_rate=0.1
        )
        p.update(PerformanceMetrics(), delta=0.9)
        assert p.current_value == pytest.approx(0.4 + 0.1 * (0.9 - 0.4))

    def test_falls_after_failure(self) -> None:
        adaptive = AdaptiveNeuromodulators()
        good = PerformanceMetrics(
            success_rate=1.0, error_rate=0.0, latency=0.01, accuracy=1.0
        )
        bad = PerformanceMetrics(
            success_rate=0.0, error_rate=1.0, latency=1.0, accuracy=0.0
        )
        for _ in range(30):
            adaptive.update_from_performance(good, task_type="general")
        peak = adaptive.get_current_state().dopamine
        for _ in range(30):
            adaptive.update_from_performance(bad, task_type="general")
        final = adaptive.get_current_state().dopamine
        assert final < peak

    def test_no_monotone_saturation_over_1000_steps(self) -> None:
        adaptive = AdaptiveNeuromodulators()
        hi = PerformanceMetrics(
            success_rate=1.0, error_rate=0.0, latency=0.01, accuracy=1.0
        )
        lo = PerformanceMetrics(
            success_rate=0.0, error_rate=1.0, latency=1.0, accuracy=0.0
        )
        trajectory: list[float] = []
        for i in range(1000):
            perf = hi if (i // 50) % 2 == 0 else lo
            state = adaptive.update_from_performance(perf, task_type="general")
            for name in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
                lo_b, hi_b = NEURO_BOUNDS[name]
                val = getattr(state, name)
                assert lo_b <= val <= hi_b
            trajectory.append(state.dopamine)
        peak, trough = max(trajectory), min(trajectory)
        assert peak - trough > 0.05
        second_half = trajectory[500:]
        assert not all(v == peak for v in second_half)
        assert not all(v == trough for v in second_half)


# ---------------------------------------------------------------------------
# ADAPT_GAINS / ADAPT_BOUNDS are what the engine actually applies
# ---------------------------------------------------------------------------


class TestEngineUsesMathContracts:
    def test_default_gains_and_bounds_match_contracts(self) -> None:
        g = AdaptationGains.from_settings()
        assert (g.alpha, g.gamma, g.lambda_, g.mu, g.nu) == (
            ADAPT_GAINS["alpha"],
            ADAPT_GAINS["gamma"],
            ADAPT_GAINS["lambda_"],
            ADAPT_GAINS["mu"],
            ADAPT_GAINS["nu"],
        )
        b = AdaptationConstraints.from_settings()
        assert (b.alpha_min, b.alpha_max) == ADAPT_BOUNDS["alpha"]
        assert (b.gamma_min, b.gamma_max) == ADAPT_BOUNDS["gamma"]
        assert (b.lambda_min, b.lambda_max) == ADAPT_BOUNDS["lambda_"]
        assert (b.mu_min, b.mu_max) == ADAPT_BOUNDS["mu"]
        assert (b.nu_min, b.nu_max) == ADAPT_BOUNDS["nu"]

    def test_weight_updates_use_contract_gains(self) -> None:
        engine = _engine("l3_gains", dynamic=False)
        # Pin dynamic LR off so the step is exactly lr × gain × signal.
        engine._enable_dynamic_lr = False
        engine._lr = engine._base_lr = 0.05
        alpha0 = engine.retrieval_weights.alpha
        gamma0 = engine.retrieval_weights.gamma
        lam0 = engine.utility_weights.lambda_
        lr = engine.learning_rate
        engine.apply_feedback(utility=1.0, reward=1.0)
        assert lr == pytest.approx(0.05)
        assert engine.retrieval_weights.alpha == pytest.approx(
            alpha0 + weight_delta(lr, ADAPT_GAINS["alpha"], 1.0)
        )
        assert engine.retrieval_weights.gamma == pytest.approx(
            gamma0 + weight_delta(lr, ADAPT_GAINS["gamma"], 1.0)
        )
        assert engine.utility_weights.lambda_ == pytest.approx(
            lam0 + weight_delta(lr, ADAPT_GAINS["lambda_"], 1.0)
        )

    def test_extreme_feedback_stays_inside_adapt_bounds(self) -> None:
        engine = _engine("l3_bounds", dynamic=False)
        engine._enable_dynamic_lr = False
        for _ in range(200):
            engine.apply_feedback(utility=10.0, reward=10.0)
        for _ in range(200):
            engine.apply_feedback(utility=-10.0, reward=-10.0)
        rw, uw = engine.retrieval_weights, engine.utility_weights
        assert ADAPT_BOUNDS["alpha"][0] <= rw.alpha <= ADAPT_BOUNDS["alpha"][1]
        assert ADAPT_BOUNDS["gamma"][0] <= rw.gamma <= ADAPT_BOUNDS["gamma"][1]
        assert ADAPT_BOUNDS["lambda_"][0] <= uw.lambda_ <= ADAPT_BOUNDS["lambda_"][1]
        assert ADAPT_BOUNDS["mu"][0] <= uw.mu <= ADAPT_BOUNDS["mu"][1]
        assert ADAPT_BOUNDS["nu"][0] <= uw.nu <= ADAPT_BOUNDS["nu"][1]


# ---------------------------------------------------------------------------
# tau: anneal non-increasing, floor always (including restore)
# ---------------------------------------------------------------------------


class TestTauSchedule:
    def test_anneal_tau_non_increasing_and_floored(self) -> None:
        tau = 1.0
        for _ in range(200):
            nxt = anneal_tau(tau)
            assert nxt <= tau
            assert nxt >= TAU_FLOOR
            tau = nxt
        assert tau == TAU_FLOOR

    def test_initialize_from_prior_restores_tau_at_floor(self) -> None:
        engine = _engine("l3_tau_prior")
        engine.initialize_from_prior({"tau": 0.01, "learning_rate": 0.02})
        assert engine.tau >= TAU_FLOOR
        assert engine.tau == TAU_FLOOR

    def test_load_state_restores_tau_at_floor(self) -> None:
        """``load_state`` is the Redis restore path — τ never comes back below floor."""

        class _StateKV:
            """In-process key/value with the Redis methods persistence uses."""

            def __init__(self) -> None:
                self._data: dict[str, str] = {}

            def setex(self, key: str, _ttl: int, value: str) -> None:
                self._data[key] = value

            def get(self, key: str) -> str | None:
                return self._data.get(key)

        engine = _engine("l3_tau_load")
        kv = _StateKV()
        engine._redis = kv  # persistence adapter
        # Simulate a stored state whose tau was corrupted below the floor.
        import json

        kv.setex(
            "adaptation:state:l3_tau_load",
            60,
            json.dumps(
                {
                    "retrieval": {"alpha": 1.2, "beta": 0.2, "gamma": 0.1, "tau": 0.01},
                    "utility": {"lambda_": 1.0, "mu": 0.1, "nu": 0.05},
                    "feedback_count": 3,
                    "learning_rate": 0.05,
                }
            ),
        )
        from somabrain.learning.persistence import is_persistence_enabled

        # Force the restore path even when persistence is off.
        engine._load_state()
        assert is_persistence_enabled() is False
        assert engine.tau >= TAU_FLOOR
        assert engine.tau == TAU_FLOOR

    def test_update_parameters_never_lowers_tau_below_floor(self) -> None:
        engine = _engine("l3_tau_update")
        engine.retrieval_weights.tau = 0.12
        engine.update_parameters({"reward": 1.0, "error": 50.0})
        assert engine.tau >= TAU_FLOOR
