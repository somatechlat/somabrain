import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def test_unitary_bind_isometry_float32_D4096():
    cfg = HRRConfig(dim=4096, dtype="float32", renorm=False)
    q = QuantumLayer(cfg)
    _ = q.make_unitary_role("role:test")
    # Use an arbitrary vector (not normalized) to test isometry on raw L2 norm
    v = q._rng.normal(0.0, 1.0, size=cfg.dim).astype(cfg.dtype)
    nv = float(np.linalg.norm(v))
    b = q.bind_unitary(v, "role:test")
    nb = float(np.linalg.norm(b))
    # Isometry: ||B v|| ~= ||v|| within float32 tolerance
    assert abs(nb - nv) <= 1e-5


def test_unbind_exact_recovers_within_tol_float32():
    # Use large dim for realistic spectrum and check max abs error
    cfg = HRRConfig(dim=4096, dtype="float32", renorm=False)
    q = QuantumLayer(cfg)
    _ = q.make_unitary_role("role:exact")
    a = q.random_vector()
    c = q.bind_unitary(a, "role:exact")
    a_rec = q.unbind_exact_unitary(c, "role:exact")
    err = np.max(np.abs(a - a_rec))
    assert err <= 3e-6
