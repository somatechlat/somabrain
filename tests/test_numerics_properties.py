import numpy as np
import pytest
from somabrain.numerics import normalize_array, compute_tiny_floor


def test_normalize_zero_vector_robust_returns_baseline():
    d = 128
    z = np.zeros(d, dtype=np.float32)
    r = normalize_array(z, axis=-1, mode="robust")
    # Expect each entry ~1/sqrt(d)
    expected = 1.0 / np.sqrt(d)
    assert np.allclose(r, expected, atol=1e-7)
    assert np.isclose(np.linalg.norm(r), 1.0, atol=1e-6)


def test_normalize_zero_vector_legacy_zero():
    d = 64
    z = np.zeros(d, dtype=np.float32)
    r = normalize_array(z, axis=-1, mode="legacy_zero")
    assert np.allclose(r, 0.0)


def test_normalize_strict_raises_on_subtiny():
    d = 32
    tiny = compute_tiny_floor(d)
    v = np.full(d, tiny * 0.1, dtype=np.float32)
    with pytest.raises(ValueError):
        _ = normalize_array(v, axis=-1, strict=True, mode="strict")
