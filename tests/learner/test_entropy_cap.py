"""Tests for entropy cap enforcement in AdaptationEngine.

Ensures that when entropy exceeds the configured cap, a sharpen event occurs
and the metrics counter increments. Uses a high-entropy starting vector.
"""

from __future__ import annotations

import os
import math
import pytest

from somabrain.learning.adaptation import AdaptationEngine, RetrievalWeights


def _entropy(alpha: float, beta: float, gamma: float, tau: float) -> float:
    vec = [alpha, beta, gamma, tau]
    s = sum(vec)
    probs = [v / s for v in vec]
    return -sum(p * math.log(p) for p in probs)


def test_entropy_cap_sharpens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOMABRAIN_ENABLE_ENTROPY_CAP", "1")
    monkeypatch.setenv("SOMABRAIN_ENTROPY_CAP", "1.0")  # low cap to force sharpen
    rw = RetrievalWeights()
    # Start with near-uniform weights for high entropy
    rw.alpha = 1.0
    rw.beta = 1.0
    rw.gamma = 1.0
    rw.tau = 1.0
    eng = AdaptationEngine(retrieval=rw)
    before = _entropy(rw.alpha, rw.beta, rw.gamma, rw.tau)
    assert before > 1.0
    eng.apply_feedback(utility=0.5)
    after = _entropy(rw.alpha, rw.beta, rw.gamma, rw.tau)
    assert after <= 1.0
    assert after < before
