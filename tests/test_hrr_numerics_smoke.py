import numpy as np

from somabrain import numerics as num, roles as roles, seed as s, wiener as wiener


def test_seed_rng_reproducible():
    rng1 = s.rng_from_seed("stable-seed")
    rng2 = s.rng_from_seed("stable-seed")
    assert rng1.integers(0, 1_000_000) == rng2.integers(0, 1_000_000)


def test_unitary_role_roundtrip():
    D = 101
    x = s.random_unit_vector(D, seed=1)
    u_time, U = roles.make_unitary_role(D, seed=42)
    X = num.rfft_norm(x, n=D)
    C = X * U
    # exact unbind via conjugate multiply (unitary role)
    X_est = C * np.conjugate(U)
    x_est = num.irfft_norm(X_est, n=D)
    x_hat = num.normalize_array(x, axis=-1)
    x_est_hat = num.normalize_array(x_est, axis=-1)
    cos = float(np.dot(x_hat, x_est_hat))
    assert cos > 0.9999


def test_wiener_deconvolution_stability():
    D = 128
    x = s.random_unit_vector(D, seed=3)
    _, U = roles.make_unitary_role(D, seed=7)
    X = num.rfft_norm(x, n=D)
    C = X * U
    lam = wiener.tikhonov_lambda_from_snr(20.0)
    X_est = wiener.wiener_deconvolve(C, U, lam)
    x_est = num.irfft_norm(X_est, n=D)
    cos = float(np.dot(num.normalize_array(x), num.normalize_array(x_est)))
    assert cos > 0.99
