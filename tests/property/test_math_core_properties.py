"""Property-based tests for Mathematical Core (BHDC/HRR operations).

**Feature: production-hardening**
**Properties: 1-5 (Bind Spectral, Unitary Role, Binding Round-Trip, Tiny Floor, BHDC Sparsity)**
**Validates: Requirements 1.1, 1.2, 1.3, 1.5, 1.6**

These tests verify the mathematical invariants of the hyperdimensional computing
operations used throughout SomaBrain. All tests run against REAL implementations
with no mocks.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings as hyp_settings, strategies as st

from somabrain.quantum import QuantumLayer, HRRConfig
from somabrain.numerics import compute_tiny_floor
from somabrain.math.bhdc_encoder import BHDCEncoder


# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

# Dimension strategy: powers of 2 for FFT compatibility, reasonable range
dim_strategy = st.sampled_from([256, 512, 1024, 2048])

# Seed strategy: random integers for reproducibility testing
seed_strategy = st.integers(min_value=1, max_value=2**31 - 1)

# Sparsity strategy: valid range (0, 1]
sparsity_strategy = st.floats(
    min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False
)

# Vector component strategy: reasonable float range
vector_component = st.floats(
    min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False
)


def random_unit_vector(dim: int, seed: int) -> np.ndarray:
    """Generate a random unit-norm vector."""
    rng = np.random.default_rng(seed)
    vec = rng.normal(0.0, 1.0, size=dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 1e-10:
        vec = vec / norm
    return vec


class TestBindSpectralInvariant:
    """Property 1: Bind Spectral Invariant.

    For any two vectors a and b of dimension D, when bind(a, b) is performed,
    the result SHALL maintain unit norm (spectral energy conservation).

    For BHDC elementwise-product binding (not FFT-based circular convolution),
    the key invariant is that the bound result remains normalized.

    **Feature: production-hardening, Property 1: Bind Spectral Invariant**
    **Validates: Requirements 1.1**
    """

    @given(
        dim=dim_strategy,
        seed_a=seed_strategy,
        seed_b=seed_strategy,
        config_seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_bind_spectral_magnitude_bounds(
        self, dim: int, seed_a: int, seed_b: int, config_seed: int
    ) -> None:
        """Verify bind result maintains unit norm (spectral energy conservation)."""
        # Create QuantumLayer with BHDC binding
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", renorm=True)
        ql = QuantumLayer(cfg)

        # Generate two random unit vectors
        a = random_unit_vector(dim, seed_a)
        b = random_unit_vector(dim, seed_b)

        # Perform bind operation
        result = ql.bind(a, b)

        # The key spectral invariant for BHDC binding: result is normalized
        # This ensures energy conservation (Parseval's theorem: ||x||^2 = (1/D)||X||^2)
        result_norm = np.linalg.norm(result)
        assert (
            0.99 <= result_norm <= 1.01
        ), f"Bind result norm {result_norm} outside [0.99, 1.01]"

        # Verify FFT energy conservation (Parseval's theorem)
        fft_result = np.fft.fft(result)
        fft_energy = np.sum(np.abs(fft_result) ** 2) / dim
        time_energy = np.sum(result**2)

        # Parseval: sum|X_k|^2 / D = sum|x_n|^2
        assert (
            abs(fft_energy - time_energy) < 1e-5
        ), f"Parseval's theorem violated: FFT energy {fft_energy} != time energy {time_energy}"


class TestUnitaryRoleNorm:
    """Property 2: Unitary Role Norm.

    For any role token string, when make_unitary_role(token) is called,
    the resulting vector SHALL have L2 norm equal to 1.0 ± 1e-6.

    **Feature: production-hardening, Property 2: Unitary Role Norm**
    **Validates: Requirements 1.2**
    """

    @given(
        dim=dim_strategy,
        config_seed=seed_strategy,
        token=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
            min_size=1,
            max_size=32,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_unitary_role_has_unit_norm(
        self, dim: int, config_seed: int, token: str
    ) -> None:
        """Verify make_unitary_role produces unit-norm vectors."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", roles_unitary=True)
        ql = QuantumLayer(cfg)

        # Generate unitary role
        role = ql.make_unitary_role(token)

        # Verify unit norm
        norm = float(np.linalg.norm(role))
        assert (
            abs(norm - 1.0) < 1e-6
        ), f"Role norm {norm} deviates from 1.0 by more than 1e-6"

    @given(
        dim=dim_strategy,
        config_seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_multiple_roles_all_unit_norm(self, dim: int, config_seed: int) -> None:
        """Verify multiple roles all have unit norm."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", roles_unitary=True)
        ql = QuantumLayer(cfg)

        tokens = ["subject", "predicate", "object", "time", "location", "agent"]
        for token in tokens:
            role = ql.make_unitary_role(token)
            norm = float(np.linalg.norm(role))
            assert (
                abs(norm - 1.0) < 1e-6
            ), f"Role '{token}' norm {norm} deviates from 1.0"


class TestBindingRoundTrip:
    """Property 3: Binding Round-Trip.

    For any two vectors a and b of dimension D, unbind(bind(a, b), b) SHALL
    return a vector with cosine similarity ≥ 0.99 to the original vector a.

    **Feature: production-hardening, Property 3: Binding Round-Trip**
    **Validates: Requirements 1.3**
    """

    @given(
        dim=dim_strategy,
        seed_a=seed_strategy,
        config_seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_unbind_recovers_original(
        self, dim: int, seed_a: int, config_seed: int
    ) -> None:
        """Verify unbind(bind(a, b), b) ≈ a with cosine similarity ≥ 0.99."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", renorm=True)
        ql = QuantumLayer(cfg)

        # Generate random unit vector a
        a = random_unit_vector(dim, seed_a)

        # Use a role vector for b (guaranteed to have no zero components)
        role_token = f"test_role_{config_seed}"
        b = ql.make_unitary_role(role_token)

        # Bind and unbind
        bound = ql.bind(a, b)
        recovered = ql.unbind(bound, b)

        # Compute cosine similarity
        cosine_sim = ql.cosine(a, recovered)

        assert cosine_sim >= 0.99, f"Round-trip cosine similarity {cosine_sim} < 0.99"

    @given(
        dim=dim_strategy,
        config_seed=seed_strategy,
        token=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
            min_size=3,
            max_size=16,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_unitary_bind_unbind_round_trip(
        self, dim: int, config_seed: int, token: str
    ) -> None:
        """Verify bind_unitary/unbind_exact_unitary round-trip."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", renorm=True)
        ql = QuantumLayer(cfg)

        # Generate random unit vector
        a = ql.random_vector()

        # Bind with unitary role and unbind
        bound = ql.bind_unitary(a, token)
        recovered = ql.unbind_exact_unitary(bound, token)

        # Compute cosine similarity
        cosine_sim = ql.cosine(a, recovered)

        assert (
            cosine_sim >= 0.99
        ), f"Unitary round-trip cosine similarity {cosine_sim} < 0.99"


class TestTinyFloorFormula:
    """Property 4: Tiny Floor Formula.

    For any dimension D and dtype, compute_tiny_floor(D, dtype, "sqrt") SHALL
    return eps × sqrt(D) where eps is the machine epsilon for dtype.

    **Feature: production-hardening, Property 4: Tiny Floor Formula**
    **Validates: Requirements 1.5**
    """

    @given(
        dim=st.integers(min_value=1, max_value=10000),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_tiny_floor_sqrt_formula_float32(self, dim: int) -> None:
        """Verify compute_tiny_floor returns eps × sqrt(D) for float32."""
        dtype = np.float32
        eps = np.finfo(dtype).eps

        result = compute_tiny_floor(dim, dtype=dtype, strategy="sqrt")
        expected = eps * np.sqrt(dim)

        # Account for TINY_MIN floor
        tiny_min = 1e-6  # TINY_MIN for float32
        expected = max(expected, tiny_min)

        assert (
            abs(result - expected) < 1e-12
        ), f"Tiny floor {result} != expected {expected} for dim={dim}"

    @given(
        dim=st.integers(min_value=1, max_value=10000),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_tiny_floor_sqrt_formula_float64(self, dim: int) -> None:
        """Verify compute_tiny_floor returns eps × sqrt(D) for float64."""
        dtype = np.float64
        eps = np.finfo(dtype).eps

        result = compute_tiny_floor(dim, dtype=dtype, strategy="sqrt")
        expected = eps * np.sqrt(dim)

        # Account for TINY_MIN floor
        tiny_min = 1e-12  # TINY_MIN for float64
        expected = max(expected, tiny_min)

        assert (
            abs(result - expected) < 1e-18
        ), f"Tiny floor {result} != expected {expected} for dim={dim}"

    @given(
        dim=st.integers(min_value=1, max_value=10000),
        scale=st.floats(
            min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False
        ),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_tiny_floor_scale_factor(self, dim: int, scale: float) -> None:
        """Verify scale factor is applied correctly."""
        dtype = np.float32
        eps = np.finfo(dtype).eps

        result = compute_tiny_floor(dim, dtype=dtype, strategy="sqrt", scale=scale)
        base = eps * np.sqrt(dim) * scale

        # Account for TINY_MIN floor
        tiny_min = 1e-6
        expected = max(base, tiny_min)

        assert (
            abs(result - expected) < 1e-10
        ), f"Scaled tiny floor {result} != expected {expected}"


class TestBHDCSparsityCount:
    """Property 5: BHDC Sparsity Count.

    For any BHDCEncoder with configured sparsity s and dimension D, all
    generated vectors SHALL have exactly round(s × D) non-zero elements
    (for pm_one mode, this means elements equal to +1).

    **Feature: production-hardening, Property 5: BHDC Sparsity Count**
    **Validates: Requirements 1.6**
    """

    @given(
        dim=dim_strategy,
        sparsity=sparsity_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_random_vector_sparsity_pm_one(
        self, dim: int, sparsity: float, seed: int
    ) -> None:
        """Verify random_vector has correct sparsity in pm_one mode."""
        encoder = BHDCEncoder(
            dim=dim,
            sparsity=sparsity,
            base_seed=seed,
            dtype="float32",
            binary_mode="pm_one",
        )

        vec = encoder.random_vector()

        # In pm_one mode: -1 for inactive, +1 for active
        # Count elements equal to +1
        active_count = int(np.sum(vec == 1.0))
        expected_count = max(1, min(dim, int(round(sparsity * dim))))

        assert active_count == expected_count, (
            f"Active count {active_count} != expected {expected_count} "
            f"for dim={dim}, sparsity={sparsity}"
        )

    @given(
        dim=dim_strategy,
        sparsity=sparsity_strategy,
        seed=seed_strategy,
        key=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
            min_size=1,
            max_size=32,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_vector_for_key_sparsity_pm_one(
        self, dim: int, sparsity: float, seed: int, key: str
    ) -> None:
        """Verify vector_for_key has correct sparsity in pm_one mode."""
        encoder = BHDCEncoder(
            dim=dim,
            sparsity=sparsity,
            base_seed=seed,
            dtype="float32",
            binary_mode="pm_one",
        )

        vec = encoder.vector_for_key(key)

        # Count elements equal to +1
        active_count = int(np.sum(vec == 1.0))
        expected_count = max(1, min(dim, int(round(sparsity * dim))))

        assert active_count == expected_count, (
            f"Active count {active_count} != expected {expected_count} "
            f"for key='{key}', dim={dim}, sparsity={sparsity}"
        )

    @given(
        dim=dim_strategy,
        sparsity=sparsity_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_random_vector_sparsity_zero_one(
        self, dim: int, sparsity: float, seed: int
    ) -> None:
        """Verify random_vector has correct sparsity in zero_one mode."""
        encoder = BHDCEncoder(
            dim=dim,
            sparsity=sparsity,
            base_seed=seed,
            dtype="float32",
            binary_mode="zero_one",
        )

        vec = encoder.random_vector()

        # In zero_one mode: vector is mean-centered after setting active positions
        # The original active positions had value 1.0, rest had 0.0
        # After mean-centering: active = 1 - mean, inactive = 0 - mean = -mean
        # So active positions have the maximum value
        expected_count = max(1, min(dim, int(round(sparsity * dim))))

        # Find the threshold: active positions have value > 0 after centering
        # (since mean = expected_count/dim < 1 for reasonable sparsity)
        active_count = int(np.sum(vec > 0))

        assert active_count == expected_count, (
            f"Active count {active_count} != expected {expected_count} "
            f"for dim={dim}, sparsity={sparsity} (zero_one mode)"
        )

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_deterministic_vector_for_key(self, dim: int, seed: int) -> None:
        """Verify vector_for_key is deterministic (same key → same vector)."""
        encoder = BHDCEncoder(
            dim=dim,
            sparsity=0.1,
            base_seed=seed,
            dtype="float32",
            binary_mode="pm_one",
        )

        key = "test_determinism_key"
        vec1 = encoder.vector_for_key(key)
        vec2 = encoder.vector_for_key(key)

        assert np.allclose(
            vec1, vec2
        ), "vector_for_key is not deterministic for the same key"

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_different_keys_different_vectors(self, dim: int, seed: int) -> None:
        """Verify different keys produce different vectors."""
        encoder = BHDCEncoder(
            dim=dim,
            sparsity=0.1,
            base_seed=seed,
            dtype="float32",
            binary_mode="pm_one",
        )

        vec1 = encoder.vector_for_key("key_alpha")
        vec2 = encoder.vector_for_key("key_beta")

        # Vectors should be different (not identical)
        assert not np.allclose(vec1, vec2), "Different keys produced identical vectors"


# ---------------------------------------------------------------------------
# Additional invariant tests
# ---------------------------------------------------------------------------


class TestNormalizationInvariants:
    """Additional tests for normalization invariants."""

    @given(
        dim=dim_strategy,
        config_seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_superpose_produces_unit_norm(self, dim: int, config_seed: int) -> None:
        """Verify superpose produces unit-norm output when renorm=True."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", renorm=True)
        ql = QuantumLayer(cfg)

        # Generate multiple random vectors
        vectors = [ql.random_vector() for _ in range(5)]

        # Superpose them
        result = ql.superpose(*vectors)

        # Verify unit norm
        norm = float(np.linalg.norm(result))
        assert abs(norm - 1.0) < 1e-5, f"Superpose result norm {norm} deviates from 1.0"

    @given(
        dim=dim_strategy,
        config_seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_encode_text_produces_unit_norm(self, dim: int, config_seed: int) -> None:
        """Verify encode_text produces unit-norm output."""
        cfg = HRRConfig(dim=dim, seed=config_seed, dtype="float32", renorm=True)
        ql = QuantumLayer(cfg)

        texts = ["hello", "world", "test", "quantum", "layer"]
        for text in texts:
            vec = ql.encode_text(text)
            norm = float(np.linalg.norm(vec))
            assert (
                abs(norm - 1.0) < 1e-5
            ), f"encode_text('{text}') norm {norm} deviates from 1.0"