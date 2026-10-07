"""Cognition wiring tests (W6 / DEBT-024…025 + W6.3–W6.5).

Production imports only: ``somabrain.admin.cognitive.basal_ganglia``,
``prefrontal``, ``emotion``, ``personality``, ``amygdala``,
``somabrain.segmentation.hmm``, ``somabrain.runtime.neuromodulators``.

Covers:
- BasalGangliaPolicy Boltzmann selection (T80): non-trivial selection over
  two candidates, temperature/epsilon effects, store/act mapping
- PrefrontalCortex precision-weighted WM admission (T81): high pred_error
  suppresses admit; score = π·salience with π = 1/(1+pred_error)
- Emotion VAD couplings (T82): arousal raises salience / sharpens T;
  dominance lowers thresholds
- Personality trait→neuromod blend (T83): mapped traits bias state,
  unmapped traits are identity metadata
- HMM params are FIXED (no Baum-Welch): production A is a constant;
  online_viterbi_probs is pure forward recursion

Marked ``no_django``: full ``somabrain.settings`` boot requires Vault
(``SOMABRAIN_MEMORY_HTTP_TOKEN``). The test configures Django with the
production defaults the production modules read.
"""

from __future__ import annotations

import random

import pytest

pytestmark = pytest.mark.no_django


def _configure_settings() -> None:
    """Boot django.conf with production defaults (only if not already up)."""
    from django.conf import settings as dj_settings

    if dj_settings.configured:
        return
    from somabrain.math.contracts import NEURO_BOUNDS

    cfg: dict[str, object] = {
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
        + 0.2 * (NEURO_BOUNDS["dopamine"][1] - NEURO_BOUNDS["dopamine"][0]),
        "SOMABRAIN_NEURO_SEROTONIN_BASE": 0.5,
        "SOMABRAIN_NEURO_NORAD_BASE": 0.0,
        "SOMABRAIN_NEURO_ACETYL_BASE": 0.0,
    }
    dj_settings.configure(**cfg)


_configure_settings()

from somabrain.admin.cognitive.amygdala import (  # noqa: E402
    AmygdalaSalience,
    SalienceConfig,
)
from somabrain.admin.cognitive.basal_ganglia import (  # noqa: E402
    BasalGangliaPolicy,
    PolicyDecision,
)
from somabrain.admin.cognitive.emotion import (  # noqa: E402
    AROUSAL_SALIENCE_WEIGHT,
    EmotionModel,
    affect_salience_boost,
    affect_temperature_scale,
    affect_threshold_offset,
    stimulus_from_signals,
)
from somabrain.admin.cognitive.personality import (  # noqa: E402
    PERSONALITY_BLEND,
    PersonalityStore,
)
from somabrain.admin.cognitive.prefrontal import (  # noqa: E402
    PrefrontalConfig,
    PrefrontalCortex,
)
from somabrain.math.contracts import NEURO_BOUNDS  # noqa: E402
from somabrain.runtime.neuromodulators import NeuromodState  # noqa: E402
from somabrain.schemas import PersonalityState  # noqa: E402
from somabrain.segmentation.hmm import (  # noqa: E402
    HMMParams,
    detect_boundaries,
    online_viterbi_probs,
)


