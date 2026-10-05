"""Neuromodulator wiring tests (W2 / DEBT-001…007).

Production imports only: ``somabrain.runtime.neuromodulators``,
``somabrain.bootstrap.singletons``, ``somabrain.learning.adaptation.engine``,
``somabrain.admin.cognitive.amygdala``, ``somabrain.runtime.supervisor``.

Covers:
- singleton DA→LR (DEBT-002): stored dopamine changes ``lr_scale``
- homeostatic law (W2.3 / DEBT-004): mean-reverting, parameters can fall
- API bounds (DEBT-003): out-of-box / garbage values are rejected
- invariant after 1000 updates: stays in ``NEURO_BOUNDS``, no monotone saturation
- ACh law shared by adaptive + supervisor (DEBT-005)
- 5-HT consumer on the amygdala gate path (DEBT-006)
- one store (DEBT-001)

Marked ``no_django``: full ``somabrain.settings`` boot requires Vault
(``SOMABRAIN_MEMORY_HTTP_TOKEN``). The test configures Django with the
production defaults from ``somabrain/settings/neuro.py`` and
``somabrain/math/contracts.py`` so the production modules import unchanged.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

REPO_ROOT = Path(__file__).resolve().parents[2]


def _production_neuro_defaults() -> dict[str, float]:
    """SOMABRAIN_NEURO_* defaults from the production settings module."""
    ns = runpy.run_path(str(REPO_ROOT / "somabrain" / "settings" / "neuro.py"))
    return {k: v for k, v in ns.items() if k.startswith("SOMABRAIN_NEURO_")}


def _configure_settings() -> None:
    """Boot django.conf with production defaults (only if not already up)."""
    from django.conf import settings as dj_settings

    if dj_settings.configured:
        return
    from somabrain.math.contracts import ADAPT_BOUNDS, ADAPT_GAINS

    cfg: dict[str, object] = dict(_production_neuro_defaults())
    cfg.update(
        {
            "SOMABRAIN_ADAPTATION_GAIN_ALPHA": ADAPT_GAINS["alpha"],
            "SOMABRAIN_ADAPTATION_GAIN_GAMMA": ADAPT_GAINS["gamma"],
            "SOMABRAIN_ADAPTATION_GAIN_LAMBDA": ADAPT_GAINS["lambda_"],
            "SOMABRAIN_ADAPTATION_GAIN_MU": ADAPT_GAINS["mu"],
            "SOMABRAIN_ADAPTATION_GAIN_NU": ADAPT_GAINS["nu"],
            "SOMABRAIN_ADAPTATION_ALPHA_MIN": ADAPT_BOUNDS["alpha"][0],
            "SOMABRAIN_ADAPTATION_ALPHA_MAX": ADAPT_BOUNDS["alpha"][1],
            "SOMABRAIN_ADAPTATION_GAMMA_MIN": ADAPT_BOUNDS["gamma"][0],
            "SOMABRAIN_ADAPTATION_GAMMA_MAX": ADAPT_BOUNDS["gamma"][1],
            "SOMABRAIN_ADAPTATION_LAMBDA_MIN": ADAPT_BOUNDS["lambda_"][0],
            "SOMABRAIN_ADAPTATION_LAMBDA_MAX": ADAPT_BOUNDS["lambda_"][1],
            "SOMABRAIN_ADAPTATION_MU_MIN": ADAPT_BOUNDS["mu"][0],
            "SOMABRAIN_ADAPTATION_MU_MAX": ADAPT_BOUNDS["mu"][1],
            "SOMABRAIN_ADAPTATION_NU_MIN": ADAPT_BOUNDS["nu"][0],
            "SOMABRAIN_ADAPTATION_NU_MAX": ADAPT_BOUNDS["nu"][1],
            "SOMABRAIN_UTILITY_LAMBDA": 1.0,
            "SOMABRAIN_UTILITY_MU": 0.1,
            "SOMABRAIN_UTILITY_NU": 0.05,
            "SOMABRAIN_LEARNING_RATE_DYNAMIC": True,
            "REQUIRE_EXTERNAL_BACKENDS": False,
            "ENABLE_LEARNING_STATE_PERSISTENCE": False,
            "REDIS_DB": 0,
            "SOMABRAIN_SALIENCE_W_NOVELTY": 0.6,
            "SOMABRAIN_SALIENCE_W_ERROR": 0.4,
            "SOMABRAIN_SALIENCE_THRESHOLD_STORE": 0.5,
            "SOMABRAIN_SALIENCE_THRESHOLD_ACT": 0.7,
            "SOMABRAIN_SALIENCE_HYSTERESIS": 0.1,
            "SOMABRAIN_USE_SOFT_SALIENCE": False,
            "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE": 0.1,
            "SOMABRAIN_SALIENCE_METHOD": "dense",
            "SOMABRAIN_SALIENCE_FD_WEIGHT": 0.25,
            "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR": 0.9,
            "SOMABRAIN_USE_META_BRAIN": False,
            "SOMABRAIN_META_GAIN": 0.1,
            "SOMABRAIN_META_LIMIT": 1.0,
        }
    )
    dj_settings.configure(**cfg)


_configure_settings()

from somabrain.adaptive.core import (  # noqa: E402
    AdaptiveParameter,
    PerformanceMetrics,
)
from somabrain.bootstrap.singletons import (  # noqa: E402
    get_neuromodulators,
    get_supervisor,
)
from somabrain.learning.adaptation.engine import AdaptationEngine  # noqa: E402
from somabrain.learning.adaptation.types import (  # noqa: E402
    RetrievalWeights,
)
from somabrain.learning.config import AdaptationGains  # noqa: E402
from somabrain.math.contracts import NEURO_BOUNDS  # noqa: E402
from somabrain.runtime.neuromodulators import (  # noqa: E402
    AdaptiveNeuromodulators,
    AdaptivePerTenantNeuromodulators,
    NeuromodState,
    NeuromodValueError,
    PerTenantNeuromodulators,
    acetylcholine_target,
    checked_value,
    project,
    serotonin_target,
)


# ---------------------------------------------------------------------------
# DEBT-001 — one store
# ---------------------------------------------------------------------------


class TestSingleStore:
    def test_one_per_tenant_class_in_production(self):
        """Exactly one ``PerTenantNeuromodulators`` class exists in somabrain/."""
        import somabrain
        from somabrain.runtime.neuromodulators import PerTenantNeuromodulators as P

        classes = []
        pkg_root = Path(somabrain.__file__).resolve().parent
        for path in pkg_root.rglob("*.py"):
            if b"class PerTenantNeuromodulators" in path.read_bytes():
                classes.append(path)
        assert len(classes) == 1, classes
        assert classes[0].name == "neuromodulators.py"
        assert P is PerTenantNeuromodulators

    def test_singleton_identity(self):
        assert get_neuromodulators() is get_neuromodulators()

    def test_singleton_sees_tenant_write(self):
        store = get_neuromodulators()
        store.set_state("w2_one_store", NeuromodState(dopamine=0.7, serotonin=0.9))
        seen = get_neuromodulators().get_state("w2_one_store")
        assert seen.dopamine == pytest.approx(0.7)
        assert seen.serotonin == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# DEBT-002 — singleton DA→LR
# ---------------------------------------------------------------------------


class TestDopamineToLearningRate:
    def _engine(self, tenant: str) -> AdaptationEngine:
        return AdaptationEngine(
            retrieval=RetrievalWeights(1.0, 0.2, 0.1, 0.7),
            utility=None,
            learning_rate=0.05,
            max_history=10,
            tenant_id=tenant,
            enable_dynamic_lr=True,
            gains=AdaptationGains.from_settings(),
        )

    def test_lr_scale_follows_stored_dopamine(self):
        """Set d=0.8 then d=0.2 in the store; lr_scale must change (W2.2)."""
        tenant = "w2_da_lr"
        store = get_neuromodulators()
        engine = self._engine(tenant)

        store.set_state(tenant, NeuromodState(dopamine=0.8))
        engine._update_learning_rate()
        lr_high = engine.learning_rate

        store.set_state(tenant, NeuromodState(dopamine=0.2))
        engine._update_learning_rate()
        lr_low = engine.learning_rate

        assert lr_high != lr_low
        # lr = base_lr · clamp(0.5 + dopamine, 0.5, 1.2)
        assert lr_high == pytest.approx(0.05 * 1.2)  # 0.5+0.8 → 1.3 clamped to 1.2
        assert lr_low == pytest.approx(0.05 * 0.7)

    def test_no_fresh_empty_store(self):
        """The engine reads the singleton, not a fresh empty container."""
        tenant = "w2_da_fresh"
        store = get_neuromodulators()
        engine = self._engine(tenant)
        store.set_state(tenant, NeuromodState(dopamine=0.31))
        assert engine._get_dopamine_level() == pytest.approx(0.31)


# ---------------------------------------------------------------------------
# W2.3 / DEBT-004 — homeostatic law
# ---------------------------------------------------------------------------


class TestHomeostaticLaw:
    def test_mean_reverting_formula(self):
        """m ← Π(m + η (δ − m)) exactly."""
        p = AdaptiveParameter("t", initial_value=0.4, min_value=0.0, max_value=1.0,
                              learning_rate=0.1)
        p.update(PerformanceMetrics(), delta=0.9)
        assert p.current_value == pytest.approx(0.4 + 0.1 * (0.9 - 0.4))

    def test_parameter_can_decrease(self):
        """Adverse evidence lowers the parameter (no saturating integrator)."""
        p = AdaptiveParameter("t", initial_value=0.5, min_value=0.2, max_value=0.8,
                              learning_rate=0.1)
        p.update(PerformanceMetrics(), delta=0.8)  # pull up
        peak = p.current_value
        for _ in range(20):
            p.update(PerformanceMetrics(), delta=0.2)  # pull down
        assert p.current_value < peak

    def test_dopamine_falls_after_failure(self):
        """DEBT-004 acceptance: success then failure → dopamine falls from peak."""
        adaptive = AdaptiveNeuromodulators()
        good = PerformanceMetrics(success_rate=1.0, error_rate=0.0, latency=0.01,
                                  accuracy=1.0)
        bad = PerformanceMetrics(success_rate=0.0, error_rate=1.0, latency=1.0,
                                 accuracy=0.0)
        for _ in range(30):
            adaptive.update_from_performance(good, task_type="general")
        peak = adaptive.get_current_state().dopamine
        for _ in range(30):
            adaptive.update_from_performance(bad, task_type="general")
        final = adaptive.get_current_state().dopamine
        assert final < peak, f"dopamine must fall from peak: {peak} -> {final}"

    def test_no_monotone_saturation_over_1000(self):
        """Invariant after 1000 updates: in bounds, not stuck at a bound."""
        adaptive = AdaptiveNeuromodulators()
        hi = PerformanceMetrics(success_rate=1.0, error_rate=0.0, latency=0.01,
                                accuracy=1.0)
        lo = PerformanceMetrics(success_rate=0.0, error_rate=1.0, latency=1.0,
                                accuracy=0.0)
        trajectory: list[float] = []
        for i in range(1000):
            perf = hi if (i // 50) % 2 == 0 else lo
            state = adaptive.update_from_performance(perf, task_type="general")
            for name in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
                lo_b, hi_b = NEURO_BOUNDS[name]
                val = getattr(state, name)
                assert lo_b <= val <= hi_b, (name, val)
            trajectory.append(state.dopamine)
        # alternating feedback ⇒ dopamine must both rise and fall across the run
        peak = max(trajectory)
        trough = min(trajectory)
        assert peak - trough > 0.05, "dopamine saturated / collapsed to a constant"
        # not glued to a bound for the whole second half
        second_half = trajectory[500:]
        assert not all(v == peak for v in second_half)
        assert not all(v == trough for v in second_half)

    def test_store_set_state_projects(self):
        store = PerTenantNeuromodulators()
        store.set_state(
            "t",
            NeuromodState(dopamine=99.0, serotonin=-3.0, noradrenaline=0.5,
                          acetylcholine=0.5),
        )
        s = store.get_state("t")
        assert s.dopamine == NEURO_BOUNDS["dopamine"][1]
        assert s.serotonin == NEURO_BOUNDS["serotonin"][0]
        assert s.noradrenaline == NEURO_BOUNDS["noradrenaline"][1]
        assert s.acetylcholine == NEURO_BOUNDS["acetylcholine"][1]


# ---------------------------------------------------------------------------
# DEBT-003 — API boundary: reject out-of-box / garbage
# ---------------------------------------------------------------------------


class TestApiBounds:
    def test_bounds_table_is_the_documented_box(self):
        assert NEURO_BOUNDS["dopamine"] == (0.2, 0.8)
        assert NEURO_BOUNDS["serotonin"] == (0.0, 1.0)
        assert NEURO_BOUNDS["noradrenaline"] == (0.0, 0.1)
        assert NEURO_BOUNDS["acetylcholine"] == (0.0, 0.1)

    @pytest.mark.parametrize(
        "name,value",
        [
            ("dopamine", 99.0),
            ("dopamine", -1.0),
            ("dopamine", 0.199999),
            ("serotonin", 1.5),
            ("noradrenaline", 0.11),
            ("acetylcholine", 0.2),
            ("dopamine", float("nan")),
            ("dopamine", float("inf")),
            ("dopamine", float("-inf")),
        ],
    )
    def test_rejects_out_of_box(self, name: str, value: float):
        with pytest.raises(NeuromodValueError):
            checked_value(name, value)

    @pytest.mark.parametrize(
        "name,value",
        [
            ("dopamine", 0.2),
            ("dopamine", 0.8),
            ("dopamine", 0.5),
            ("serotonin", 0.0),
            ("serotonin", 1.0),
            ("noradrenaline", 0.0),
            ("noradrenaline", 0.1),
            ("acetylcholine", 0.05),
        ],
    )
    def test_accepts_in_box(self, name: str, value: float):
        assert checked_value(name, value) == value

    def test_rejects_non_float(self):
        with pytest.raises(NeuromodValueError):
            checked_value("dopamine", "high")  # type: ignore[arg-type]

    def test_endpoint_module_uses_checked_value(self):
        """The HTTP handler validates through the same boundary function."""
        src = (REPO_ROOT / "somabrain" / "api" / "endpoints" / "neuromod.py").read_text()
        assert "checked_value" in src
        assert "NeuromodValueError" in src
        assert "HttpError(422" in src


# ---------------------------------------------------------------------------
# DEBT-005 — one ACh law, shared by adaptive + supervisor
# ---------------------------------------------------------------------------


class TestAChLaw:
    def test_target_formula(self):
        """δ_ACh = Π(0.5·novelty + 0.3·pred_error + 0.2·memory_load)."""
        lo, hi = NEURO_BOUNDS["acetylcholine"]
        expected = lo + (hi - lo) * (0.5 * 0.8 + 0.3 * 0.4 + 0.2 * 1.0)
        assert acetylcholine_target(0.8, 0.4, memory_load=1.0) == pytest.approx(expected)

    def test_same_ach_delta_sign_as_supervisor(self):
        """Given the same novelty/pred_error, both paths move ACh the same way."""
        from somabrain.runtime.supervisor import Supervisor, SupervisorConfig

        novelty, pred_error = 0.9, 0.1
        target = acetylcholine_target(novelty, pred_error)

        # adaptive path (task_type=general ⇒ memory_load=0)
        adaptive = AdaptiveNeuromodulators()
        # pin ACh below the target so the expected direction is "up"
        adaptive.acetylcholine_param.current_value = NEURO_BOUNDS["acetylcholine"][0]
        before = adaptive.acetylcholine_param.current_value
        adaptive.update_from_performance(
            PerformanceMetrics(error_rate=pred_error),
            task_type="general",
            novelty=novelty,
            pred_error=pred_error,
        )
        adaptive_delta = adaptive.acetylcholine_param.current_value - before

        # supervisor path, same starting point
        sup = Supervisor(SupervisorConfig(gain=0.2, limit=0.1))
        nm = NeuromodState(
            dopamine=0.4,
            serotonin=0.5,
            noradrenaline=0.0,
            acetylcholine=NEURO_BOUNDS["acetylcholine"][0],
        )
        new_nm, _F, _mag = sup.adjust(nm, novelty, pred_error)
        supervisor_delta = new_nm.acetylcholine - nm.acetylcholine

        assert target > before
        assert adaptive_delta > 0
        assert supervisor_delta > 0
        assert (adaptive_delta > 0) == (supervisor_delta > 0)

    def test_low_attention_lowers_ach(self):
        adaptive = AdaptiveNeuromodulators()
        adaptive.acetylcholine_param.current_value = NEURO_BOUNDS["acetylcholine"][1]
        before = adaptive.acetylcholine_param.current_value
        for _ in range(50):
            adaptive.update_from_performance(
                PerformanceMetrics(error_rate=1.0),
                task_type="general",
                novelty=0.0,
                pred_error=1.0,
            )
        assert adaptive.acetylcholine_param.current_value < before


# ---------------------------------------------------------------------------
# DEBT-006 — serotonin has a real consumer
# ---------------------------------------------------------------------------


class TestSerotoninConsumer:
    def _amygdala(self):
        from somabrain.admin.cognitive.amygdala import AmygdalaSalience, SalienceConfig

        return AmygdalaSalience(
            SalienceConfig(
                w_novelty=0.6,
                w_error=0.4,
                threshold_store=0.5,
                threshold_act=0.7,
                hysteresis=0.1,
            )
        )

    def test_5ht_alters_gate_thresholds(self):
        """A 5-HT change alters the documented downstream output (gate th)."""
        amygdala = self._amygdala()
        # arm hysteresis so the 5-HT coupling is visible
        amygdala.gates(0.6, NeuromodState(serotonin=0.0))
        low = amygdala._thresholds(NeuromodState(serotonin=0.0, noradrenaline=0.0))
        high = amygdala._thresholds(NeuromodState(serotonin=1.0, noradrenaline=0.0))
        assert high[0] < low[0], "higher 5-HT must increase stickiness (hysteresis)"

    def test_5ht_alters_soft_gate_temperature(self):
        from somabrain.admin.cognitive.amygdala import AmygdalaSalience, SalienceConfig

        amygdala = AmygdalaSalience(
            SalienceConfig(
                w_novelty=0.6,
                w_error=0.4,
                threshold_store=0.5,
                threshold_act=0.7,
                hysteresis=0.1,
                use_soft=True,
                soft_temperature=0.1,
            )
        )
        s = 0.6
        p_stable = amygdala.gate_probs(s, NeuromodState(serotonin=1.0))
        p_unstable = amygdala.gate_probs(s, NeuromodState(serotonin=0.0))
        # wider sigmoid (high 5-HT) ⇒ probability closer to 0.5 than the sharp one
        assert abs(p_stable[0] - 0.5) < abs(p_unstable[0] - 0.5)

    def test_stability_law(self):
        assert serotonin_target(0.0) == pytest.approx(1.0)
        assert serotonin_target(1.0) == pytest.approx(0.0)
        assert serotonin_target(0.3) == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# W2.3 projection helper
# ---------------------------------------------------------------------------


class TestProjection:
    def test_project_is_pi(self):
        assert project("dopamine", 0.0) == 0.2
        assert project("dopamine", 1.0) == 0.8
        assert project("dopamine", 0.5) == 0.5
        assert project("acetylcholine", 5.0) == 0.1

    def test_neuromod_state_clamped(self):
        s = NeuromodState(dopamine=5.0, serotonin=-1.0, noradrenaline=9.0,
                          acetylcholine=9.0).clamped()
        assert (s.dopamine, s.serotonin, s.noradrenaline, s.acetylcholine) == (
            0.8,
            0.0,
            0.1,
            0.1,
        )


# ---------------------------------------------------------------------------
# W2.6 — supervisor is wired (factory reachable), not ornamental
# ---------------------------------------------------------------------------


class TestSupervisorWiring:
    def test_get_supervisor_factory_exists(self):
        sup = get_supervisor()
        # default SOMABRAIN_USE_META_BRAIN=False ⇒ None; the wiring itself is
        # what matters: /act passes get_supervisor() instead of a literal None
        assert sup is None or hasattr(sup, "adjust")

    def test_act_endpoint_passes_supervisor(self):
        src = (REPO_ROOT / "somabrain" / "api" / "endpoints" / "cognitive.py").read_text()
        assert "get_supervisor" in src
        assert "supervisor=supervisor" in src

    def test_rust_ode_deleted(self):
        neuro_rs = (REPO_ROOT / "rust_core" / "src" / "neuro.rs").read_text()
        assert "pub fn update(" not in neuro_rs
        assert "pub fn set_dynamics" not in neuro_rs
        assert "pub fn get_dynamics" not in neuro_rs
        assert "k_d:" not in neuro_rs  # no dynamics fields
        models = (REPO_ROOT / "somabrain" / "brain_settings" / "models.py").read_text()
        assert "neuro_k_d_" not in models
        assert "neuro_k_r_" not in models
        assert "neuro_u_scale" not in models

    def test_adaptive_registry_no_attribute_shim(self):
        import somabrain.runtime.neuromodulators as mod

        assert not hasattr(mod, "adaptive_per_tenant_neuromods")
        reg = mod.get_adaptive_per_tenant_neuromods()
        assert isinstance(reg, AdaptivePerTenantNeuromodulators)
        assert reg is mod.get_adaptive_per_tenant_neuromods()
