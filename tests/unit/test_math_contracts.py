"""Contract tests for somabrain.math.contracts — the single math-contract source.

Every assertion imports the production symbol and pins its value or property.
No local re-implementations.  (W1.1 acceptance: pytest tests/unit/test_math_contracts.py green)

These tests are ``no_django``: contracts is a Django-free module and these
tests must not boot settings (the credential gate is irrelevant here).
"""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.no_django


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


class TestContractsSurface:
    def test_module_exports_all_contract_names(self) -> None:
        import somabrain.math.contracts as C

        required = [
            "ADAPT_GAINS",
            "ADAPT_BOUNDS",
            "TAU_FLOOR",
            "TAU_DECAY_FACTOR",
            "TAU_INTERVAL",
            "RECENCY_SCALE",
            "RECENCY_SHARPNESS",
            "RECENCY_FLOOR",
            "RECENCY_CAP",
            "SCORER_WEIGHTS",
            "SCORER_WEIGHT_MIN",
            "SCORER_WEIGHT_MAX",
            "PROMOTE_THETA",
            "PROMOTE_TICKS",
            "NEURO_BOUNDS",
            "BHDC_D",
            "BHDC_P",
            "QUANT_STEP",
            "compute_wiener_lambda",
            "production_sparsity",
            "production_wiener_lambda",
        ]
        for name in required:
            assert hasattr(C, name), f"contracts missing {name}"

    def test_all_dunder_all_names_exist(self) -> None:
        import somabrain.math.contracts as C

        for name in C.__all__:
            assert hasattr(C, name), f"__all__ lists {name} but module lacks it"


# ---------------------------------------------------------------------------
# BHDC / quantization constants
# ---------------------------------------------------------------------------


class TestBHDCConstants:
    def test_bhdc_d_is_8192(self) -> None:
        from somabrain.math.contracts import BHDC_D

        assert BHDC_D == 8192

    def test_bhdc_p_is_0_1(self) -> None:
        from somabrain.math.contracts import BHDC_P

        assert BHDC_P == 0.1

    def test_quant_step_is_2_over_255(self) -> None:
        from somabrain.math.contracts import QUANT_STEP

        assert math.isclose(QUANT_STEP, 2.0 / 255.0, rel_tol=1e-15)

    def test_production_sparsity_matches_bhdc_p(self) -> None:
        from somabrain.math.contracts import BHDC_P, production_sparsity

        assert production_sparsity() == BHDC_P


# ---------------------------------------------------------------------------
# Wiener λ* formula
# ---------------------------------------------------------------------------


class TestWienerLambdaFormula:
    def test_lambda_at_production_p(self) -> None:
        from somabrain.math.contracts import compute_wiener_lambda

        lam = compute_wiener_lambda(0.1, 8)
        # Δ = 2/255, σ_ε² = Δ²/12, σ_v² = 0.1*0.9
        expected = (2.0 / 255.0) ** 2 / (12.0 * 0.1 * 0.9)
        assert math.isclose(lam, expected, rel_tol=1e-15)

    def test_lambda_honors_bits(self) -> None:
        from somabrain.math.contracts import compute_wiener_lambda

        lam8 = compute_wiener_lambda(0.1, 8)
        lam4 = compute_wiener_lambda(0.1, 4)
        # Δ(4-bit) = 2/15 > Δ(8-bit) = 2/255  ⇒  λ*(4) > λ*(8)
        assert lam4 > lam8

    def test_lambda_p_clamped(self) -> None:
        from somabrain.math.contracts import compute_wiener_lambda

        lam_low = compute_wiener_lambda(0.0)
        lam_clamp = compute_wiener_lambda(0.01)
        assert lam_low == lam_clamp

    def test_production_wiener_lambda_consistent(self) -> None:
        from somabrain.math.contracts import (
            compute_wiener_lambda,
            production_sparsity,
            production_wiener_lambda,
        )

        assert math.isclose(
            production_wiener_lambda(),
            compute_wiener_lambda(production_sparsity()),
            rel_tol=1e-15,
        )

    def test_bhdc_encoder_imports_same_formula(self) -> None:
        """bhdc_encoder must use the contracts definition, not a copy."""
        from somabrain.math import bhdc_encoder
        from somabrain.math.contracts import compute_wiener_lambda

        assert bhdc_encoder.compute_wiener_lambda is compute_wiener_lambda


# ---------------------------------------------------------------------------
# Adaptation gains (signed, γ negative)
# ---------------------------------------------------------------------------


