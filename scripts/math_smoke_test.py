"""Quick smoke tests for core math primitives: QuantumLayer bind/unbind/unitary roles and numerics."""
from somabrain.quantum import HRRConfig, QuantumLayer, make_quantum_layer
from somabrain.numerics import normalize_array, compute_tiny_floor, rfft_norm, irfft_norm, spectral_floor_from_tiny
import numpy as np


def approx_equal(a, b, tol=1e-6):
    return abs(a - b) <= tol


def run():
    cfg = HRRConfig(dim=256, seed=42)
    q = make_quantum_layer(cfg)
    # random vector
    a = q.random_vector()
    b = q.random_vector()
    # bind/unbind roundtrip
    c = q.bind(a, b)
    a_rec = q.unbind(c, b)
    cos = q.cosine(a, a_rec)
    print("bind/unbind cosine:", cos)
    # unitary role
    role = q.make_unitary_role("token:hello")
    # check role spectrum magnitude
    from somabrain.numerics import rfft_norm
    H = rfft_norm(role, n=cfg.dim)
    mags = np.abs(H)
    print("role spectrum min/max:", float(mags.min()), float(mags.max()))
    # check normalize fallback behavior on tiny vector
    tiny = np.zeros((cfg.dim,), dtype=cfg.dtype)
    tiny[0] = 1e-50
    try:
        normed = normalize_array(tiny, axis=-1, dtype=cfg.dtype)
        nrm = float(np.linalg.norm(normed))
        print("normalize tiny norm:", nrm)
    except Exception as e:
        print("normalize raised:", e)
    # tiny floor values
    tf = compute_tiny_floor(cfg.dim, dtype=np.dtype(cfg.dtype))
    print("tiny_floor:", tf)
    print("spectral_floor_from_tiny:", spectral_floor_from_tiny(tf, cfg.dim))

if __name__ == '__main__':
    run()
