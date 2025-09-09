import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def test_no_nan_inf_across_ops():
    cfg = HRRConfig(dim=2048, dtype="float32", renorm=True)
    q = QuantumLayer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    c = q.bind(a, b)
    d = q.unbind(c, b)
    for x in (a, b, c, d):
        assert np.isfinite(x).all()
        assert np.linalg.norm(x) > 0.0
