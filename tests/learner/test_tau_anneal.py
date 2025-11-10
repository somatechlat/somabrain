"""Tests for tau annealing schedules in AdaptationEngine.

Verifies exponential, step and linear annealing behaviour, per-tenant overrides
and minimum floor clamping. The tests use an isolated AdaptationEngine instance
with synthetic feedback signals.
"""

from __future__ import annotations

import os
import tempfile
import yaml

import pytest

from somabrain.learning.adaptation import AdaptationEngine, RetrievalWeights


def _engine(initial_tau: float, tenant: str = "public") -> AdaptationEngine:
    rw = RetrievalWeights()
    rw.tau = initial_tau
    return AdaptationEngine(retrieval=rw, tenant_id=tenant)


def test_exponential_anneal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_MODE", "exp")
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_RATE", "0.1")  # 10% decay each event
    eng = _engine(0.8)
    for _ in range(3):
        eng.apply_feedback(utility=0.5)
    # 0.8 * 0.9^3
    expected = 0.8 * (0.9**3)
    assert eng.retrieval_weights.tau == pytest.approx(expected, rel=1e-3)


def test_step_anneal_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_MODE", "step")
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_RATE", "0.2")
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL", "2")
    eng = _engine(1.0)
    # First feedback – no decay yet (interval=2)
    eng.apply_feedback(utility=0.1)
    assert eng.retrieval_weights.tau == pytest.approx(1.0)
    # Second feedback – decay applies: tau * (1 - 0.2) = 0.8
    eng.apply_feedback(utility=0.1)
    assert eng.retrieval_weights.tau == pytest.approx(0.8)
    # Third feedback – no decay
    eng.apply_feedback(utility=0.1)
    assert eng.retrieval_weights.tau == pytest.approx(0.8)
    # Fourth feedback – decay again: 0.8 * 0.8 = 0.64
    eng.apply_feedback(utility=0.1)
    assert eng.retrieval_weights.tau == pytest.approx(0.64)


def test_linear_anneal_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_MODE", "linear")
    monkeypatch.setenv("SOMABRAIN_TAU_ANNEAL_RATE", "0.3")
    monkeypatch.setenv("SOMABRAIN_TAU_MIN", "0.25")
    eng = _engine(0.9)
    # Apply enough feedbacks to cross below floor
    eng.apply_feedback(utility=0.0)  # 0.9 - 0.3 = 0.6
    eng.apply_feedback(utility=0.0)  # 0.6 - 0.3 = 0.3
    eng.apply_feedback(utility=0.0)  # 0.3 - 0.3 = 0.0 -> clamp to 0.25
    assert eng.retrieval_weights.tau == pytest.approx(0.25)


def test_per_tenant_override_file(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create YAML overrides file specifying per-tenant exponential anneal
    overrides = {
        "tenantX": {
            "tau_anneal_mode": "exp",
            "tau_anneal_rate": 0.2,
            "tau_min": 0.3,
        }
    }
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        yaml.safe_dump(overrides, tf)
        path = tf.name
    monkeypatch.setenv("SOMABRAIN_LEARNING_TENANTS_FILE", path)
    eng = _engine(0.9, tenant="tenantX")
    eng.apply_feedback(utility=0.5)  # 0.9 * 0.8 = 0.72
    assert eng.retrieval_weights.tau == pytest.approx(0.72)
    # Drive below floor to ensure clamp
    for _ in range(10):
        eng.apply_feedback(utility=0.5)
    assert eng.retrieval_weights.tau >= 0.3
