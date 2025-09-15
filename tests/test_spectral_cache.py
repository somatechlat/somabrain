from pathlib import Path

import numpy as np


def test_spectral_cache_roundtrip(tmp_path: Path):
    # Ensure the SOMABRAIN_SPECTRAL_CACHE_DIR env is honored
    import os

    os.environ["SOMABRAIN_SPECTRAL_CACHE_DIR"] = str(tmp_path)
    from somabrain.spectral_cache import get_role, set_role

    token = "__test_token__"
    D = 128
    role_time = np.random.RandomState(0).randn(D).astype("float32")
    # create a fake spectrum (n_bins = D//2 + 1)
    n_bins = D // 2 + 1
    role_fft = (
        np.random.RandomState(1).randn(n_bins)
        + 1j * np.random.RandomState(2).randn(n_bins)
    ).astype(np.complex128)

    set_role(token, role_time, role_fft)
    got = get_role(token)
    assert got is not None
    rt, rf = got
    assert rt.shape == role_time.shape
    assert rf.shape == role_fft.shape
    # dtype checks
    assert rf.dtype == np.complex128
