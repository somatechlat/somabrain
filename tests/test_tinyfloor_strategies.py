import math

import numpy as np

from somabrain.numerics import compute_tiny_floor


def tiny_floor_sqrt_expected(dtype, dim):
    dt = np.dtype(dtype)
    eps = float(np.finfo(dt).eps)
    val = eps * math.sqrt(float(dim))
    # per-dtype clamp used in code
    tiny_min = 1e-6 if dt == np.float32 else 1e-12
    return max(val, tiny_min)


def tiny_floor_linear_expected(dtype, dim):
    dt = np.dtype(dtype)
    eps = float(np.finfo(dt).eps)
    val = eps * float(dim)
    tiny_min = 1e-6 if dt == np.float32 else 1e-12
    return max(val, tiny_min)


def test_tinyfloor_comparison_cases():
    dims = [128, 512, 2048, 8192]
    dtypes = [np.float32, np.float64]
    for dt in dtypes:
        for D in dims:
            # Default strategy is 'sqrt'
            current = compute_tiny_floor(dt, D)
            expected_sqrt = tiny_floor_sqrt_expected(dt, D)
            assert math.isclose(current, expected_sqrt, rel_tol=0.0, abs_tol=0.0)

            # Also allow callers to request legacy linear strategy explicitly
            linear = compute_tiny_floor(dt, D, strategy="linear")
            expected_linear = tiny_floor_linear_expected(dt, D)
            assert math.isclose(linear, expected_linear, rel_tol=0.0, abs_tol=0.0)
            assert linear >= expected_sqrt
