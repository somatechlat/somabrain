import numpy as np
import pytest

from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.numerics import rfft_norm, normalize_array, compute_tiny_floor

D_SMALL = 256
D_LARGE = 1024  # moderate dimension for property check
SEED = 42


@pytest.mark.parametrize("dim", [D_SMALL, D_LARGE])
def test_role_spectrum_unitarity_and_determinism(dim):
    cfg = HRRConfig(dim=dim, seed=SEED)
    q = QuantumLayer(cfg)  # direct to avoid hybrid/global overrides
    r1 = q.make_unitary_role("token:alpha")
    r2 = q.make_unitary_role("token:alpha")
    assert r1.shape == (dim,)
    assert np.allclose(r1, r2, atol=1e-7)
    H = rfft_norm(r1, n=dim)
    mags = np.abs(H)
    assert np.allclose(mags, 1.0, atol=2e-5)
    # Binding with a unitary role preserves norm (within small tolerance)
    a = q.encode_text("norm-preserve-test")
    c = q.bind(a, r1)
    na = np.linalg.norm(a)
    nc = np.linalg.norm(c)
    assert np.isclose(nc / na, 1.0, atol=5e-4), f"norm ratio {nc/na} deviates"


@pytest.mark.parametrize("dim", [D_SMALL, D_LARGE])
def test_bind_unbind_roundtrip(dim):
    cfg = HRRConfig(dim=dim, seed=SEED)
    q = QuantumLayer(cfg)
    a = q.encode_text("the quick brown fox jumps")
    role_token = "role:context"
    _ = q.make_unitary_role(role_token)
    c = q.bind(a, q._role_cache[role_token])
    a_hat = q.unbind(c, q._role_cache[role_token])
    cos = QuantumLayer.cosine(a, a_hat)
    threshold = 0.985 if dim >= 512 else 0.97
    assert cos >= threshold, f"cos={cos} below threshold {threshold}"


def test_wiener_improves_with_higher_snr():
    cfg = HRRConfig(dim=D_SMALL, seed=SEED)
    q = QuantumLayer(cfg)
    a = q.encode_text("signal-base")
    role_token = "role:carrier"
    _ = q.make_unitary_role(role_token)
    c = q.bind(a, q._role_cache[role_token])
    snrs = [20.0, 40.0, 60.0]
    cosines = []
    for s in snrs:
        a_w = q.unbind_wiener(c, role_token, snr_db=s)
        cosines.append(QuantumLayer.cosine(a, a_w))
    # Basic floor
    assert min(cosines) > 0.9
    # Monotonic non-decreasing
    assert all(
        cosines[i + 1] + 1e-6 >= cosines[i] for i in range(len(cosines) - 1)
    ), cosines


def test_exact_not_worse_than_robust():
    cfg = HRRConfig(dim=D_SMALL, seed=SEED)
    q = QuantumLayer(cfg)
    a = q.encode_text("roundtrip reference")
    role_token = "role:carrier2"
    _ = q.make_unitary_role(role_token)
    c = q.bind(a, q._role_cache[role_token])
    robust = q.unbind(c, q._role_cache[role_token])
    exact = q.unbind_exact_unitary(c, role_token)
    cos_robust = QuantumLayer.cosine(a, robust)
    cos_exact = QuantumLayer.cosine(a, exact)
    assert cos_exact + 1e-6 >= cos_robust


def test_normalize_array_idempotent():
    cfg = HRRConfig(dim=512, seed=SEED)
    q = QuantumLayer(cfg)
    v = q.encode_text("idempotence-check")
    v1 = normalize_array(v)
    v2 = normalize_array(v1)
    assert np.allclose(v1, v2, atol=1e-7)


def test_tiny_floor_scaling():
    d1, d2 = 256, 4096
    t1 = compute_tiny_floor(d1)
    t2 = compute_tiny_floor(d2)
    expected = np.sqrt(d2 / d1)
    ratio = t2 / t1
    assert (
        0.8 * expected <= ratio <= 1.2 * expected
    ), f"ratio {ratio} outside band around {expected}"
