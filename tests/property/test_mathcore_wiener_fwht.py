"""Property tests for W4 mathcore: Wiener λ*, bind/unbind, FWHT guard.

Every assertion targets a **production function** (`somabrain.math.bhdc_encoder`,
`somabrain_rs`, `somabrain.math.similarity`) — no test-local reimplementations
of the formulas under test.

**Feature: production-hardening (W4 Math core / BHDC correctness)**
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from somabrain.math.bhdc_encoder import (
    PRODUCTION_SPARSITY_P,
    PermutationBinder,
    _PythonPermutationBinder,
    compute_wiener_lambda,
    fwht,
    production_sparsity,
    production_wiener_lambda,
)
from somabrain.math.similarity import cosine_error

# Django-free: the math layer under test never touches settings/DB/Vault.
pytestmark = pytest.mark.no_django

dim_strategy = st.sampled_from([64, 128, 256, 512])
seed_strategy = st.integers(min_value=1, max_value=2**31 - 1)
p_strategy = st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False)


def _pm1_codes(dim: int, seed_a: int, seed_b: int) -> tuple[np.ndarray, np.ndarray]:
    """Two dense ±1 codes (the invertible BHDC regime)."""
    rng_a = np.random.default_rng(seed_a)
    rng_b = np.random.default_rng(seed_b)
    a = rng_a.choice([-1.0, 1.0], size=dim).astype(np.float64)
    b = rng_b.choice([-1.0, 1.0], size=dim).astype(np.float64)
    return a, b


class TestWienerLambdaFormula:
    """W4.1: λ* is computed from the formula at production p, not a constant."""

    @given(p_strategy)
    @hyp_settings(max_examples=50, deadline=None)
    def test_formula_is_delta2_over_12pq(self, p: float) -> None:
        """λ*(p) = Δ² / (12 p (1−p)) with Δ = 2/(2^bits − 1)."""
        bits = 8
        delta = 2.0 / (2**bits - 1)
        expected = (delta * delta) / (12.0 * p * (1.0 - p))
        assert abs(compute_wiener_lambda(p, bits) - expected) < 1e-15

    def test_bits_parameter_is_honored(self) -> None:
        assert compute_wiener_lambda(0.1, 8) != compute_wiener_lambda(0.1, 16)

    def test_default_lambda_equals_formula_at_production_p(self) -> None:
        """DEBT-011 acceptance: binder default λ == compute_wiener_lambda(p, 8)."""
        p = production_sparsity()
        binder = PermutationBinder(dim=64, seed=1)
        assert abs(binder.lambda_reg - compute_wiener_lambda(p, 8)) < 1e-15
        assert abs(production_wiener_lambda() - compute_wiener_lambda(p, 8)) < 1e-15
        # Production p is the documented engineering choice 0.1 by default.
        if "SOMABRAIN_BHDC_SPARSITY" not in __import__("os").environ:
            assert p == PRODUCTION_SPARSITY_P

    def test_caller_supplied_p_selects_lambda(self) -> None:
        binder = PermutationBinder(dim=64, seed=1, p=0.2)
        assert abs(binder.lambda_reg - compute_wiener_lambda(0.2, 8)) < 1e-15

    def test_python_and_rust_lambda_agree(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        for p in (0.05, 0.1, 0.25, 0.5):
            assert abs(compute_wiener_lambda(p, 8) - rs.compute_wiener_lambda(p, 8)) < 1e-15


class TestBindUnbindRoundTrip:
    """W4.3: both backends recover ±1 codes with cos ≥ 0.99."""

    @given(dim_strategy, seed_strategy, seed_strategy)
    @hyp_settings(max_examples=50, deadline=2000)
    def test_python_fallback_roundtrip_pm1(
        self, dim: int, seed_a: int, seed_b: int
    ) -> None:
        a, b = _pm1_codes(dim, seed_a, seed_b)
        for mix in ("none", "hadamard"):
            binder = _PythonPermutationBinder(dim=dim, seed=seed_b, mix=mix, p=0.1)
            c = np.asarray(binder.bind(a.tolist(), b.tolist()))
            rec = np.asarray(binder.unbind(c.tolist(), b.tolist()))
            cos = float(np.dot(a, rec) / (np.linalg.norm(a) * np.linalg.norm(rec)))
            assert cos >= 0.99, f"mix={mix} dim={dim}: round-trip cos {cos}"

    @given(dim_strategy, seed_strategy, seed_strategy)
    @hyp_settings(max_examples=50, deadline=2000)
    def test_rust_backend_roundtrip_pm1(self, dim: int, seed_a: int, seed_b: int) -> None:
        pytest.importorskip("somabrain_rs")
        a, b = _pm1_codes(dim, seed_a, seed_b)
        for mix in ("none", "hadamard"):
            binder = PermutationBinder(dim=dim, seed=seed_b, mix=mix)
            c = binder.bind(a, b)
            rec = binder.unbind(c, b)
            cos = float(np.dot(a, rec) / (np.linalg.norm(a) * np.linalg.norm(rec)))
            assert cos >= 0.99, f"mix={mix} dim={dim}: round-trip cos {cos}"

    def test_python_unbind_is_wiener_rule(self) -> None:
        """W4.3 / DEBT-015: unbind = (c ⊙ π(b)) / (π(b)² + λ), then L2."""
        lam = compute_wiener_lambda(0.1, 8)
        binder = _PythonPermutationBinder(dim=8, seed=3, lambda_reg=lam)
        c = np.array([0.5, -1.0, 0.25, 0.0, 1.0, -0.5, 0.75, -0.25])
        b = np.array([0.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0])
        b_perm = np.asarray(binder._permute(b, 1))
        expected = (c * b_perm) / (b_perm * b_perm + lam)
        expected = expected / np.linalg.norm(expected)
        got = np.asarray(binder.unbind(c.tolist(), b.tolist()))
        assert np.allclose(got, expected, atol=1e-12)


class TestFwhtGuard:
    """W4.4: non-2^r input raises ValueError — never a silent no-op."""

    @given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=0, max_size=20))
    @hyp_settings(max_examples=100, deadline=None)
    def test_python_fwht_rejects_non_power_of_two(self, values: list[float]) -> None:
        n = len(values)
        if n == 0 or (n & (n - 1)) != 0:
            with pytest.raises(ValueError):
                fwht(values)
        else:
            out = fwht(values)
            assert len(out) == n

    def test_rust_fwht_rejects_non_power_of_two(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        with pytest.raises(ValueError):
            rs.fwht([1.0, 2.0, 3.0])
        assert len(rs.fwht([1.0, 2.0, 3.0, 4.0])) == 4

    def test_python_and_rust_fwht_agree(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        v = [0.5, -1.0, 2.0, 0.25, 1.0, 0.0, -0.75, 3.0]
        assert np.allclose(fwht(v), rs.fwht(v), atol=1e-12)

    @pytest.mark.parametrize("ctor_kind", ["python", "rust"])
    def test_hadamard_binder_rejects_non_pow2_dim(self, ctor_kind: str) -> None:
        if ctor_kind == "python":
            with pytest.raises(ValueError):
                _PythonPermutationBinder(dim=100, seed=1, mix="hadamard")
        else:
            pytest.importorskip("somabrain_rs")
            with pytest.raises(ValueError):
                PermutationBinder(dim=100, seed=1, mix="hadamard")


class TestCosineErrorFormula:
    """W4.6 / DEBT-019: cosine_error = clamp(1 − cos, 0, 1), no abs."""

    def test_antipodal_is_maximum_error(self) -> None:
        assert cosine_error([1.0, 0.0], [-1.0, 0.0]) == 1.0

    def test_rust_slow_predictor_matches_python(self) -> None:
        rs = pytest.importorskip("somabrain_rs")
        pred = rs.SlowPredictor(max_size=4)
        cases = [
            ([1.0, 0.0], [-1.0, 0.0]),
            ([1.0, 0.0], [1.0, 0.0]),
            ([1.0, 0.0], [0.0, 1.0]),
            ([1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]),
        ]
        for a, b in cases:
            rust_err = float(pred.error(a, b))
            py_err = cosine_error(a, b)
            assert abs(rust_err - py_err) < 1e-12, (a, b, rust_err, py_err)
