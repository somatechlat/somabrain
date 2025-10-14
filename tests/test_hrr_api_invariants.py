import numpy as np
import pytest

from somabrain.quantum import HRRConfig, QuantumLayer


def test_hrr_rejects_wrong_length_vector():
    cfg = HRRConfig(dim=256, seed=123)
    q = QuantumLayer(cfg)

    # too short
    with pytest.raises(ValueError):
        q.bind(np.zeros(10, dtype=cfg.dtype), np.zeros(cfg.dim, dtype=cfg.dtype))

    # too long
    with pytest.raises(ValueError):
        q.bind(
            np.zeros(cfg.dim + 5, dtype=cfg.dtype), np.zeros(cfg.dim, dtype=cfg.dtype)
        )


def test_unbind_regularization_floor():
    cfg = HRRConfig(dim=128, seed=1)
    q = QuantumLayer(cfg)

    # Create random anchors and bind
    a = np.random.randn(cfg.dim).astype(cfg.dtype)
    b = np.random.randn(cfg.dim).astype(cfg.dtype)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)

    c = q.bind(a, b)
    # unbind should not raise and should return a vector of correct dim
    a_est = q.unbind(c, b)
    assert a_est.shape[0] == cfg.dim
    assert not np.any(np.isnan(a_est))
