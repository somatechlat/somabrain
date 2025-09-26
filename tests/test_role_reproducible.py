import numpy as np

from somabrain.numerics import make_unitary_role, role_spectrum_from_seed


def test_role_spectrum_reproducible():
    s1 = role_spectrum_from_seed("testrole", D=1024, global_seed=42, dtype=np.float32)
    s2 = role_spectrum_from_seed("testrole", D=1024, global_seed=42, dtype=np.float32)
    assert np.array_equal(s1, s2)


def test_make_unitary_role_reproducible():
    r1 = make_unitary_role("roleA", D=1024, global_seed=7, dtype=np.float32)
    r2 = make_unitary_role("roleA", D=1024, global_seed=7, dtype=np.float32)
    assert np.allclose(r1, r2, atol=0.0, rtol=0.0)
