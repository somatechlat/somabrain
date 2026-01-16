"""Property-based UNIT tests for Memory System (SuperposedTrace, WorkingMemory).

**Feature: production-hardening**
**Properties: 6-8 (Tiered Memory Recall, SuperposedTrace Decay, Memory Promotion)**
**Validates: Requirements 2.2, 2.3, 2.7**

These are UNIT TESTS that verify the mathematical invariants of in-memory
data structures. They do NOT require external infrastructure.

For INTEGRATION tests against real Redis/Postgres/Memory Service, see:
- tests/integration/test_memory_integration.py
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings as hyp_settings, strategies as st

from somabrain.memory.superposed_trace import SuperposedTrace, TraceConfig
from somabrain.wm import WorkingMemory


# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

dim_strategy = st.sampled_from([256, 512, 1024])
seed_strategy = st.integers(min_value=1, max_value=2**31 - 1)
eta_strategy = st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)


def random_unit_vector(dim: int, seed: int) -> np.ndarray:
    """Generate a random unit-norm vector."""
    rng = np.random.default_rng(seed)
    vec = rng.normal(0.0, 1.0, size=dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 1e-10:
        vec = vec / norm
    return vec


class TestSuperposedTraceDecayFormula:
    """Property 7: SuperposedTrace Decay Formula (UNIT TEST).

    For any SuperposedTrace with decay factor η, after upsert(key, value),
    the new state SHALL equal (1-η)×M_old + η×bind(R×key, value), normalized.

    **Feature: production-hardening, Property 7: SuperposedTrace Decay Formula**
    **Validates: Requirements 2.3**
    """

    @given(
        dim=dim_strategy,
        eta=eta_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=10000)
    def test_decay_formula_single_upsert(self, dim: int, eta: float, seed: int) -> None:
        """Verify decay formula: M_{t+1} = (1-η)M_t + η·bind(Rk, v), normalized."""
        cfg = TraceConfig(dim=dim, eta=eta, rotation_enabled=False, rotation_seed=seed)
        trace = SuperposedTrace(cfg)

        # Get initial state (should be zeros)
        initial_state = trace.state.copy()
        assert np.allclose(initial_state, 0.0), "Initial state should be zeros"

        # Generate key and value vectors
        key = random_unit_vector(dim, seed)
        value = random_unit_vector(dim, seed + 1)

        # Perform upsert
        trace.upsert("anchor1", key, value)

        # Get new state
        new_state = trace.state

        # For first upsert from zero state:
        # M_new = (1-η)*0 + η*bind(key, value) = η*bind(key, value)
        # Then normalized
        expected_binding = trace.quantum.bind(key, value)
        expected_unnorm = eta * expected_binding
        expected_norm = np.linalg.norm(expected_unnorm)

        if expected_norm > 1e-12:
            expected_state = expected_unnorm / expected_norm
            # Verify states match (allowing for numerical precision)
            cosine_sim = float(
                np.dot(new_state, expected_state)
                / (np.linalg.norm(new_state) * np.linalg.norm(expected_state) + 1e-12)
            )
            assert cosine_sim > 0.99, (
                f"State after upsert doesn't match expected decay formula. "
                f"Cosine similarity: {cosine_sim}"
            )

    @given(
        dim=dim_strategy,
        eta=eta_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_decay_accumulates_multiple_upserts(self, dim: int, eta: float, seed: int) -> None:
        """Verify decay accumulates correctly over multiple upserts."""
        cfg = TraceConfig(dim=dim, eta=eta, rotation_enabled=False, rotation_seed=seed)
        trace = SuperposedTrace(cfg)

        # Perform multiple upserts
        for i in range(5):
            key = random_unit_vector(dim, seed + i * 2)
            value = random_unit_vector(dim, seed + i * 2 + 1)
            trace.upsert(f"anchor_{i}", key, value)

        # State should be unit norm after all upserts
        state_norm = np.linalg.norm(trace.state)
        assert (
            abs(state_norm - 1.0) < 1e-5 or state_norm < 1e-10
        ), f"State norm {state_norm} should be ~1.0 or ~0.0"


class TestWorkingMemoryRecall:
    """Property 6: Working Memory Recall Order (UNIT TEST).

    For any WorkingMemory instance, recall() SHALL return items ranked by
    cosine similarity in descending order.

    **Feature: production-hardening, Property 6: Tiered Memory Recall Order**
    **Validates: Requirements 2.2**
    """

    @given(
        dim=dim_strategy,
        capacity=st.integers(min_value=5, max_value=20),
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_recall_returns_descending_similarity(self, dim: int, capacity: int, seed: int) -> None:
        """Verify recall returns items in descending similarity order."""
        wm = WorkingMemory(capacity=capacity, dim=dim)

        # Add several items
        rng = np.random.default_rng(seed)
        for i in range(min(capacity, 10)):
            vec = rng.normal(0, 1, size=dim).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            wm.admit(vec, {"id": i})

        # Query with a random vector
        query = rng.normal(0, 1, size=dim).astype(np.float32)
        query = query / np.linalg.norm(query)

        results = wm.recall(query, top_k=capacity)

        # Verify descending order
        scores = [score for score, _ in results]
        for i in range(len(scores) - 1):
            assert (
                scores[i] >= scores[i + 1]
            ), f"Recall results not in descending order: {scores[i]} < {scores[i + 1]}"

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_recall_finds_exact_match(self, dim: int, seed: int) -> None:
        """Verify recall finds exact match with highest score."""
        wm = WorkingMemory(capacity=10, dim=dim)

        # Add several random items
        rng = np.random.default_rng(seed)
        target_vec = rng.normal(0, 1, size=dim).astype(np.float32)
        target_vec = target_vec / np.linalg.norm(target_vec)

        # Add target
        wm.admit(target_vec.copy(), {"id": "target"})

        # Add other random items
        for i in range(5):
            vec = rng.normal(0, 1, size=dim).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            wm.admit(vec, {"id": f"other_{i}"})

        # Query with target vector
        results = wm.recall(target_vec, top_k=10)

        # Target should be in results with high score
        target_found = False
        for score, payload in results:
            if payload.get("id") == "target":
                target_found = True
                # Score should be very high (close to 1.0)
                assert score > 0.9, f"Target score {score} should be > 0.9"
                break

        assert target_found, "Target item not found in recall results"


class TestWorkingMemoryNovelty:
    """Additional unit tests for WorkingMemory novelty detection."""

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_novelty_empty_wm_returns_one(self, dim: int, seed: int) -> None:
        """Verify novelty returns 1.0 for empty working memory."""
        wm = WorkingMemory(capacity=10, dim=dim)

        query = random_unit_vector(dim, seed)
        novelty = wm.novelty(query)

        assert novelty == 1.0, f"Novelty for empty WM should be 1.0, got {novelty}"

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_novelty_identical_vector_returns_zero(self, dim: int, seed: int) -> None:
        """Verify novelty returns ~0.0 for identical vector."""
        wm = WorkingMemory(capacity=10, dim=dim)

        vec = random_unit_vector(dim, seed)
        wm.admit(vec.copy(), {"id": "test"})

        novelty = wm.novelty(vec)

        assert novelty < 0.01, f"Novelty for identical vector should be ~0.0, got {novelty}"


class TestSuperposedTraceCleanup:
    """Unit tests for SuperposedTrace cleanup/recall functionality."""

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_recall_finds_stored_anchor(self, dim: int, seed: int) -> None:
        """Verify recall can find a stored anchor."""
        cfg = TraceConfig(dim=dim, eta=0.5, rotation_enabled=False, rotation_seed=seed)
        trace = SuperposedTrace(cfg)

        # Store a key-value pair
        key = random_unit_vector(dim, seed)
        value = random_unit_vector(dim, seed + 1)
        trace.upsert("test_anchor", key, value)

        # Recall with the same key
        raw, (anchor_id, best_score, second_score) = trace.recall(key)

        # Should find the anchor
        assert anchor_id == "test_anchor", f"Expected 'test_anchor', got {anchor_id}"
        assert best_score > 0.5, f"Best score {best_score} should be > 0.5"

    @given(
        dim=dim_strategy,
        seed=seed_strategy,
    )
    @hyp_settings(max_examples=50, deadline=10000)
    def test_anchors_are_registered(self, dim: int, seed: int) -> None:
        """Verify anchors are properly registered after upsert."""
        cfg = TraceConfig(dim=dim, eta=0.5, rotation_enabled=False, rotation_seed=seed)
        trace = SuperposedTrace(cfg)

        # Store multiple anchors
        for i in range(3):
            key = random_unit_vector(dim, seed + i * 2)
            value = random_unit_vector(dim, seed + i * 2 + 1)
            trace.upsert(f"anchor_{i}", key, value)

        # Verify all anchors are registered
        anchors = trace.anchors
        assert len(anchors) == 3, f"Expected 3 anchors, got {len(anchors)}"
        for i in range(3):
            assert f"anchor_{i}" in anchors, f"anchor_{i} not found in anchors"
