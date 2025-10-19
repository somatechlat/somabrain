import numpy as np
import pytest

from somabrain.amygdala import AmygdalaSalience, SalienceConfig
from somabrain.neuromodulators import NeuromodState
from somabrain.salience import FDSalienceSketch


def test_fd_salience_boosts_on_residual_energy():
    sketch = FDSalienceSketch(dim=4, rank=2, decay=1.0)
    cfg = SalienceConfig(
        w_novelty=0.0,
        w_error=0.0,
        threshold_store=0.5,
        threshold_act=0.5,
        hysteresis=0.0,
        method="fd",
        w_fd=0.5,
        fd_energy_floor=0.9,
    )
    amy = AmygdalaSalience(cfg, fd_backend=sketch)
    nm = NeuromodState(
        dopamine=0.4, serotonin=0.5, noradrenaline=0.0, acetylcholine=0.0
    )

    v = np.array([1.0, 0.0, 0.0, 0.0])
    s1 = amy.score(0.0, 0.0, nm, v)
    assert s1 == pytest.approx(0.5, rel=1e-6)
    assert amy.last_fd_residual == pytest.approx(1.0, rel=1e-6)
    assert amy.last_fd_capture == pytest.approx(1.0, rel=1e-6)
    assert sketch.psd_ok is True
    assert sketch.trace_norm_error < 1e-6

    s2 = amy.score(0.0, 0.0, nm, v)
    assert s2 < 0.01
    assert amy.last_fd_residual < 0.01


def test_fd_salience_energy_capture_tracks_subspace():
    sketch = FDSalienceSketch(dim=4, rank=2, decay=0.95)
    cfg = SalienceConfig(
        w_novelty=0.0,
        w_error=0.0,
        threshold_store=0.5,
        threshold_act=0.5,
        hysteresis=0.0,
        method="fd",
        w_fd=0.0,
        fd_energy_floor=0.8,
    )
    amy = AmygdalaSalience(cfg, fd_backend=sketch)
    nm = NeuromodState()

    v1 = np.array([1.0, 0.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0, 0.0])

    amy.score(0.0, 0.0, nm, v1)
    capture_after_v1 = amy.last_fd_capture
    amy.score(0.0, 0.0, nm, v2)
    capture_after_v2 = amy.last_fd_capture

    assert capture_after_v1 > 0.99
    assert capture_after_v2 > capture_after_v1 * 0.9
    assert 0.0 <= capture_after_v2 <= 1.0
    assert sketch.trace_norm_error < 1e-4


def test_fd_covariance_psd_and_trace_matches_energy():
    sketch = FDSalienceSketch(dim=3, rank=2, decay=1.0)
    cfg = SalienceConfig(
        w_novelty=0.0,
        w_error=0.0,
        threshold_store=0.0,
        threshold_act=0.0,
        hysteresis=0.0,
        method="fd",
        w_fd=0.1,
        fd_energy_floor=0.8,
    )
    amy = AmygdalaSalience(cfg, fd_backend=sketch)
    nm = NeuromodState()

    vectors = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.5, 0.5, 0.0]),
    ]
    for v in vectors:
        amy.score(0.0, 0.0, nm, v)

    cov = sketch.covariance()
    sym_cov = 0.5 * (cov + cov.T)
    eigvals = np.linalg.eigvalsh(sym_cov)

    assert np.all(eigvals >= -1e-9)
    assert np.allclose(sym_cov, sym_cov.T, atol=1e-9)
    assert pytest.approx(1.0, abs=1e-6) == np.trace(sym_cov)
    if sketch.total_energy > 0:
        expected_ratio = sketch.captured_energy / sketch.total_energy
        assert sketch.capture_ratio == pytest.approx(expected_ratio, rel=1e-6)
    assert sketch.psd_ok is True
    assert sketch.trace_norm_error < 1e-6
