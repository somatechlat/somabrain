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


def _benchmark_mean(benchmark) -> float:
    """Return the measured mean in seconds from pytest-benchmark metadata."""
    return float(benchmark.stats["mean"])


class TestEntropyLatency:
    """Benchmark entropy computation latency."""

    def test_entropy_computation_pure_python(self, benchmark):
        """Pure Python entropy computation should be fast."""
        import math

        probs = [0.25, 0.25, 0.25, 0.25]

        def compute_entropy():
            return -sum(p * math.log(p) for p in probs if p > 0)

        benchmark(compute_entropy)
        mean = _benchmark_mean(benchmark)
        # SLO: < 100μs for entropy computation
        assert mean < 0.0001, (
            f"Entropy computation took {mean * 1e6:.2f}μs, " "should be < 100μs"
        )

    def test_entropy_rust_fallback(self, benchmark):
        """Entropy using Rust bridge (or Python fallback)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import _rust_compute_entropy

        probs = [0.25, 0.25, 0.25, 0.25]
        benchmark(lambda: _rust_compute_entropy(probs))
        mean = _benchmark_mean(benchmark)

        # SLO: < 100μs with Rust acceleration
        assert mean < 0.0001, f"Rust entropy took {mean * 1e6:.2f}μs, should be < 100μs"


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

        benchmark(compute_softmax)
        mean = _benchmark_mean(benchmark)

        # SLO: < 1ms for 100-memory softmax
        assert mean < 0.001, f"Softmax took {mean * 1000:.3f}ms, should be < 1ms"

    def test_softmax_1000_memories(self, benchmark):
        """Softmax with 1000 memories for stress testing."""
        scores = np.random.randn(1000).astype(np.float32)
        tau = 0.7

        def compute_softmax():
            s = scores - scores.max()
            w = np.exp(s / tau)
            return w / w.sum()

        benchmark(compute_softmax)
        mean = _benchmark_mean(benchmark)

        # SLO: < 5ms for 1000-memory softmax
        assert mean < 0.005, f"Large softmax took {mean * 1000:.3f}ms, should be < 5ms"


class TestTauAnnealingLatency:
    """Benchmark the ONE geometric tau anneal latency."""

    def test_apply_tau_annealing(self, benchmark):
        """Geometric anneal step."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import apply_tau_annealing

        benchmark(lambda: apply_tau_annealing(0.7))
        mean = _benchmark_mean(benchmark)

        # SLO: < 50μs
        assert mean < 0.00005, f"Anneal took {mean * 1e6:.2f}μs, should be < 50μs"


class TestEntropyCapLatency:
    """Benchmark entropy cap enforcement latency."""

    def test_check_entropy_cap_no_sharpening(self, benchmark):
        """Entropy cap check when below cap (no sharpening needed)."""
        pytest.importorskip("django")
        import django

        django.setup()

        from somabrain.learning.annealing import check_entropy_cap

        # Already dominated by alpha (low entropy)
        benchmark(
            lambda: check_entropy_cap(
                alpha=0.9,
                beta=0.05,
                gamma=0.03,
                tau=0.02,
                tenant_id="benchmark_no_sharpen",
            )
        )
        mean = _benchmark_mean(benchmark)

        # SLO: < 100μs for non-sharpening case
        assert mean < 0.0001, (
            f"No-sharpen cap check took {mean * 1e6:.2f}μs, " "should be < 100μs"
        )
