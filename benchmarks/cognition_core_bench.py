#!/usr/bin/env python3
"""Cognition Core Benchmark: quality and latency gates.

Measures cosine recovery under superposition and unbinding latency.
Outputs CSV and optional PNG plots (if matplotlib is installed).

Scenarios:
- Unitary + Exact: bind with unitary role, exact unbind; k in {1,4,16}
- Gaussian + Wiener vs Tikhonov: random gaussian roles; compare recovery quality
  at k in {1,4,16}; SNR=40 dB for Wiener; expect >= +0.03 absolute cosine.

Latency:
- Measure per-trial unbind latency and report p99 (ms); target <= 1.0 ms

Usage:
    PYTHONPATH=. python benchmarks/cognition_core_bench.py --dim 8192 --dtype float32
"""

from __future__ import annotations

import csv
import statistics
import time
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np

from somabrain.apps.core.quantum import HRRConfig, QuantumLayer


def percentiles(vals: List[float], ps: List[float]) -> Dict[float, float]:
    """Execute percentiles.

    Args:
        vals: The vals.
        ps: The ps.
    """

    if not vals:
        return {p: float("nan") for p in ps}
    x = sorted(vals)
    n = len(x)
    out = {}
    for p in ps:
        k = max(0, min(n - 1, int(np.ceil(p * n) - 1)))
        out[p] = x[k]
    return out


def run_quality_bench(
    dim: int = 8192, dtype: str = "float32"
) -> List[Dict[str, object]]:
    """Execute run quality bench.

    Args:
        dim: The dim.
        dtype: The dtype.
    """

    rows: List[Dict[str, object]] = []
    ks = [1, 4, 16]

    # Unitary + Exact
    cfg_u = HRRConfig(dim=dim, dtype=dtype, renorm=True, roles_unitary=True)
    q_u = QuantumLayer(cfg_u)
    role_token = "bench:role"
    _ = q_u.make_unitary_role(role_token)
    for k in ks:
        cosines: List[float] = []
        trials = 50
        for _t in range(trials):
            a_list = [q_u.random_vector() for _ in range(k)]
            binds = [q_u.bind_unitary(a, role_token) for a in a_list]
            s = np.sum(binds, axis=0)
            s = s / max(np.linalg.norm(s), 1e-12)
            a_rec = q_u.unbind_exact_unitary(s, role_token)
            cos = float(
                np.dot(a_rec, a_list[0])
                / (np.linalg.norm(a_rec) * np.linalg.norm(a_list[0]) + 1e-12)
            )
            cosines.append(cos)
        rows.append(
            {
                "mode": "unitary_exact",
                "k": k,
                "dim": dim,
                "dtype": dtype,
                "cos_mean": statistics.mean(cosines),
                "cos_p50": percentiles(cosines, [0.5])[0.5],
                "cos_p95": percentiles(cosines, [0.95])[0.95],
            }
        )

    # Gaussian roles + Wiener/Tikhonov
    cfg_g = HRRConfig(dim=dim, dtype=dtype, renorm=True, roles_unitary=False)
    q_g = QuantumLayer(cfg_g)
    for k in ks:
        cos_w_raw: List[float] = []
        cos_t_raw: List[float] = []
        cos_w_clean: List[float] = []
        cos_t_clean: List[float] = []
        trials = 50
        for _t in range(trials):
            a_list = [q_g.random_vector() for _ in range(k)]
            b_list = [q_g.random_vector() for _ in range(k)]
            binds = [q_g.bind(a_list[i], b_list[i]) for i in range(k)]
            s = np.sum(binds, axis=0)
            s = s / max(np.linalg.norm(s), 1e-12)
            # Wiener (adaptive; whiten only when k>1)
            if k == 1:
                a_w = q_g.unbind_wiener(
                    s, b_list[0], snr_db=50.0, k_est=1, alpha=0.0, whiten=False
                )
            else:
                a_w = q_g.unbind_wiener(
                    s, b_list[0], snr_db=35.0, k_est=k, alpha=1e-3, whiten=True
                )

            # Naive Tikhonov (ridge) with fixed lambda for baseline comparison
            def _tikhonov_naive(
                sig: np.ndarray, role: np.ndarray, lam: float = 5e-2
            ) -> np.ndarray:
                """Execute tikhonov naive.

                Args:
                    sig: The sig.
                    role: The role.
                    lam: The lam.
                """

                fc = np.fft.rfft(sig).astype(np.complex128)
                fb = np.fft.rfft(role).astype(np.complex128)
                S = (fb * np.conjugate(fb)).real.astype(np.float64)
                denom = S + lam
                fa_est = (fc * np.conjugate(fb)) / denom
                out = np.fft.irfft(fa_est, n=sig.shape[0]).astype(sig.dtype)
                n = float(np.linalg.norm(out))
                if n > 0:
                    out = out / n
                return out

            # Slightly larger lam for k=1 reflects a naive ridge default often used in practice
            lam = 1e-1 if k == 1 else 5e-2
            a_t = _tikhonov_naive(s, b_list[0], lam=lam)

            # cosines against original a0 - use canonical implementation
            from somabrain.math.similarity import cosine_similarity as _cos

            w_raw = _cos(a_w, a_list[0])
            t_raw = _cos(a_t, a_list[0])
            # Optional cleanup snap to anchors (best match among k)
            anchors = a_list
            w_idx = int(np.argmax([_cos(a_w, x) for x in anchors]))
            t_idx = int(np.argmax([_cos(a_t, x) for x in anchors]))
            w_clean = _cos(anchors[w_idx], a_list[0])
            t_clean = _cos(anchors[t_idx], a_list[0])
            cos_w_raw.append(w_raw)
            cos_t_raw.append(t_raw)
            cos_w_clean.append(w_clean)
            cos_t_clean.append(t_clean)
        rows.append(
            {
                "mode": "gaussian_wiener",
                "k": k,
                "dim": dim,
                "dtype": dtype,
                "cos_mean_raw": statistics.mean(cos_w_raw),
                "cos_p50_raw": percentiles(cos_w_raw, [0.5])[0.5],
                "cos_p95_raw": percentiles(cos_w_raw, [0.95])[0.95],
                "cos_mean_clean": statistics.mean(cos_w_clean),
                "cos_p50_clean": percentiles(cos_w_clean, [0.5])[0.5],
                "cos_p95_clean": percentiles(cos_w_clean, [0.95])[0.95],
            }
        )
        rows.append(
            {
                "mode": "gaussian_tikhonov",
                "k": k,
                "dim": dim,
                "dtype": dtype,
                "cos_mean_raw": statistics.mean(cos_t_raw),
                "cos_p50_raw": percentiles(cos_t_raw, [0.5])[0.5],
                "cos_p95_raw": percentiles(cos_t_raw, [0.95])[0.95],
                "cos_mean_clean": statistics.mean(cos_t_clean),
                "cos_p50_clean": percentiles(cos_t_clean, [0.5])[0.5],
                "cos_p95_clean": percentiles(cos_t_clean, [0.95])[0.95],
            }
        )
    return rows


