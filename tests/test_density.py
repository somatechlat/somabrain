import numpy as np
from memory.density import DensityMatrix


def _random_unit_vector(dim: int) -> np.ndarray:
    vec = np.random.randn(dim)
    norm = np.linalg.norm(vec)
    if norm == 0:
        return _random_unit_vector(dim)
    return vec / norm


def test_density_matrix_psd_and_trace():
    d = 8
    rho = DensityMatrix(d, lam=0.2)
    fillers = np.random.randn(5, d)
    rho.update(fillers)
    assert rho.is_psd(), "Density matrix must be PSD"
    tr = rho.trace()
    assert np.isclose(tr, 1.0, atol=1e-6), f"Trace must be 1, got {tr}"


def test_density_matrix_scoring():
    d = 8
    rho = DensityMatrix(d, lam=0.2)
    fillers = np.random.randn(5, d)
    rho.update(fillers)
    hat_f = np.random.randn(d)
    candidates = np.random.randn(3, d)
    scores = rho.score(hat_f, candidates)
    assert scores.shape == (3,)
    assert np.all(np.isfinite(scores)), "Scores must be finite"


def test_density_matrix_resilience_under_zero_eigenvalues():
    d = 6
    rho = DensityMatrix(d, lam=0.5)
    for _ in range(10):
        fillers = np.zeros((4, d))
        fillers[0] = _random_unit_vector(d)
        rho.update(fillers)
    assert rho.is_psd()
    assert np.isclose(rho.trace(), 1.0, atol=1e-6)


def test_density_matrix_handles_degenerate_updates():
    d = 4
    rho = DensityMatrix(d, lam=0.5)
    degenerate = np.zeros((3, d))
    rho.update(degenerate)
    assert rho.is_psd()
    assert np.isclose(rho.trace(), 1.0, atol=1e-6)