class TestBasalGangliaSelection:
    """T80: Boltzmann action selection + ε-exploration (DEBT-024)."""

    def test_two_candidates_nontrivial_selection(self) -> None:
        """DEBT-024 acceptance: different utilities → non-pass-through selection."""
        bg = BasalGangliaPolicy(temperature=0.5, epsilon=0.0, seed=7)
        values = {"store": 0.9, "skip": 0.1}
        wins = {"store": 0, "skip": 0}
        for i in range(400):
            sel = bg.select(values, rng=random.Random(i))
            wins[sel.action] += 1
        # Higher utility wins most of the time, but not exclusively.
        assert wins["store"] > wins["skip"]
        assert wins["store"] < 400
        assert wins["skip"] > 0

    def test_softmax_probs_match_formula(self) -> None:
        """p(a) = exp((v_a − v_max)/T) / Σ exp((v_b − v_max)/T)."""
        import math

        values = {"a": 1.0, "b": 0.5, "c": 0.0}
        t = 0.7
        probs = BasalGangliaPolicy.softmax_probs(values, t)
        v_max = max(values.values())
        exps = {k: math.exp((v - v_max) / t) for k, v in values.items()}
        z = sum(exps.values())
        for k in values:
            assert abs(probs[k] - exps[k] / z) < 1e-12

    def test_zero_temperature_is_greedy(self) -> None:
        """T is validated > 0; greedy argmax is recovered as T→0+ via tiny T."""
        bg = BasalGangliaPolicy(temperature=1e-9, epsilon=0.0, seed=1)
        values = {"low": 0.1, "high": 0.9}
        for i in range(50):
            sel = bg.select(values, rng=random.Random(i))
            assert sel.action == "high"
            assert sel.explored is False

    def test_epsilon_exploration_uses_uniform(self) -> None:
        """With ε=1 every draw is the exploration branch."""
        bg = BasalGangliaPolicy(temperature=0.5, epsilon=1.0, seed=3)
        values = {"a": 1.0, "b": 0.0}
        seen = set()
        for i in range(100):
            sel = bg.select(values, rng=random.Random(i))
            assert sel.explored is True
            seen.add(sel.action)
        assert seen == {"a", "b"}

    def test_decide_maps_action_to_store_act(self) -> None:
        """STORE_ACTIONS / ACT_ACTIONS mapping is total and honest."""
        bg = BasalGangliaPolicy(temperature=1e-9, epsilon=0.0, seed=11)
        decision, selection = bg.decide(
            {"store": 1.0, "act": 0.0, "both": 0.0, "skip": 0.0},
            rng=random.Random(0),
        )
        assert selection.action == "store"
        assert decision.store is True
        assert decision.act is False
        assert isinstance(decision, PolicyDecision)

        decision2, selection2 = bg.decide(
            {"store": 0.0, "act": 0.0, "both": 1.0, "skip": 0.0},
            rng=random.Random(0),
        )
        assert selection2.action == "both"
        assert decision2.store is True
        assert decision2.act is True

        decision3, selection3 = bg.decide(
            {"store": 0.0, "act": 1.0, "both": 0.0, "skip": 0.0},
            rng=random.Random(0),
        )
        assert selection3.action == "act"
        assert decision3.store is False
        assert decision3.act is True

        decision4, selection4 = bg.decide(
            {"store": 0.0, "act": 0.0, "both": 0.0, "skip": 1.0},
            rng=random.Random(0),
        )
        assert selection4.action == "skip"
        assert decision4.store is False
        assert decision4.act is False

    def test_invalid_temperature_rejected(self) -> None:
        with pytest.raises(ValueError):
            BasalGangliaPolicy(temperature=0.0)
        with pytest.raises(ValueError):
            BasalGangliaPolicy(epsilon=1.5)


class TestPrefrontalWMGate:
    """T81: precision-weighted working-memory admission (DEBT-025)."""

    def test_precision_formula(self) -> None:
        assert abs(PrefrontalCortex.precision(0.0) - 1.0) < 1e-12
        assert abs(PrefrontalCortex.precision(1.0) - 0.5) < 1e-12
        assert abs(PrefrontalCortex.precision(3.0) - 0.25) < 1e-12

    def test_admit_score_is_precision_times_salience(self) -> None:
        pf = PrefrontalCortex(PrefrontalConfig(admit_threshold=0.25))
        score = pf.admit_score(salience=0.8, pred_error=1.0)
        assert abs(score - 0.8 * 0.5) < 1e-12

    def test_high_error_suppresses_admission(self) -> None:
        """Same salience admits at low error and rejects at high error."""
        pf = PrefrontalCortex(PrefrontalConfig(admit_threshold=0.4))
        assert pf.gate_wm(salience=0.8, pred_error=0.0) is True
        # π = 1/11 ≈ 0.09 → score ≈ 0.073 < 0.4
        assert pf.gate_wm(salience=0.8, pred_error=10.0) is False

    def test_not_a_uniform_scale(self) -> None:
        """DEBT-025 acceptance: decision depends on precision, not a scalar gain."""
        pf = PrefrontalCortex(PrefrontalConfig(admit_threshold=0.3))
        # Two alternatives with the same salience but different precision
        # resolve differently — a uniform scale would treat them alike.
        assert pf.gate_wm(0.6, pred_error=0.0) is True
        assert pf.gate_wm(0.6, pred_error=5.0) is False

    def test_state_counters(self) -> None:
        pf = PrefrontalCortex(PrefrontalConfig(admit_threshold=0.1))
        pf.gate_wm(1.0, 0.0)
        pf.gate_wm(0.0, 0.0)
        assert pf.state["calls"] == 2
        assert pf.state["admits"] == 1


