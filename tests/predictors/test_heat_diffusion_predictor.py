from __future__ import annotations

import os

import numpy as np
from numpy.testing import assert_allclose
from scipy.linalg import expm

from somabrain.predictors.base import (
    HeatDiffusionPredictor,
    PredictorConfig,
    make_line_graph_laplacian,
    matvec_from_matrix,
)


def _exact_heat(L: np.ndarray, x: np.ndarray, t: float) -> np.ndarray:
    return expm(-t * L) @ x


def test_chebyshev_matches_expm_small_graph(monkeypatch):
    monkeypatch.setenv("SOMA_HEAT_METHOD", "chebyshev")
    n = 5
    L = make_line_graph_laplacian(n)
    x0 = np.zeros(n); x0[0] = 1.0
    t = 0.3
    pred = HeatDiffusionPredictor(apply_A=matvec_from_matrix(L), dim=n, cfg=PredictorConfig(diffusion_t=t, chebyshev_K=40))
    y = pred.salience(x0)
    y_exact = _exact_heat(L, x0, t)
    assert_allclose(y, y_exact, rtol=1e-3, atol=1e-4)


def test_lanczos_matches_expm_small_graph(monkeypatch):
    monkeypatch.setenv("SOMA_HEAT_METHOD", "lanczos")
    n = 5
    L = make_line_graph_laplacian(n)
    x0 = np.zeros(n); x0[0] = 1.0
    t = 0.3
    pred = HeatDiffusionPredictor(apply_A=matvec_from_matrix(L), dim=n, cfg=PredictorConfig(diffusion_t=t, lanczos_m=20))
    y = pred.salience(x0)
    y_exact = _exact_heat(L, x0, t)
    assert_allclose(y, y_exact, rtol=2e-3, atol=2e-4)


def test_error_confidence_monotonic():
    n = 5
    L = make_line_graph_laplacian(n)
    x0 = np.zeros(n); x0[0] = 1.0
    pred = HeatDiffusionPredictor(apply_A=matvec_from_matrix(L), dim=n)
    y = pred.salience(x0)
    # observed identical -> error 0, confidence ~1
    e0, c0 = pred.error_and_confidence(y, y)
    # observed shifted -> larger error, smaller confidence
    obs2 = np.roll(y, 1)
    e1, c1 = pred.error_and_confidence(y, obs2)
    assert e0 <= e1
    assert c0 >= c1
