"""Numerics workbench: run deterministic numeric experiments and write JSON results.

This script is intended to be runnable in the project venv. It exercises:
- tiny-floor calculation across dtypes and dimensions
- unitary FFT roundtrips
- role generation and renormalization
- binding / unbinding paths (exact, tikhonov, wiener)

Outputs a small JSON summary in `benchmarks/workbench_numerics_results.json`.
Now parameterized via CLI and captures provenance metadata alongside results.
"""

from __future__ import annotations

import json
from pathlib import Path
import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

from somabrain.numerics import (
    compute_tiny_floor,
    irfft_norm,
    make_unitary_role,
    rfft_norm,
)

OUT = Path(__file__).resolve().parent / "workbench_numerics_results.json"


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _provenance(extra: dict | None = None) -> dict:
    prov = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "git_sha": _git_sha(),
        "cwd": str(os.getcwd()),
        "executable": sys.executable,
    }
    if extra:
        prov.update(extra)
    return prov


def run(
    D_list: tuple[int, ...] = (128, 256, 1024),
    dtypes: tuple[str, ...] = ("float32", "float64"),
):
    results = {
        "provenance": _provenance(
            {
                "phase": "workbench_core",
                "D_list": list(D_list),
                "dtypes": list(dtypes),
            }
        ),
        "tiny_floor": {},
        "unitary_roundtrip": {},
        "role_norms": {},
        "bind_unbind": {},
    }

    dtype_map = {"float32": np.float32, "float64": np.float64}
    for dtype_name in dtypes:
        dt = dtype_map[dtype_name]
        for D in D_list:
            key = f"{dtype_name}:{D}"
            # static type checkers may be conservative about numpy dtype types
            tiny = compute_tiny_floor(D, dtype=dt)
            results["tiny_floor"][key] = tiny

            # FFT roundtrip
            x = np.random.default_rng(0).normal(size=D).astype(dt)
            X = rfft_norm(x, n=D)
            xr = irfft_norm(X, n=D).astype(dt)
            err = float(np.linalg.norm(x - xr) / (np.linalg.norm(x) + 1e-30))
            results["unitary_roundtrip"][key] = err

            # role generation norm
            role = make_unitary_role("bench_role", D=D, global_seed=42, dtype=dt)
            role_norm = float(np.linalg.norm(role))
            results["role_norms"][key] = role_norm

            # bind/unbind sanity with exact unbind
            a = np.random.default_rng(1).normal(size=D).astype(dt)
            r = role
            # bind
            A = rfft_norm(a, n=D)
            R = rfft_norm(r, n=D)
            C = irfft_norm(A * R, n=D).astype(dt)
            # unbind exact via spectrum division where safe
            a_est = irfft_norm(rfft_norm(C, n=D) / R, n=D).astype(dt)
            cos = float(
                np.dot(a, a_est) / (np.linalg.norm(a) * np.linalg.norm(a_est) + 1e-30)
            )
            results["bind_unbind"][key] = cos

    OUT.write_text(json.dumps(results, indent=2))
    print(f"Wrote workbench results to {OUT}")


def extended_snr_capacity_run(
    D_list: tuple[int, ...] = (512, 1024),
    snr_db_list: tuple[float, ...] = (40.0, 20.0, 10.0, 0.0, -10.0),
    seeds: tuple[int, ...] = (0, 1, 2),
):
    """Run SNR sweep and capacity experiments and save to a separate JSON file."""
    outp = Path(__file__).resolve().parent / "results_numerics.json"

    all_rows = []
    for D in D_list:
        for sd in seeds:
            rng = np.random.default_rng(sd)
            a = rng.normal(size=D).astype(np.float32)
            a = a / (np.linalg.norm(a) + 1e-30)
            role_token = f"bench_role_{D}_{sd}"
            # Use the quantum layer to generate a role and bind
            from somabrain.quantum import HRRConfig, QuantumLayer

            q = QuantumLayer(HRRConfig(dim=D, dtype="float32", renorm=True))
            q.make_unitary_role(role_token)
            c_clean = q.bind_unitary(a, role_token)
            from somabrain.numerics import irfft_norm, rfft_norm

            C = rfft_norm(c_clean)
            S = (C * np.conjugate(C)).real
            mean_power = float(np.mean(S)) if S.size else 1.0

            for snr_db in snr_db_list:
                snr_lin = 10.0 ** (snr_db / 10.0)
                noise_power = mean_power / max(snr_lin, 1e-12)
                noise = (
                    rng.normal(size=C.shape) + 1j * rng.normal(size=C.shape)
                ).astype(np.complex128)
                cur_noise_power = float(np.mean((noise * np.conjugate(noise)).real))
                if cur_noise_power <= 0:
                    cur_noise_power = 1.0
                noise = noise * (noise_power / cur_noise_power) ** 0.5

                C_noisy = C.astype(np.complex128) + noise
                c_noisy = irfft_norm(C_noisy, n=D).astype(np.float32)

                a_exact = q.unbind_exact_unitary(c_noisy, role_token)
                a_wien = q.unbind_wiener(c_noisy, role_token, snr_db=snr_db)

                # Use canonical cosine_similarity from somabrain.math.similarity
                from somabrain.math.similarity import cosine_similarity

                all_rows.append(
                    {
                        "D": D,
                        "seed": int(sd),
                        "snr_db": float(snr_db),
                        "mean_power": mean_power,
                        "exact": {
                            "cosine": cosine_similarity(a, a_exact),
                            "mse": float(np.mean((a - a_exact) ** 2)),
                        },
                        "wiener": {
                            "cosine": cosine_similarity(a, a_wien),
                            "mse": float(np.mean((a - a_wien) ** 2)),
                        },
                    }
                )

    outp.write_text(
        json.dumps(
            {
                "provenance": _provenance(
                    {
                        "phase": "extended_snr_capacity",
                        "D_list": list(D_list),
                        "snr_db_list": list(map(float, snr_db_list)),
                        "seeds": list(map(int, seeds)),
                    }
                ),
                "results": all_rows,
            },
            indent=2,
        )
    )
    print(f"Wrote extended bench results to {outp}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Numerics workbench and extended SNR capacity sweep"
    )
    parser.add_argument(
        "--D",
        dest="D_list",
        nargs="*",
        type=int,
        default=[128, 256, 1024],
        help="Dimensions for core workbench",
    )
    parser.add_argument(
        "--dtype",
        dest="dtypes",
        nargs="*",
        default=["float32", "float64"],
        choices=["float32", "float64"],
        help="Dtypes for core workbench",
    )
    parser.add_argument(
        "--extended-D",
        dest="ext_D_list",
        nargs="*",
        type=int,
        default=[512, 1024],
        help="Dimensions for extended SNR capacity",
    )
    parser.add_argument(
        "--snr",
        dest="snr_db_list",
        nargs="*",
        type=float,
        default=[40.0, 20.0, 10.0, 0.0, -10.0],
        help="SNR values in dB for extended sweep",
    )
    parser.add_argument(
        "--seeds",
        dest="seeds",
        nargs="*",
        type=int,
        default=[0, 1, 2],
        help="Seeds for extended sweep",
    )
    args = parser.parse_args()

    run(D_list=tuple(args.D_list), dtypes=tuple(args.dtypes))
    extended_snr_capacity_run(
        D_list=tuple(args.ext_D_list),
        snr_db_list=tuple(args.snr_db_list),
        seeds=tuple(args.seeds),
    )
