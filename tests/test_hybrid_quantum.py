import numpy as np
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.quantum_hybrid import HybridQuantumLayer


def mse(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    return float(np.mean((a - b) ** 2))


def test_hybrid_encode_and_bind_roundtrip():
    cfg = HRRConfig(dim=256, seed=123, dtype='float32')
    q = QuantumLayer(cfg)
    h = HybridQuantumLayer(cfg)

    text = "the quick brown fox"
    vq = q.encode_text(text)
    vh = h.encode_text(text)
    assert vq.shape == (cfg.dim,)
    assert vh.shape == (cfg.dim,)
    # Make a simple role and bind a random vector
    role = q.make_unitary_role("role1")
    x = q.random_vector()
    bound = q.bind(x, role)
    # Unbind via Wiener/unbind and compare similarity
    recovered = q.unbind(bound, role)
    # with unitary roles exact unbind should be close
    assert mse(x, recovered) < 1e-2

    # Repeat same with hybrid layer (should behave similarly)
    role_h = h.make_unitary_role("role1")
    x2 = h.random_vector()
    bound2 = h.bind(x2, role_h)
    rec2 = h.unbind(bound2, role_h)
    assert mse(x2, rec2) < 1e-2
