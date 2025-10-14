import importlib

import numpy as np
import pytest

from somabrain.quantum import HRRConfig, QuantumLayer


def test_quantum_mask_roundtrip_vector_bind():
    cfg = HRRConfig(dim=256, seed=123, dtype="float32")
    q = QuantumLayer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    bound = q.bind(a, b)
    recovered = q.unbind(bound, b)
    err = np.linalg.norm(a - recovered) / max(np.linalg.norm(a), 1e-9)
    assert err < 1e-5


def test_quantum_hybrid_module_removed():
    with pytest.raises(ImportError):
        importlib.import_module("somabrain.quantum_hybrid")
