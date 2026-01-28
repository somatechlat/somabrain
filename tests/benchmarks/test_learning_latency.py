"""Performance benchmarks for learning hot paths.

Measures latency of:
- Softmax weight computation
- Entropy computation
- Tau annealing

These tests use pytest-benchmark for accurate timing.
Run with: pytest tests/benchmarks/test_learning_latency.py -v --benchmark-only

VIBE Compliance: Real implementations only, performance SLOs documented.
"""

from __future__ import annotations

import numpy as np
import pytest


class TestEntropyLatency:
    """Benchmark entropy computation latency."""

    def test_entropy_computation_pure_python(self, benchmark):
        """Pure Python entropy computation should be fast."""
        import math

        probs = [0.25, 0.25, 0.25, 0.25]

        def compute_entropy():
            return -sum(p * math.log(p) for p in probs if p > 0)

        result = benchmark(compute_entropy)
        # SLO: < 100μs for entropy computation
        assert benchmark.stats.mean < 0.0001, (
            f"Entropy computation took {benchmark.stats.mean * 1e6:.2f}μs, "
            "should be < 100μs"
        )

    def test_entropy_rust_fallback(self, benchmark):
        """Entropy using Rust bridge (or Python fallback)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import _rust_compute_entropy

        probs = [0.25, 0.25, 0.25, 0.25]
        result = benchmark(lambda: _rust_compute_entropy(probs))

        # SLO: < 100μs with Rust acceleration
        assert benchmark.stats.mean < 0.0001, (
            f"Rust entropy took {benchmark.stats.mean * 1e6:.2f}μs, should be < 100μs"
        )


class TestSoftmaxLatency:
    """Benchmark softmax computation latency."""

    def test_softmax_100_memories(self, benchmark):
        """Softmax with 100 memories must complete in <1ms."""
        scores = np.random.randn(100).astype(np.float32)
        tau = 0.7

        def compute_softmax():
            s = scores - scores.max()
            w = np.exp(s / tau)
            return w / w.sum()

        result = benchmark(compute_softmax)

        # SLO: < 1ms for 100-memory softmax
        assert benchmark.stats.mean < 0.001, (
            f"Softmax took {benchmark.stats.mean * 1000:.3f}ms, should be < 1ms"
        )

    def test_softmax_1000_memories(self, benchmark):
        """Softmax with 1000 memories for stress testing."""
        scores = np.random.randn(1000).astype(np.float32)
        tau = 0.7

        def compute_softmax():
            s = scores - scores.max()
            w = np.exp(s / tau)
            return w / w.sum()

        result = benchmark(compute_softmax)

        # SLO: < 5ms for 1000-memory softmax
        assert benchmark.stats.mean < 0.005, (
            f"Large softmax took {benchmark.stats.mean * 1000:.3f}ms, should be < 5ms"
        )


class TestTauAnnealingLatency:
    """Benchmark tau annealing latency."""

    def test_linear_decay(self, benchmark):
        """Linear decay should be extremely fast."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import linear_decay

        result = benchmark(lambda: linear_decay(tau_0=1.0, tau_min=0.1, alpha=0.01, t=50))

        # SLO: < 50μs
        assert benchmark.stats.mean < 0.00005, (
            f"Linear decay took {benchmark.stats.mean * 1e6:.2f}μs, should be < 50μs"
        )

    def test_exponential_decay(self, benchmark):
        """Exponential decay should be extremely fast."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import exponential_decay

        result = benchmark(lambda: exponential_decay(tau_0=1.0, gamma=0.95, t=50))

        # SLO: < 50μs
        assert benchmark.stats.mean < 0.00005, (
            f"Exponential decay took {benchmark.stats.mean * 1e6:.2f}μs, should be < 50μs"
        )

    def test_apply_tau_annealing(self, benchmark):
        """Full tau annealing with config lookup."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import apply_tau_annealing

        tenant_override = {"tau_anneal_mode": "linear", "tau_anneal_rate": 0.01}

        result = benchmark(
            lambda: apply_tau_annealing(
                current_tau=0.7,
                tenant_id="benchmark",
                feedback_count=100,
                tenant_override=tenant_override,
            )
        )

        # SLO: < 200μs for full annealing with config
        assert benchmark.stats.mean < 0.0002, (
            f"Full annealing took {benchmark.stats.mean * 1e6:.2f}μs, should be < 200μs"
        )


class TestEntropyCapLatency:
    """Benchmark entropy cap enforcement latency."""

    def test_check_entropy_cap_no_sharpening(self, benchmark):
        """Entropy cap check when below cap (no sharpening needed)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import check_entropy_cap

        # Already dominated by alpha (low entropy)
        result = benchmark(
            lambda: check_entropy_cap(
                alpha=0.9,
                beta=0.05,
                gamma=0.03,
                tau=0.02,
                tenant_id="benchmark_no_sharpen",
            )
        )

        # SLO: < 100μs for non-sharpening case
        assert benchmark.stats.mean < 0.0001, (
            f"No-sharpen cap check took {benchmark.stats.mean * 1e6:.2f}μs, "
            "should be < 100μs"
        )
