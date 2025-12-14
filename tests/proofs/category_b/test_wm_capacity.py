"""Category B1: Working Memory Capacity and Eviction Tests.

**Feature: full-capacity-testing**
**Validates: Requirements B1.1, B1.2, B1.3, B1.4, B1.5**

Unit tests that verify working memory capacity limits and eviction behavior.
These tests run against the REAL WorkingMemory implementation.

The WM implementation uses salience-based eviction as specified in Requirements B1.1:
- Salience = alpha * novelty + gamma * recency
- When capacity is exceeded, the item with lowest salience is evicted
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from somabrain.wm import WorkingMemory


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def make_random_vector(dim: int = 128, seed: int | None = None) -> np.ndarray:
    """Create a random unit-norm vector."""
    if seed is not None:
        np.random.seed(seed)
    vec = np.random.randn(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def make_wm(capacity: int = 5, dim: int = 128) -> WorkingMemory:
    """Create a WorkingMemory instance for testing."""
    return WorkingMemory(capacity=capacity, dim=dim)


# ---------------------------------------------------------------------------
# Test Class: Working Memory Capacity and Eviction
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestWMCapacityAndEviction:
    """Tests for working memory capacity and eviction behavior.

    **Feature: full-capacity-testing, Category B1: Working Memory**
    """

    def test_capacity_limit_enforced(self) -> None:
        """B1.1: WM enforces capacity limit.

        **Feature: full-capacity-testing, Property 13: WM Lowest Salience Eviction**
        **Validates: Requirements B1.1**

        WHEN WM reaches capacity THEN the system SHALL evict items to maintain limit.
        Eviction is based on salience score (lowest salience item is evicted).
        """
        capacity = 5
        wm = make_wm(capacity=capacity, dim=128)

        # Add more items than capacity
        for i in range(10):
            vec = make_random_vector(128, seed=i)
            wm.admit(vec, {"index": i})

        # Verify capacity is enforced
        assert (
            len(wm._items) == capacity
        ), f"Expected {capacity} items, got {len(wm._items)}"

    def test_salience_based_eviction(self) -> None:
        """B1.1: Salience-based eviction removes lowest salience items.

        **Feature: full-capacity-testing, Property 13: WM Lowest Salience Eviction**
        **Validates: Requirements B1.1**

        WHEN WM reaches capacity THEN the system SHALL evict the item with
        lowest salience score (combination of novelty and recency).
        """
        capacity = 3
        wm = make_wm(capacity=capacity, dim=128)

        # Add items 0, 1, 2, 3, 4
        for i in range(5):
            vec = make_random_vector(128, seed=i)
            wm.admit(vec, {"index": i})

        # Verify capacity is maintained
        assert len(wm._items) == capacity, f"Expected {capacity} items, got {len(wm._items)}"

        # The most recent items should generally be retained due to recency boost
        # The exact items retained depend on the salience calculation
        indices = [item.payload["index"] for item in wm._items]
        
        # Most recent item (4) should definitely be retained (highest recency)
        assert 4 in indices, f"Most recent item (4) should be retained, got {indices}"
        
        # Second most recent (3) should also likely be retained
        assert 3 in indices, f"Second most recent item (3) should be retained, got {indices}"

    def test_recency_set_on_admission(self) -> None:
        """B1.2: Recency score is set on admission.

        **Feature: full-capacity-testing**
        **Validates: Requirements B1.2**

        WHEN an item is admitted to WM THEN recency score SHALL be set to maximum.
        """
        wm = make_wm(capacity=5, dim=128)

        before = time.time()
        vec = make_random_vector(128, seed=42)
        wm.admit(vec, {"test": "item"})
        after = time.time()

        # Verify admitted_at timestamp is set
        item = wm._items[0]
        assert item.admitted_at >= before, "admitted_at should be >= test start time"
        assert item.admitted_at <= after, "admitted_at should be <= test end time"

        # Verify tick is set (recency counter)
        assert item.tick == 1, f"Expected tick=1, got {item.tick}"

    def test_tick_increments_on_admission(self) -> None:
        """B1.2: Tick counter increments with each admission.

        **Feature: full-capacity-testing**
        **Validates: Requirements B1.2**
        """
        wm = make_wm(capacity=10, dim=128)

        for i in range(5):
            vec = make_random_vector(128, seed=i)
            wm.admit(vec, {"index": i})

        # Verify ticks increment
        ticks = [item.tick for item in wm._items]
        assert ticks == [1, 2, 3, 4, 5], f"Expected [1,2,3,4,5], got {ticks}"

    def test_recall_ranking_by_similarity(self) -> None:
        """B1.5: Results are ranked by similarity.

        **Feature: full-capacity-testing**
        **Validates: Requirements B1.5**

        WHEN WM is queried THEN results SHALL be ranked by combined salience and recency.
        (Current implementation ranks by cosine similarity with recency adjustment)
        """
        wm = make_wm(capacity=10, dim=128)

        # Create a target vector
        target = make_random_vector(128, seed=100)

        # Add items with varying similarity to target
        for i in range(5):
            # Create vectors with different similarities
            if i == 2:
                # Make this one very similar to target
                vec = target + np.random.randn(128).astype(np.float32) * 0.1
                vec = vec / np.linalg.norm(vec)
            else:
                vec = make_random_vector(128, seed=i)
            wm.admit(vec, {"index": i})

        # Recall with target as query
        results = wm.recall(target, top_k=5)

        # Verify results are sorted by score (descending)
        scores = [score for score, _ in results]
        assert scores == sorted(
            scores, reverse=True
        ), "Results should be sorted by score descending"

        # The most similar item (index 2) should be first or near first
        top_indices = [payload["index"] for _, payload in results[:2]]
        assert 2 in top_indices, f"Expected index 2 in top results, got {top_indices}"

    def test_novelty_detection(self) -> None:
        """Novelty detection works correctly.

        **Feature: full-capacity-testing**
        **Validates: Requirements B1 (novelty is part of salience)**
        """
        wm = make_wm(capacity=10, dim=128)

        # Empty WM should have max novelty
        vec1 = make_random_vector(128, seed=1)
        novelty_empty = wm.novelty(vec1)
        assert (
            novelty_empty == 1.0
        ), f"Empty WM should have novelty=1.0, got {novelty_empty}"

        # Add the vector
        wm.admit(vec1, {"test": 1})

        # Same vector should have low novelty
        novelty_same = wm.novelty(vec1)
        assert (
            novelty_same < 0.1
        ), f"Same vector should have low novelty, got {novelty_same}"

        # Different vector should have higher novelty
        vec2 = make_random_vector(128, seed=999)
        novelty_diff = wm.novelty(vec2)
        assert (
            novelty_diff > novelty_same
        ), "Different vector should have higher novelty"

    def test_dimension_normalization_padding(self) -> None:
        """Vectors shorter than dim are padded.

        **Feature: full-capacity-testing**
        """
        wm = make_wm(capacity=5, dim=128)

        # Admit a shorter vector
        short_vec = np.random.randn(64).astype(np.float32)
        wm.admit(short_vec, {"test": "short"})

        # Verify stored vector has correct dimension
        stored = wm._items[0].vector
        assert stored.shape[0] == 128, f"Expected dim=128, got {stored.shape[0]}"

    def test_dimension_normalization_truncation(self) -> None:
        """Vectors longer than dim are truncated.

        **Feature: full-capacity-testing**
        """
        wm = make_wm(capacity=5, dim=128)

        # Admit a longer vector
        long_vec = np.random.randn(256).astype(np.float32)
        wm.admit(long_vec, {"test": "long"})

        # Verify stored vector has correct dimension
        stored = wm._items[0].vector
        assert stored.shape[0] == 128, f"Expected dim=128, got {stored.shape[0]}"

    def test_vectors_are_unit_normalized(self) -> None:
        """All stored vectors are unit-normalized.

        **Feature: full-capacity-testing**
        """
        wm = make_wm(capacity=5, dim=128)

        # Admit vectors with various norms
        for i in range(5):
            vec = np.random.randn(128).astype(np.float32) * (i + 1) * 10
            wm.admit(vec, {"index": i})

        # Verify all stored vectors are unit-norm
        for item in wm._items:
            norm = np.linalg.norm(item.vector)
            assert abs(norm - 1.0) < 1e-5, f"Expected unit norm, got {norm}"


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestWMPropertyBased:
    """Property-based tests for working memory.

    **Feature: full-capacity-testing, Category B1**
    """

    @given(
        capacity=st.integers(min_value=1, max_value=100),
        num_items=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=50, deadline=None)
    def test_capacity_never_exceeded(self, capacity: int, num_items: int) -> None:
        """Property: WM never exceeds capacity.

        **Feature: full-capacity-testing, Property 13**
        **Validates: Requirements B1.1**

        *For any* capacity and number of admitted items, WM size SHALL never exceed capacity.
        """
        wm = WorkingMemory(capacity=capacity, dim=64)

        for i in range(num_items):
            vec = np.random.randn(64).astype(np.float32)
            wm.admit(vec, {"i": i})

        assert (
            len(wm._items) <= capacity
        ), f"WM exceeded capacity: {len(wm._items)} > {capacity}"

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, deadline=None)
    def test_recall_returns_at_most_top_k(self, top_k: int) -> None:
        """Property: Recall returns at most top_k items.

        **Feature: full-capacity-testing, Property 17**
        **Validates: Requirements B2.2**

        *For any* top_k, recall SHALL return at most top_k items.
        """
        wm = WorkingMemory(capacity=100, dim=64)

        # Add some items
        for i in range(30):
            vec = np.random.randn(64).astype(np.float32)
            wm.admit(vec, {"i": i})

        query = np.random.randn(64).astype(np.float32)
        results = wm.recall(query, top_k=top_k)

        assert (
            len(results) <= top_k
        ), f"Recall returned more than top_k: {len(results)} > {top_k}"

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_novelty_bounded_zero_one(self, num_items: int) -> None:
        """Property: Novelty is always in [0, 1].

        **Feature: full-capacity-testing**

        *For any* WM state, novelty SHALL be bounded in [0.0, 1.0].
        """
        wm = WorkingMemory(capacity=50, dim=64)

        for i in range(num_items):
            vec = np.random.randn(64).astype(np.float32)
            wm.admit(vec, {"i": i})

        query = np.random.randn(64).astype(np.float32)
        novelty = wm.novelty(query)

        assert 0.0 <= novelty <= 1.0, f"Novelty out of bounds: {novelty}"
