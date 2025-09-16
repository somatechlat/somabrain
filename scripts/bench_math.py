"""Benchmark old vs new numerics for SomaBrain.

This script compares:
- tiny-floor: old linear (eps * D) vs new sqrt (eps * sqrt(D))
- normalize behavior: legacy_zero vs robust baseline
- unbind: exact division (legacy) vs robust tikhonov/wiener
- unitary role isometry: legacy gaussian-renorm vs spectral role generation

Run: python3 scripts/bench_math.py
"""

import json
import math

import numpy as np

from somabrain.numerics import (
    compute_tiny_floor,
    irfft_norm,
    normalize_array,
    rfft_norm,
)
from somabrain.quantum import HRRConfig, QuantumLayer

# Legacy helpers (emulate old math)


def compute_tiny_floor_legacy(dtype, D, scale=1.0):
    dt = np.dtype(dtype)
    eps = float(np.finfo(dt).eps)
    tiny_min = {np.float32: 1e-6, np.float64: 1e-12}.get(dt.type, 1e-12)
    return float(max(tiny_min, eps * float(D) * scale))


def normalize_array_legacy(x, D, dtype=np.float32):
    # legacy_zero: return zeros when L2 < tiny
    arr = np.asarray(x, dtype=dtype).reshape(-1)
    tiny = compute_tiny_floor_legacy(dtype, D)
    norm = float(np.linalg.norm(arr))
    if norm < tiny:
        return np.zeros_like(arr, dtype=dtype)
    return (arr / max(norm, 1e-30)).astype(dtype)


def unbind_legacy(c, r):
    # exact division in freq domain with tiny epsilon guard
    D = c.size
    C = rfft_norm(c, n=D)
    R = rfft_norm(r, n=D)
    eps = 1e-12
    denom = R.copy()
    small = np.abs(denom) < eps
    denom[small] = denom[small] + eps
    est = irfft_norm(C / denom, n=D).astype(c.dtype)
    return est


# Bench 1: tiny floor comparison

dims = [128, 512, 2048, 8192]
dtypes = [np.float32, np.float64]

tiny_table = []
for dt in dtypes:
    for D in dims:
        new = compute_tiny_floor(D, dtype=dt)
        legacy = compute_tiny_floor_legacy(dt, D)
        tiny_table.append(
            {
                "dtype": str(dt),
                "D": D,
                "legacy": legacy,
                "new": new,
                "ratio": legacy / new if new > 0 else None,
            }
        )

# Bench 2: normalize subtiny behavior

norm_cases = []
for dt in [np.float32]:
    D = 128
    tiny = compute_tiny_floor(D, dtype=dt)
    tiny_vec = np.ones((D,), dtype=dt) * (tiny / (10.0 * math.sqrt(float(D))))
    legacy_out = normalize_array_legacy(tiny_vec, D, dtype=dt)
    new_out = normalize_array(
        tiny_vec,
        axis=D,
        keepdims=False,
        dtype=dt,
        tiny_floor_strategy="sqrt",
        mode="robust",
    )
    # compute L2 norms and sample values
    norm_cases.append(
        {
            "dtype": str(dt),
            "D": D,
            "tiny": tiny,
            "legacy_norm": float(np.linalg.norm(legacy_out)),
            "new_norm": float(np.linalg.norm(new_out)),
            "legacy_sample": legacy_out[:5].tolist(),
            "new_sample": new_out[:5].tolist(),
        }
    )

# Bench 3: unbind recovery under small-denom conditions

unbind_cases = []
cfg = HRRConfig(dim=2048, seed=123, dtype="float32", renorm=True)
ql = QuantumLayer(cfg)
trials = 10
for case in ["random_roles", "small_bins"]:
    errs_new = []
    errs_legacy = []
    for t in range(trials):
        a = ql.random_vector()
        b = ql.random_vector()
        c = ql.bind(a, b)
        # legacy unbind
        a_rec_legacy = unbind_legacy(c, b)
        # new unbind (robust)
        a_rec_new = ql.unbind(c, b)
        err_legacy = float(np.linalg.norm(a - a_rec_legacy))
        err_new = float(np.linalg.norm(a - a_rec_new))
        errs_legacy.append(err_legacy)
        errs_new.append(err_new)
    unbind_cases.append(
        {
            "case": case,
            "legacy_mean_err": np.mean(errs_legacy),
            "new_mean_err": np.mean(errs_new),
            "legacy_max_err": float(np.max(errs_legacy)),
            "new_max_err": float(np.max(errs_new)),
        }
    )

# Bench 4: unitary role isometry

unitary_cases = []
for D in [2048, 4096]:
    cfg = HRRConfig(dim=D, seed=7, dtype="float32", renorm=True)
    q = QuantumLayer(cfg)
    a = q.random_vector()
    # make unitary role (new)
    role_new = (
        q.make_unitary_role("role:test") if hasattr(q, "make_unitary_role") else None
    )
    # legacy role: gaussian renorm
    rng = np.random.default_rng(42)
    role_legacy = rng.normal(size=(D,)).astype(cfg.dtype)
    role_legacy = role_legacy / (np.linalg.norm(role_legacy) + 1e-12)
    # bind norms
    bind_new = q.bind(a, role_new) if role_new is not None else None
    bind_legacy = q.bind(a, role_legacy)
    unitary_cases.append(
        {
            "D": D,
            "a_norm": float(np.linalg.norm(a)),
            "role_new_norm": (
                float(np.linalg.norm(role_new)) if role_new is not None else None
            ),
            "role_legacy_norm": float(np.linalg.norm(role_legacy)),
            "bind_new_norm": (
                float(np.linalg.norm(bind_new)) if bind_new is not None else None
            ),
            "bind_legacy_norm": float(np.linalg.norm(bind_legacy)),
        }
    )

# Collect results
out = {
    "tiny_table": tiny_table,
    "norm_cases": norm_cases,
    "unbind_cases": unbind_cases,
    "unitary_cases": unitary_cases,
}
print(json.dumps(out, indent=2))
