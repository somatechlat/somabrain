import numpy as np

from somabrain.numerics import compute_tiny_floor, normalize_array


def test_normalize_array_float32_and_float64():
    x32 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    x64 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    y32 = normalize_array(x32, dtype=np.float32)
    y64 = normalize_array(x64, dtype=np.float64)
    assert y32.dtype == x32.dtype
    assert y64.dtype == x64.dtype
    assert np.all(np.isfinite(y32))
    assert np.all(np.isfinite(y64))


def test_compute_tiny_floor_accepts_dtype_objects():
    # ensure compute_tiny_floor works with dtype objects passed
    f32 = compute_tiny_floor(512, dtype=np.float32)
    f64 = compute_tiny_floor(512, dtype=np.float64)
    assert isinstance(f32, float)
    assert isinstance(f64, float)
    assert f64 <= 1.0 and f32 <= 1.0
