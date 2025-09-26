import numpy as np
from memory.density import DensityMatrix

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
