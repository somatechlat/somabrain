import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def test_unit_norm_random_and_superpose():
    q = QuantumLayer(HRRConfig(dim=256, seed=1))
    v = q.random_vector()
    u = q.random_vector()
    s = q.superpose(v, u)
    assert abs(np.linalg.norm(v) - 1.0) < 1e-4
    assert abs(np.linalg.norm(u) - 1.0) < 1e-4
    assert abs(np.linalg.norm(s) - 1.0) < 1e-4


def test_bind_unbind_identity_like():
    q = QuantumLayer(HRRConfig(dim=256, seed=2))
    a = q.random_vector()
    b = q.random_vector()
    ab = q.bind(a, b)
    a2 = q.unbind(ab, b)
    # cosine should be high enough given noise in circular correlation
    cos = q.cosine(a, a2)
    assert cos > 0.7


def test_permute_and_inverse():
    q = QuantumLayer(HRRConfig(dim=128, seed=3))
    a = q.random_vector()
    p = q.permute(a, times=5)
    inv = q.permute(p, times=-5)
    assert np.allclose(a, inv, atol=1e-6)
