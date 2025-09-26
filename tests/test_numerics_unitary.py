import numpy as np

from somabrain.numerics import (
    compute_tiny_floor,
    irfft_norm,
    make_unitary_role,
    normalize_array,
    rfft_norm,
)
from somabrain.quantum import bind_unitary, unbind_exact_or_tikhonov_or_wiener


def cosine(a, b):
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def test_roundtrip_unitary_float32():
    rng = np.random.default_rng(0)
    x = rng.normal(size=256).astype(np.float32)
    xr = irfft_norm(rfft_norm(x), n=x.size)
    assert np.max(np.abs(x - xr)) < 1e-6


def test_role_is_unit_L2():
    role = make_unitary_role("A", D=256, global_seed=42, dtype=np.float32)
    assert np.isclose(np.linalg.norm(role), 1.0, atol=1e-6)


def test_bind_unbind_exact_unitary():
    rng = np.random.default_rng(1)
    a = rng.normal(size=256).astype(np.float32)
    a = a / (np.linalg.norm(a) + 1e-30)
    role = make_unitary_role("B", D=256, global_seed=42, dtype=np.float32)
    c = bind_unitary(a, role)
    a_hat = unbind_exact_or_tikhonov_or_wiener(c, role)
    assert cosine(a, a_hat) > 0.999999


def test_normalize_array_modes():
    D = 256
    x = np.zeros(D, dtype=np.float32)
    x[0] = 1e-12
    ta = compute_tiny_floor(D, dtype=np.float32)
    assert ta > 0
    z = normalize_array(x, mode="legacy_zero")
    assert np.allclose(z, 0.0)
    r = normalize_array(x, mode="robust")
    assert np.isclose(np.linalg.norm(r), 1.0, atol=1e-6)
    import pytest

    with pytest.raises(ValueError):
        normalize_array(x, mode="strict")


def test_wiener_improves_under_noise():
    rng = np.random.default_rng(2)
    D = 256
    a = rng.normal(size=D).astype(np.float32)
    a /= np.linalg.norm(a) + 1e-30
    role = make_unitary_role("C", D=D, global_seed=7, dtype=np.float32)
    c_clean = bind_unitary(a, role)
    C = rfft_norm(c_clean)
    noise = (rng.normal(size=C.shape) + 1j * rng.normal(size=C.shape)).astype(
        np.complex64
    ) * 0.05
    c_noisy = irfft_norm(C + noise, n=D).astype(np.float32)
    a_exact = unbind_exact_or_tikhonov_or_wiener(
        c_noisy, role
    )  # exact/Tikhonov as needed
    a_wien = unbind_exact_or_tikhonov_or_wiener(c_noisy, role, snr_db=10.0)  # Wiener
    assert cosine(a, a_wien) >= cosine(a, a_exact) - 1e-9


def test_unbind_snr_sweep_small():
    # Small sweep to ensure Wiener is beneficial at low SNRs across seeds
    D = 256
    seeds = [0, 1, 2]
    snr_low = 0.0
    improvements = []
    for sd in seeds:
        rng2 = np.random.default_rng(sd)
        a = rng2.normal(size=D).astype(np.float32)
        a /= np.linalg.norm(a) + 1e-30
        role = make_unitary_role("sweep_role", D=D, global_seed=42, dtype=np.float32)
        c_clean = bind_unitary(a, role)
        C = rfft_norm(c_clean)
        noise = (rng2.normal(size=C.shape) + 1j * rng2.normal(size=C.shape)).astype(
            np.complex64
        ) * 0.1
        c_noisy = irfft_norm(C + noise, n=D).astype(np.float32)
        a_exact = unbind_exact_or_tikhonov_or_wiener(c_noisy, role)
        a_wien = unbind_exact_or_tikhonov_or_wiener(c_noisy, role, snr_db=snr_low)
        improvements.append(cosine(a, a_wien) - cosine(a, a_exact))
    # On average Wiener should not be worse at low SNR
    assert sum(improvements) / len(improvements) >= -1e-6
