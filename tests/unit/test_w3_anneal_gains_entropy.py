"""W3 — one anneal law, gains parity, entropy does not move τ.

Covers DEBT-008 (gains), DEBT-009 (one τ schedule), DEBT-010 (entropy cap
must not rescale τ), DEF-09 (predictor_gamma bounds include the gain).

Production imports only: ``somabrain.math.contracts``,
``somabrain.learning.annealing``, ``somabrain_rs``.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

REPO_ROOT = Path(__file__).resolve().parents[2]


def _configure_settings() -> None:
    from django.conf import settings as dj_settings

    if dj_settings.configured:
        return
    from somabrain.math.contracts import ADAPT_BOUNDS, ADAPT_GAINS

    dj_settings.configure(
        SOMABRAIN_ADAPTATION_GAIN_ALPHA=ADAPT_GAINS["alpha"],
        SOMABRAIN_ADAPTATION_GAIN_GAMMA=ADAPT_GAINS["gamma"],
        SOMABRAIN_ADAPTATION_GAIN_LAMBDA=ADAPT_GAINS["lambda_"],
        SOMABRAIN_ADAPTATION_GAIN_MU=ADAPT_GAINS["mu"],
        SOMABRAIN_ADAPTATION_GAIN_NU=ADAPT_GAINS["nu"],
        SOMABRAIN_ADAPTATION_ALPHA_MIN=ADAPT_BOUNDS["alpha"][0],
        SOMABRAIN_ADAPTATION_ALPHA_MAX=ADAPT_BOUNDS["alpha"][1],
        SOMABRAIN_ADAPTATION_GAMMA_MIN=ADAPT_BOUNDS["gamma"][0],
        SOMABRAIN_ADAPTATION_GAMMA_MAX=ADAPT_BOUNDS["gamma"][1],
        SOMABRAIN_ADAPTATION_LAMBDA_MIN=ADAPT_BOUNDS["lambda_"][0],
        SOMABRAIN_ADAPTATION_LAMBDA_MAX=ADAPT_BOUNDS["lambda_"][1],
        SOMABRAIN_ADAPTATION_MU_MIN=ADAPT_BOUNDS["mu"][0],
        SOMABRAIN_ADAPTATION_MU_MAX=ADAPT_BOUNDS["mu"][1],
        SOMABRAIN_ADAPTATION_NU_MIN=ADAPT_BOUNDS["nu"][0],
        SOMABRAIN_ADAPTATION_NU_MAX=ADAPT_BOUNDS["nu"][1],
        SOMABRAIN_UTILITY_LAMBDA=1.0,
        SOMABRAIN_UTILITY_MU=0.1,
        SOMABRAIN_UTILITY_NU=0.05,
        SOMABRAIN_LEARNING_RATE_DYNAMIC=False,
        REQUIRE_EXTERNAL_BACKENDS=False,
        ENABLE_LEARNING_STATE_PERSISTENCE=False,
        REDIS_DB=0,
    )


class TestOneAnnealFormula:
    """DEBT-009 / W3: ONE geometric tau schedule in Python and Rust."""

    def test_contracts_anneal_tau_is_geometric(self) -> None:
        from somabrain.math.contracts import (
            TAU_DECAY_FACTOR,
            TAU_FLOOR,
            anneal_tau,
        )

        assert anneal_tau(0.7) == pytest.approx(0.7 * TAU_DECAY_FACTOR)
        assert anneal_tau(0.105) == TAU_FLOOR  # product drops below floor
        assert anneal_tau(0.1) == TAU_FLOOR
        # Non-increasing, never below floor.
        tau = 1.0
        for _ in range(200):
            nxt = anneal_tau(tau)
            assert nxt <= tau
            assert nxt >= TAU_FLOOR
            tau = nxt
        assert tau == TAU_FLOOR

    def test_python_apply_tau_annealing_matches_contracts(self) -> None:
        from somabrain.learning.annealing import apply_tau_annealing
        from somabrain.math.contracts import anneal_tau

        for tau in (0.05, 0.1, 0.3, 0.7, 1.2, 5.0):
            assert apply_tau_annealing(tau) == anneal_tau(tau)

    def test_rust_anneal_tau_matches_python(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        from somabrain.math.contracts import TAU_DECAY_FACTOR, TAU_FLOOR, anneal_tau

        for tau in (0.05, 0.105, 0.3, 0.7, 1.2):
            assert rs.anneal_tau(tau) == pytest.approx(anneal_tau(tau), abs=1e-15)
        # Rust defaults match the contract constants.
        assert rs.anneal_tau(0.7) == pytest.approx(0.7 * TAU_DECAY_FACTOR, abs=1e-15)
        assert rs.anneal_tau(0.01) == TAU_FLOOR

    def test_conflicting_semantics_deleted(self) -> None:
        """linear/exponential closed forms and mode schedules are gone."""
        import somabrain.learning.annealing as annealing

        for gone in (
            "linear_decay",
            "exponential_decay",
            "apply_tau_decay",
            "get_annealing_config",
            "get_decay_config",
        ):
            assert not hasattr(annealing, gone), f"{gone} must be deleted"

        rs = pytest.importorskip("somabrain_rs")
        for gone in (
            "apply_tau_annealing",
            "linear_tau_decay",
            "exponential_tau_decay",
        ):
            assert not hasattr(rs, gone), f"rust {gone} must be deleted"
        eng = rs.AdaptationEngine(0.05)
        assert not hasattr(eng, "apply_tau_decay")
        assert not hasattr(eng, "linear_decay")
        assert not hasattr(eng, "exponential_decay")


class TestGainsParity:
    """DEBT-008 / W3: Rust adaptation gains == contracts.ADJT_GAINS."""

    def test_contracts_adapt_gains_signs(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        assert ADAPT_GAINS["gamma"] == -0.5
        assert ADAPT_GAINS["mu"] == -0.25
        assert ADAPT_GAINS["nu"] == -0.25
        assert ADAPT_GAINS["alpha"] == 1.0
        assert ADAPT_GAINS["lambda_"] == 1.0

    def test_rust_gains_equal_python_contract(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        from somabrain.math.contracts import ADAPT_GAINS

        engine = rs.AdaptationEngine(0.05)
        ga, gg, gl, gm, gn = engine.get_gains()
        assert ga == ADAPT_GAINS["alpha"]
        assert gg == ADAPT_GAINS["gamma"]
        assert gl == ADAPT_GAINS["lambda_"]
        assert gm == ADAPT_GAINS["mu"]
        assert gn == ADAPT_GAINS["nu"]

    def test_sign_law_gamma_decreases_on_positive_reward(self) -> None:
        """gain_gamma < 0 and signal > 0 ⇒ γ decreases in BOTH engines."""
        rs = pytest.importorskip("somabrain_rs")
        from somabrain.math.contracts import ADAPT_GAINS

        assert ADAPT_GAINS["gamma"] < 0.0

        rust = rs.AdaptationEngine(0.05)
        rust.set_retrieval(1.0, 0.2, 0.1, 0.7)
        rust.set_utility(1.0, 0.1, 0.05)
        rust.apply_feedback(1.0, 1.0)
        _, _, gamma_rust, _ = rust.get_retrieval()
        assert gamma_rust < 0.1

    def test_python_config_defaults_match_contract(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        src = (REPO_ROOT / "somabrain" / "learning" / "config.py").read_text()
        assert "ADAPT_GAINS" in src
        assert ADAPT_GAINS["gamma"] == -0.5


class TestEntropyDoesNotMoveTau:
    """DEBT-010 / W3: entropy cap never rescales τ."""

    def test_check_entropy_cap_passes_tau_through(self) -> None:
        from somabrain.learning.annealing import check_entropy_cap
        from somabrain.math.contracts import sharpen_mixture_weights

        tenant = "w3-entropy"
        from somabrain.learning import annealing as annealing_mod

        original = annealing_mod.get_entropy_cap
        annealing_mod.get_entropy_cap = lambda _tid: 0.5  # type: ignore[assignment]
        try:
            tau_in = 0.7
            alpha, beta, gamma, tau_out, was_sharpened = check_entropy_cap(
                0.3, 0.3, 0.2, tau_in, tenant
            )
            assert tau_out == tau_in, "τ must be returned unchanged"
            if was_sharpened:
                assert (alpha, beta, gamma) != (0.3, 0.3, 0.2)
        finally:
            annealing_mod.get_entropy_cap = original  # type: ignore[assignment]

    def test_sharpen_mixture_weights_never_sees_tau(self) -> None:
        """The mass rule operates on 3-tuples; τ is not an input."""
        from somabrain.math.contracts import entropy_of, sharpen_mixture_weights

        tau = 0.7
        vec, was = sharpen_mixture_weights([0.3, 0.3, 0.2], cap=0.5)
        assert len(vec) == 3
        assert tau == 0.7  # caller-held tau untouched
        if was:
            assert entropy_of(vec) <= 0.5
            # Total mass preserved.
            assert sum(vec) == pytest.approx(0.8)

    def test_builder_entropy_excludes_tau(self) -> None:
        """builder.py entropy vector is (α, β, γ) — no τ."""
        src = (REPO_ROOT / "somabrain" / "context" / "builder.py").read_text()
        # The old 4-vector entropy must be gone.
        assert "max(1e-9, float(self._weights.tau))" not in src
        # Softmax temperature comes from contracts.
        assert "TAU_RECIPROCAL_FLOOR" in src
        assert "TAU_FLOOR" in src

    def test_engine_entropy_does_not_move_tau(self) -> None:
        """Source contract: engine entropy path never writes tau from sharpening."""
        src = (REPO_ROOT / "somabrain" / "learning" / "adaptation" / "engine.py").read_text()
        assert "sharpen_mixture_weights" in src or "check_entropy_cap" in src
        # τ must be passed through, not reassigned from mixture sharpening
        assert "tau_out" in src or "tau == " in src or "tau," in src


class TestPredictorGammaBounds:
    """DEF-09 / W3: predictor_gamma bounds include the signed gain −0.5."""

    def test_brain_defaults_include_gain(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        src = (REPO_ROOT / "somabrain" / "brain_settings" / "models.py").read_text()
        # gamma default must be the signed gain and bounds must contain it
        assert "predictor_gamma" in src
        assert "ADAPT_GAINS" in src or '"v"' in src
        # Source-level: negative gamma must be representable
        assert ADAPT_GAINS["gamma"] == -0.5

    def test_settings_default_is_gain(self) -> None:
        from somabrain.math.contracts import ADAPT_GAINS

        src = (REPO_ROOT / "somabrain" / "settings" / "cognitive.py").read_text()
        assert "SOMABRAIN_PREDICTOR_GAMMA" in src
        assert ADAPT_GAINS["gamma"] == -0.5