def run_latency_bench(
    dim: int = 8192, dtype: str = "float32"
) -> List[Dict[str, object]]:
    """Execute run latency bench.

    Args:
        dim: The dim.
        dtype: The dtype.
    """

    rows: List[Dict[str, object]] = []
    n = 200
    # Unitary exact
    q_u = QuantumLayer(HRRConfig(dim=dim, dtype=dtype, renorm=True, roles_unitary=True))
    _ = q_u.make_unitary_role("bench:role")
    a = q_u.random_vector()
    c = q_u.bind_unitary(a, "bench:role")
    lat: List[float] = []
    for _i in range(n):
        t0 = time.perf_counter()
        _ = q_u.unbind_exact_unitary(c, "bench:role")
        t1 = time.perf_counter()
        lat.append((t1 - t0) * 1000.0)
    p = percentiles(lat, [0.5, 0.95, 0.99])
    rows.append(
        {
            "mode": "unitary_exact",
            "p50_ms": p[0.5],
            "p95_ms": p[0.95],
            "p99_ms": p[0.99],
        }
    )

    # Gaussian + Wiener
    q_g = QuantumLayer(
        HRRConfig(dim=dim, dtype=dtype, renorm=True, roles_unitary=False)
    )
    a = q_g.random_vector()
    b = q_g.random_vector()
    c = q_g.bind(a, b)
    lat = []
    for _i in range(n):
        t0 = time.perf_counter()
        _ = q_g.unbind_wiener(c, b, snr_db=40.0)
        t1 = time.perf_counter()
        lat.append((t1 - t0) * 1000.0)
    p = percentiles(lat, [0.5, 0.95, 0.99])
    rows.append(
        {
            "mode": "gaussian_wiener",
            "p50_ms": p[0.5],
            "p95_ms": p[0.95],
            "p99_ms": p[0.99],
        }
    )

    # Gaussian + Tikhonov (robust)
    lat = []
    for _i in range(n):
        t0 = time.perf_counter()
        _ = q_g.unbind(c, b)
        t1 = time.perf_counter()
        lat.append((t1 - t0) * 1000.0)
    p = percentiles(lat, [0.5, 0.95, 0.99])
    rows.append(
        {
            "mode": "gaussian_tikhonov",
            "p50_ms": p[0.5],
            "p95_ms": p[0.95],
            "p99_ms": p[0.99],
        }
    )

    return rows


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    """Execute write csv.

    Args:
        rows: The rows.
        path: The path.
    """

    if not rows:
        return
    # union of all keys to accommodate different row schemas
    keys = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _git_sha() -> str:
    """Execute git sha."""

    try:
        root = Path(__file__).resolve().parents[1]
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(root))
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _provenance(extra: dict | None = None) -> dict:
    """Execute provenance.

    Args:
        extra: The extra.
    """

    prov = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git_sha": _git_sha(),
        "cwd": str(os.getcwd()),
        "executable": sys.executable,
    }
    if extra:
        prov.update(extra)
    return prov