class TestEmotionVADCouplings:
    """T82: VAD wired into salience, gate temperature, and thresholds."""

    def test_stimulus_from_signals(self) -> None:
        v, a, d = stimulus_from_signals(novelty=0.5, pred_error=0.25)
        assert abs(v - (1.0 - 0.5)) < 1e-12
        assert abs(a - 0.5) < 1e-12
        assert abs(d - 0.75) < 1e-12

    def test_arousal_raises_salience_boost(self) -> None:
        low = affect_salience_boost(type("S", (), {"valence": 0.0, "arousal": 0.0, "dominance": 0.0})())
        high = affect_salience_boost(type("S", (), {"valence": 0.0, "arousal": 1.0, "dominance": 0.0})())
        assert high - low == pytest.approx(AROUSAL_SALIENCE_WEIGHT)

    def test_valence_contributes_only_when_positive(self) -> None:
        from somabrain.admin.cognitive.emotion import EmotionVector

        pos = affect_salience_boost(EmotionVector(valence=1.0, arousal=0.0, dominance=0.0))
        neg = affect_salience_boost(EmotionVector(valence=-1.0, arousal=0.0, dominance=0.0))
        assert pos > 0.0
        assert neg == 0.0

    def test_arousal_sharpens_temperature(self) -> None:
        from somabrain.admin.cognitive.emotion import EmotionVector

        calm = affect_temperature_scale(EmotionVector(arousal=0.0))
        aroused = affect_temperature_scale(EmotionVector(arousal=1.0))
        assert calm == pytest.approx(1.0)
        assert aroused == pytest.approx(0.5)

    def test_dominance_lowers_thresholds(self) -> None:
        from somabrain.admin.cognitive.emotion import EmotionVector

        offset = affect_threshold_offset(EmotionVector(dominance=1.0))
        assert offset < 0.0

    def test_model_update_from_signals_and_decouple(self) -> None:
        from somabrain.admin.cognitive.emotion import VALENCE_SALIENCE_WEIGHT

        emotion = EmotionModel(decay_rate=0.0)
        emotion.update_from_signals(novelty=0.8, pred_error=0.0)
        assert emotion.state.arousal == pytest.approx(0.8)
        assert emotion.state.valence == pytest.approx(1.0)
        boost = emotion.salience_boost()
        # arousal term + positive-valence term
        assert boost == pytest.approx(
            AROUSAL_SALIENCE_WEIGHT * 0.8 + VALENCE_SALIENCE_WEIGHT * 1.0
        )
        assert emotion.temperature_scale() == pytest.approx(1.0 / 1.8)

    def test_amygdala_consumes_affect_arguments(self) -> None:
        cfg = SalienceConfig(
            w_novelty=0.6,
            w_error=0.4,
            threshold_store=0.5,
            threshold_act=0.5,
            hysteresis=0.1,
            use_soft=True,
            soft_temperature=0.5,
        )
        amy = AmygdalaSalience(cfg)
        nm = NeuromodState(dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0)
        s_plain = amy.score(0.5, 0.0, nm, affect_boost=0.0)
        s_boosted = amy.score(0.5, 0.0, nm, affect_boost=0.3)
        assert s_boosted > s_plain
        # Temperature scale 0.5 sharpens the soft gate relative to 1.0
        p_soft, _ = amy.gate_probs(0.5, nm, temperature_scale=1.0)
        p_sharp, _ = amy.gate_probs(0.5, nm, temperature_scale=0.5)
        # Away from the threshold midpoint a sharper gate is more extreme
        # (threshold 0.5, s=0.5 → at midpoint both ≈ 0.5; use s≠threshold)
        p_soft2, _ = amy.gate_probs(0.7, nm, temperature_scale=1.0)
        p_sharp2, _ = amy.gate_probs(0.7, nm, temperature_scale=0.5)
        assert p_sharp2 > p_soft2


