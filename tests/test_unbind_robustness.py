import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def test_unbind_handles_spectral_null():
    D = 128
    cfg = HRRConfig(dim=D, dtype="float32", renorm=True)
    q = QuantumLayer(cfg)

    # create role with a spectral null: make unitary role then zero a bin
    role_token = "null_role"
    q.make_unitary_role(role_token)
    H = q._role_fft_cache[role_token].copy()
    mid = len(H) // 2
    H[mid] = 0.0 + 0.0j
    q._role_fft_cache[role_token] = H

    from somabrain.numerics import irfft_norm

    role_time = irfft_norm(H, n=D).astype("float32")

    # bind a random vector and attempt unbind via compatibility wrapper
    rng = np.random.default_rng(0)
    a = rng.normal(size=D).astype("float32")
    c = q.bind_unitary(a, role_token)

    from somabrain.quantum import unbind_exact_or_tikhonov_or_wiener

    recovered = unbind_exact_or_tikhonov_or_wiener(c, role_time)

    # ensure we recover a finite normalized vector
    assert recovered.shape[0] == D
    assert np.all(np.isfinite(recovered))
    nrm = float(np.linalg.norm(recovered))
    assert nrm > 0