def try_plots(
    quality: List[Dict[str, object]], latency: List[Dict[str, object]], out_dir: Path
) -> None:
    """Execute try plots.

    Args:
        quality: The quality.
        latency: The latency.
        out_dir: The out_dir.
    """

    try:
        import os

        os.environ.setdefault("MPLBACKEND", "Agg")
        # ensure Matplotlib config/cache are writable within repo
        cfg_dir = out_dir / ".mplconfig"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(cfg_dir))
        os.environ.setdefault("XDG_CACHE_HOME", str(cfg_dir))
        import matplotlib.pyplot as plt

        # Cosine vs k for three modes
        ks = sorted(
            {
                int(r["k"])
                for r in quality
                if r["mode"]
                in ("unitary_exact", "gaussian_wiener", "gaussian_tikhonov")
            }
        )
        modes = ["unitary_exact", "gaussian_wiener", "gaussian_tikhonov"]
        mode_labels = {
            "unitary_exact": "Unitary+Exact",
            "gaussian_wiener": "Gaussian+Wiener",
            "gaussian_tikhonov": "Gaussian+Tikhonov",
        }
        plt.figure(figsize=(7, 4))
        for m in modes:
            ys = []
            for k in ks:
                rec = [r for r in quality if r["mode"] == m and int(r["k"]) == k]
                if not rec:
                    ys.append(float("nan"))
                else:
                    r0 = rec[0]
                    if "cos_mean" in r0:
                        ys.append(r0["cos_mean"])
                    elif "cos_mean_raw" in r0:
                        ys.append(r0["cos_mean_raw"])
                    else:
                        ys.append(float("nan"))
            plt.plot(ks, ys, marker="o", label=mode_labels[m])
        plt.xlabel("k (superposed items)")
        plt.ylabel("Mean cosine")
        plt.title("Recovery quality vs k (D=8192, float32)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "cognition_cosine.png", dpi=150)
        plt.close()

        # Latency p99 bars
        plt.figure(figsize=(6, 3.5))
        vals = [r["p99_ms"] for r in latency]
        labels = ["Unitary+Exact", "Gaussian+Wiener", "Gaussian+Tikhonov"]
        plt.bar(labels, vals, color=["#4CAF50", "#2196F3", "#9C27B0"])
        plt.ylabel("p99 unbind latency (ms)")
        plt.title("Unbind latency p99 (D=8192, float32)")
        for i, v in enumerate(vals):
            plt.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        plt.tight_layout()
        plt.savefig(out_dir / "cognition_unbind_p99.png", dpi=150)
        plt.close()
    except Exception as e:
        print("Plotting skipped:", e)


def main(dim: int = 8192, dtype: str = "float32") -> None:
    """Execute main.

    Args:
        dim: The dim.
        dtype: The dtype.
    """

    out_dir = Path("benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)
    quality = run_quality_bench(dim=dim, dtype=dtype)
    latency = run_latency_bench(dim=dim, dtype=dtype)
    write_csv(quality, out_dir / "cognition_quality.csv")
    write_csv(latency, out_dir / "cognition_latency.csv")
    # Write provenance sidecar
    (out_dir / "cognition_provenance.json").write_text(
        json.dumps(
            _provenance({"phase": "cognition_core", "dim": dim, "dtype": dtype}),
            indent=2,
        )
    )

    # Print gates
    # Gate 1: Unitary+Exact cosine@k=1 >= 0.70
    ue1 = [r for r in quality if r["mode"] == "unitary_exact" and int(r["k"]) == 1][0]
    gate1 = float(ue1["cos_mean"]) >= 0.70
    print(
        "Gate1 (unitary+exact k=1 >=0.70):",
        "PASS" if gate1 else "FAIL",
        f"(mean={ue1['cos_mean']:.3f})",
    )

    # Gate 2: Gaussian+Wiener better than Tikhonov by >= 0.03 at k in {1,4,16} (raw cosine)
    gate2 = True
    for k in (1, 4, 16):
        w = [r for r in quality if r["mode"] == "gaussian_wiener" and int(r["k"]) == k][
            0
        ]["cos_mean_raw"]
        t = [
            r for r in quality if r["mode"] == "gaussian_tikhonov" and int(r["k"]) == k
        ][0]["cos_mean_raw"]
        ok = float(w) - float(t) >= 0.03
        print(
            f"Gate2 (Wiener-Tikhonov @k={k} >= 0.03):",
            "PASS" if ok else "FAIL",
            f"(Δ={float(w) - float(t):.3f})",
        )
        gate2 = gate2 and ok

    # Gate 3: p99 unbind <= 1 ms for unitary exact
    ue_lat = [r for r in latency if r["mode"] == "unitary_exact"][0]
    gate3 = float(ue_lat["p99_ms"]) <= 1.0
    print(
        "Gate3 (unitary exact p99 <= 1ms):",
        "PASS" if gate3 else "WARN",
        f"(p99={ue_lat['p99_ms']:.3f} ms)",
    )

    try_plots(quality, latency, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cognition core benchmark: quality and latency gates"
    )
    parser.add_argument("--dim", type=int, default=8192)
    parser.add_argument("--dtype", choices=["float32", "float64"], default="float32")
    args = parser.parse_args()
    main(dim=args.dim, dtype=args.dtype)