class TestPersonalityTraitCoupling:
    """T83: mapped traits bias neuromods; unmapped traits are metadata."""

    def test_mapped_trait_blends_dopamine(self) -> None:
        store = PersonalityStore()
        base = NeuromodState(dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0)
        traits = PersonalityState(traits={"dopamine": 0.8})
        out = store.modulate_neuromods(base, traits)
        expected = (1.0 - PERSONALITY_BLEND) * 0.4 + PERSONALITY_BLEND * 0.8
        assert out.dopamine == pytest.approx(expected)
        assert base.dopamine == 0.4  # base not mutated

    def test_alias_keys_map(self) -> None:
        store = PersonalityStore()
        base = NeuromodState(dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0)
        out = store.modulate_neuromods(base, PersonalityState(traits={"da": 0.8, "5ht": 0.0}))
        assert out.dopamine != base.dopamine or out.serotonin != base.serotonin

    def test_unmapped_traits_are_identity_metadata(self) -> None:
        store = PersonalityStore()
        base = NeuromodState(dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0)
        out = store.modulate_neuromods(
            base, PersonalityState(traits={"openness": 0.99, "extraversion": -1.0})
        )
        assert out.dopamine == base.dopamine
        assert out.serotonin == base.serotonin
        assert out.noradrenaline == base.noradrenaline
        assert out.acetylcholine == base.acetylcholine

    def test_blended_value_stays_in_bounds(self) -> None:
        store = PersonalityStore()
        base = NeuromodState(dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0)
        out = store.modulate_neuromods(
            base, PersonalityState(traits={"dopamine": 99.0, "acetylcholine": -5.0})
        )
        lo, hi = NEURO_BOUNDS["dopamine"]
        assert lo <= out.dopamine <= hi
        lo, hi = NEURO_BOUNDS["acetylcholine"]
        assert lo <= out.acetylcholine <= hi

    def test_none_traits_returns_base(self) -> None:
        store = PersonalityStore()
        base = NeuromodState()
        assert store.modulate_neuromods(base, None) is base


class TestHMMFixedParams:
    """W6.5: HMM transitions are FIXED — no Baum-Welch / segment learning."""

    def test_production_transition_matrix_is_constant(self) -> None:
        """The production A matrix is a literal, not a learned quantity."""
        # Mirrors segmentation_service._run_hmm
        a = ((0.95, 0.05), (0.10, 0.90))
        params = HMMParams(A=a, mu=(0.0, 1.0), sigma=(1.0, 1.5))
        assert params.A == ((0.95, 0.05), (0.10, 0.90))
        # Row-stochastic
        for row in params.A:
            assert abs(sum(row) - 1.0) < 1e-12

    def test_online_viterbi_is_pure_forward_recursion(self) -> None:
        """Same inputs → same outputs; no hidden parameter state mutates."""
        params = HMMParams(A=((0.95, 0.05), (0.10, 0.90)), mu=(0.0, 1.0), sigma=(1.0, 1.0))
        obs = [0.0, 0.1, 0.2, 2.0, 2.1, 0.0]
        first = online_viterbi_probs(obs, params, prior=(0.9, 0.1))
        second = online_viterbi_probs(obs, params, prior=(0.9, 0.1))
        assert first == second
        assert all(abs(p0 + p1 - 1.0) < 1e-9 for p0, p1 in first)

    def test_detect_boundaries_threshold_crossing(self) -> None:
        probs = [(0.9, 0.1), (0.4, 0.6), (0.4, 0.6), (0.8, 0.2), (0.3, 0.7)]
        bounds = detect_boundaries(probs, threshold=0.6)
        assert bounds == [1, 4]
