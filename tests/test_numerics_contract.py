import numpy as np

from somabrain.numerics import compute_tiny_floor, make_unitary_role, normalize_array


def test_tiny_floor_is_amplitude():
    # tiny is amplitude; spectral callers must convert tiny**2 / D for power
    tiny32 = compute_tiny_floor(256, dtype=np.float32)  # type: ignore[arg-type]
    tiny64 = compute_tiny_floor(256, dtype=np.float64)  # type: ignore[arg-type]
    assert tiny32 > 0.0
    assert tiny64 > 0.0
    assert tiny64 <= 1e-2  # sanity upper bound for float64 tiny at D=256


def test_normalize_array_robust_fallback():
    D = 128
    x = np.zeros((D,), dtype=np.float32)
    # robust mode should produce baseline ones/sqrt(D)
    r = normalize_array(x, axis=-1, keepdims=False, dtype=np.float32, mode="robust")
    assert r.shape == x.shape
    # L2 norm should be 1.0
    assert abs(float(np.linalg.norm(r)) - 1.0) < 1e-6


def test_make_unitary_role_unit_norm():
    D = 256
    r = make_unitary_role("unit_test", D=D, global_seed=123, dtype=np.float32)
    assert r.shape[0] == D
    assert abs(float(np.linalg.norm(r)) - 1.0) < 1e-6
