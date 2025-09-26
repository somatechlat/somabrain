import math

import numpy as np

from somabrain.numerics import compute_tiny_floor, normalize_array
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.quantum_pure import PureQuantumLayer


def test_compute_tiny_floor_linear_float32():
    # current implementation uses eps * D and per-dtype tiny_min
    dt = np.float32
    D = 8192
    # default strategy is now 'sqrt'
    eps = float(np.finfo(dt).eps)
    expected_sqrt = max(eps * math.sqrt(float(D)), 1e-6)
    got = compute_tiny_floor(dt, D)
    assert math.isclose(got, expected_sqrt, rel_tol=0.0, abs_tol=0.0)

    # legacy linear strategy is still available explicitly
    expected_linear = max(eps * float(D), 1e-6)
    got_linear = compute_tiny_floor(dt, D, strategy="linear")
    assert math.isclose(got_linear, expected_linear, rel_tol=0.0, abs_tol=0.0)


def test_compute_tiny_floor_linear_float64():
    dt = np.float64
    D = 8192
    # expect sqrt default
    eps = float(np.finfo(dt).eps)
    expected_sqrt = max(eps * math.sqrt(float(D)), 1e-12)
    got = compute_tiny_floor(dt, D)
    assert math.isclose(got, expected_sqrt, rel_tol=0.0, abs_tol=0.0)

    # explicit linear
    expected_linear = max(eps * float(D), 1e-12)
    got_linear = compute_tiny_floor(dt, D, strategy="linear")
    assert math.isclose(got_linear, expected_linear, rel_tol=0.0, abs_tol=0.0)


def test_normalize_array_subtiny_behavior():
    D = 128
    # create a vector with norm smaller than tiny_floor
    dt = np.float32
    tiny = compute_tiny_floor(dt, D)
    # construct a vector with L2 norm < tiny: set each element to tiny / (10*sqrt(D))
    tiny_vec = np.ones((D,), dtype=dt) * (tiny / (10.0 * math.sqrt(float(D))))
    # robust mode: should return zero vector
    out = normalize_array(tiny_vec, D, dt, raise_on_subtiny=False)
    assert isinstance(out, np.ndarray)
    assert out.shape[0] == D
    assert np.allclose(out, np.zeros((D,), dtype=dt))

    # strict mode: should raise
    try:
        normalize_array(tiny_vec, D, dt, raise_on_subtiny=True)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_unbind_sanity_small_dim():
    # small-dim sanity check: QuantumLayer.unbind should not raise and
    # should produce a vector; compare roughly to PureQuantumLayer behavior
    cfg = HRRConfig(
        dim=32, seed=42, dtype="float32", renorm=True, fft_eps=1e-8, beta=1e-6
    )
    q = QuantumLayer(cfg)
    p = PureQuantumLayer(cfg)  # noqa: F841

    a = q.random_vector()
    b = q.random_vector()
    # bind and unbind with production layer
    c = q.bind(a, b)
    recovered = q.unbind(c, b)
    # pure unbind may raise if exact zeros; we only assert production returns
    # a finite vector
    assert isinstance(recovered, np.ndarray)
    assert recovered.shape[0] == cfg.dim
    assert not np.any(np.isnan(recovered))