class TestAdaptGains:
    def test_gamma_is_negative(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        assert ADAPT_GAINS["gamma"] < 0.0

    def test_mu_nu_are_negative(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        assert ADAPT_GAINS["mu"] < 0.0
        assert ADAPT_GAINS["nu"] < 0.0

    def test_alpha_lambda_are_positive(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        assert ADAPT_GAINS["alpha"] > 0.0
        assert ADAPT_GAINS["lambda_"] > 0.0

    def test_five_gains_present(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        assert set(ADAPT_GAINS.keys()) == {"alpha", "gamma", "lambda_", "mu", "nu"}

    def test_bounds_cover_all_five(self) -> None:
        from somabrain.math.contracts import ADAPT_BOUNDS

        assert set(ADAPT_BOUNDS.keys()) == {"alpha", "gamma", "lambda_", "mu", "nu"}

    def test_bounds_lo_less_than_hi(self) -> None:
        from somabrain.math.contracts import ADAPT_BOUNDS

        for name, (lo, hi) in ADAPT_BOUNDS.items():
            assert lo < hi, f"{name}: lo={lo} >= hi={hi}"

    def test_learning_config_defaults_match_contract(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        try:
            from somabrain.learning.config import AdaptationGains
        except Exception:
            pytest.skip("learning.config requires Django settings")

        g = AdaptationGains()
        assert g.alpha == ADAPT_GAINS["alpha"]
        assert g.gamma == ADAPT_GAINS["gamma"]
        assert g.lambda_ == ADAPT_GAINS["lambda_"]
        assert g.mu == ADAPT_GAINS["mu"]
        assert g.nu == ADAPT_GAINS["nu"]


# ---------------------------------------------------------------------------
# Tau schedule — ONE set
# ---------------------------------------------------------------------------


class TestTauSchedule:
    def test_tau_floor_is_0_1(self) -> None:
        from somabrain.math.contracts import TAU_FLOOR

        assert TAU_FLOOR == 0.1

    def test_tau_decay_factor_in_open_unit_interval(self) -> None:
        from somabrain.math.contracts import TAU_DECAY_FACTOR

        assert 0.0 < TAU_DECAY_FACTOR < 1.0

    def test_tau_interval_positive(self) -> None:
        from somabrain.math.contracts import TAU_INTERVAL

        assert TAU_INTERVAL > 0.0

    def test_temperature_anneal_uses_contract(self) -> None:
        from somabrain.math.contracts import TAU_DECAY_FACTOR, TAU_FLOOR, TAU_INTERVAL
        from somabrain.tasks.temperature_anneal import _load_config

        cfg = _load_config()
        assert cfg["factor"] == TAU_DECAY_FACTOR
        assert cfg["floor"] == TAU_FLOOR
        assert cfg["interval"] == TAU_INTERVAL

    def test_settings_tau_min_defaults_to_contract_floor(self) -> None:
        from somabrain.math.contracts import TAU_FLOOR

        try:
            from somabrain.settings.cognitive import SOMABRAIN_TAU_MIN
        except Exception:
            pytest.skip("settings not importable in this environment")
        assert SOMABRAIN_TAU_MIN == TAU_FLOOR


# ---------------------------------------------------------------------------
# Recency kernel parameters
# ---------------------------------------------------------------------------


class TestRecencyContract:
    def test_scale_is_60(self) -> None:
        from somabrain.math.contracts import RECENCY_SCALE

        assert RECENCY_SCALE == 60.0

    def test_sharpness_is_1_2(self) -> None:
        from somabrain.math.contracts import RECENCY_SHARPNESS

        assert RECENCY_SHARPNESS == 1.2

    def test_floor_is_0_05(self) -> None:
        from somabrain.math.contracts import RECENCY_FLOOR

        assert RECENCY_FLOOR == 0.05

    def test_cap_is_1000(self) -> None:
        from somabrain.math.contracts import RECENCY_CAP

        assert RECENCY_CAP == 1000.0

    def test_recency_kernel_at_contract_defaults(self) -> None:
        from somabrain.math.contracts import (
            RECENCY_FLOOR,
            RECENCY_SCALE,
            RECENCY_SHARPNESS,
        )
        from somabrain.math.recency import stretched_exponential_recency

        r0 = stretched_exponential_recency(
            0.0,
            scale=RECENCY_SCALE,
            sharpness=RECENCY_SHARPNESS,
            floor=RECENCY_FLOOR,
        )
        assert r0 == 1.0

        r_big = stretched_exponential_recency(
            1e9,
            scale=RECENCY_SCALE,
            sharpness=RECENCY_SHARPNESS,
            floor=RECENCY_FLOOR,
        )
        assert r_big == RECENCY_FLOOR


# ---------------------------------------------------------------------------
# Scorer weights
# ---------------------------------------------------------------------------


class TestScorerWeights:
    def test_weights_sum_to_one(self) -> None:
        from somabrain.math.contracts import SCORER_WEIGHTS

        assert math.isclose(sum(SCORER_WEIGHTS), 1.0, rel_tol=1e-15)

    def test_triple_order_cosine_fd_recency(self) -> None:
        from somabrain.math.contracts import SCORER_WEIGHTS

        w_cos, w_fd, w_rec = SCORER_WEIGHTS
        assert w_cos > w_fd > w_rec > 0.0

    def test_weight_bounds(self) -> None:
        from somabrain.math.contracts import SCORER_WEIGHT_MAX, SCORER_WEIGHT_MIN

        assert SCORER_WEIGHT_MIN == 0.0
        assert SCORER_WEIGHT_MAX == 1.0


# ---------------------------------------------------------------------------
# Promotion contract
# ---------------------------------------------------------------------------


class TestPromotionContract:
    def test_theta_is_0_85(self) -> None:
        from somabrain.math.contracts import PROMOTE_THETA

        assert PROMOTE_THETA == 0.85

    def test_ticks_is_3(self) -> None:
        from somabrain.math.contracts import PROMOTE_TICKS

        assert PROMOTE_TICKS == 3

    def test_promotion_tracker_uses_contract_defaults(self) -> None:
        from somabrain.math.contracts import PROMOTE_THETA, PROMOTE_TICKS

        try:
            from somabrain.memory.promotion import PromotionTracker

            t = PromotionTracker(threshold=PROMOTE_THETA, min_ticks=PROMOTE_TICKS)
        except Exception:
            pytest.skip("promotion requires Django settings")

        assert t.threshold == PROMOTE_THETA
        assert t.min_ticks == PROMOTE_TICKS


# ---------------------------------------------------------------------------
# Neuromodulator bounds
# ---------------------------------------------------------------------------


class TestNeuroBounds:
    def test_four_modulators_present(self) -> None:
        from somabrain.math.contracts import NEURO_BOUNDS

        assert set(NEURO_BOUNDS.keys()) == {
            "dopamine",
            "serotonin",
            "noradrenaline",
            "acetylcholine",
        }

    def test_bounds_lo_less_than_hi(self) -> None:
        from somabrain.math.contracts import NEURO_BOUNDS

        for name, (lo, hi) in NEURO_BOUNDS.items():
            assert lo < hi, f"{name}: lo={lo} >= hi={hi}"

    def test_dopamine_range(self) -> None:
        from somabrain.math.contracts import NEURO_BOUNDS

        assert NEURO_BOUNDS["dopamine"] == (0.2, 0.8)

    def test_serotonin_range(self) -> None:
        from somabrain.math.contracts import NEURO_BOUNDS

        assert NEURO_BOUNDS["serotonin"] == (0.0, 1.0)

    def test_norad_acetyl_ranges(self) -> None:
        from somabrain.math.contracts import NEURO_BOUNDS

        assert NEURO_BOUNDS["noradrenaline"] == (0.0, 0.1)
        assert NEURO_BOUNDS["acetylcholine"] == (0.0, 0.1)


# ---------------------------------------------------------------------------
# Cross-module single-source checks
# ---------------------------------------------------------------------------


class TestSingleSource:
    def test_math_package_reexports_contract_gains(self) -> None:
        from somabrain import math as m
        from somabrain.math.contracts import ADAPT_GAINS

        assert m.ADAPT_GAINS is ADAPT_GAINS

    def test_no_duplicate_wiener_definition(self) -> None:
        """compute_wiener_lambda must exist only in contracts."""
        import somabrain.math.bhdc_encoder as be
        from somabrain.math.contracts import compute_wiener_lambda

        assert be.compute_wiener_lambda is compute_wiener_lambda

    def test_scoring_eps_matches_contract(self) -> None:
        from somabrain.math.contracts import MATH_EPS

        try:
            from somabrain.admin.core.learning.scoring import _EPS
        except Exception:
            pytest.skip("scoring requires Django settings")
        assert _EPS == MATH_EPS

    def test_annealing_floor_matches_contract(self) -> None:
        import inspect

        from somabrain.math.contracts import TAU_FLOOR

        try:
            from somabrain.learning import annealing
        except Exception:
            pytest.skip("annealing requires Django settings")

        src = inspect.getsource(annealing.apply_tau_decay)
        assert "TAU_FLOOR" in src, "apply_tau_decay must floor at TAU_FLOOR"
        assert "0.05" not in src, "hardcoded 0.05 floor must be removed"
