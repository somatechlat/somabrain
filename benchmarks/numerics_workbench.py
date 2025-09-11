"""Numerics workbench: run deterministic numeric experiments and write JSON results.

This script is intended to be runnable in the project venv. It exercises:
- tiny-floor calculation across dtypes and dimensions
- unitary FFT roundtrips
- role generation and renormalization
- binding / unbinding paths (exact, tikhonov, wiener)

Outputs a small JSON summary in `benchmarks/workbench_numerics_results.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from somabrain.numerics import (compute_tiny_floor, irfft_norm,
                                make_unitary_role, rfft_norm)

OUT = Path(__file__).resolve().parent / "workbench_numerics_results.json"


def run():
    results = {
        "env": {
            "numpy": np.__version__,
        },
        "tiny_floor": {},
        "unitary_roundtrip": {},
        "role_norms": {},
        "bind_unbind": {},
    }

    for dtype in (np.float32, np.float64):
        for D in (128, 256, 1024):
            key = f"{dtype.__name__}:{D}"
            # static type checkers may be conservative about numpy dtype types
            tiny = compute_tiny_floor(D, dtype=dtype)  # type: ignore[arg-type]
            results["tiny_floor"][key] = tiny

            # FFT roundtrip
            x = np.random.default_rng(0).normal(size=D).astype(dtype)
            X = rfft_norm(x, n=D)
            xr = irfft_norm(X, n=D).astype(dtype)
            err = float(np.linalg.norm(x - xr) / (np.linalg.norm(x) + 1e-30))
            results["unitary_roundtrip"][key] = err

            # role generation norm
            role = make_unitary_role("bench_role", D=D, global_seed=42, dtype=dtype)  # type: ignore[arg-type]
            role_norm = float(np.linalg.norm(role))
            results["role_norms"][key] = role_norm

            # bind/unbind sanity with exact unbind
            a = np.random.default_rng(1).normal(size=D).astype(dtype)
            r = role
            # bind
            A = rfft_norm(a, n=D)
            R = rfft_norm(r, n=D)
            C = irfft_norm(A * R, n=D).astype(dtype)
            # unbind exact via spectrum division where safe
            a_est = irfft_norm(rfft_norm(C, n=D) / R, n=D).astype(dtype)
            cos = float(
                np.dot(a, a_est) / (np.linalg.norm(a) * np.linalg.norm(a_est) + 1e-30)
            )
            results["bind_unbind"][key] = cos

    OUT.write_text(json.dumps(results, indent=2))
    print(f"Wrote workbench results to {OUT}")


if __name__ == "__main__":
    run()
