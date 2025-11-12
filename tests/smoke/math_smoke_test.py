"""Quick smoke tests for core math primitives: QuantumLayer bind/unbind/unitary roles and numerics.

Centralized copy of prior scripts/math_smoke_test.py.
"""

from somabrain.quantum import HRRConfig, make_quantum_layer
from somabrain.numerics import (
    normalize_array,
    compute_tiny_floor,
    rfft_norm,
    spectral_floor_from_tiny,
)
import numpy as np


def approx_equal(a, b, tol=1e-6):
    return abs(a - b) <= tol


def run():
    cfg = HRRConfig(dim=256, seed=42)
    q = make_quantum_layer(cfg)
    a = q.random_vector()
    b = q.random_vector()
    c = q.bind(a, b)
    a_rec = q.unbind(c, b)
    cos = q.cosine(a, a_rec)
    print("bind/unbind cosine:", cos)
    role = q.make_unitary_role("token:hello")
    H = rfft_norm(role, n=cfg.dim)
    mags = np.abs(H)
    print("role spectrum min/max:", float(mags.min()), float(mags.max()))
    tiny = np.zeros((cfg.dim,), dtype=cfg.dtype)
    tiny[0] = 1e-50
    try:
        normed = normalize_array(tiny, axis=-1, dtype=cfg.dtype)
        nrm = float(np.linalg.norm(normed))
        print("normalize tiny norm:", nrm)
    except Exception as e:
        print("normalize raised:", e)
    tf = compute_tiny_floor(cfg.dim, dtype=np.dtype(cfg.dtype))
    print("tiny_floor:", tf)
    print("spectral_floor_from_tiny:", spectral_floor_from_tiny(tf, cfg.dim))


if __name__ == "__main__":
    run()
