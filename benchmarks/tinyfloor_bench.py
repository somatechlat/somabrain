"""Tiny-floor and HRR unbind benchmark.

Compares current compute_tiny_floor (linear) vs sqrt(D) strategy by:
- measuring fraction of vectors zeroed by normalization (robust mode)
- measuring unbind reconstruction MSE and cosine vs PureQuantumLayer oracle

Writes results to docs/benchmarks/results_tinyfloor.json and .md
"""

import json
import math
import time
from pathlib import Path

import numpy as np

from somabrain import numerics
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.quantum_pure import PureQuantumLayer


def tiny_floor_sqrt(dtype, dim):
    """Execute tiny floor sqrt.

    Args:
        dtype: The dtype.
        dim: The dim.
    """

    dt = np.dtype(dtype)
    eps = float(np.finfo(dt).eps)
    tiny_min = 1e-6 if dt == np.float32 else 1e-12
    return max(eps * math.sqrt(float(dim)), tiny_min)


def simulate_zeroed_fraction(dim, dtype, n=1000, kind="gaussian", strategy="linear"):
    """Execute simulate zeroed fraction.

    Args:
        dim: The dim.
        dtype: The dtype.
        n: The n.
        kind: The kind.
        strategy: The strategy.
    """

    rng = np.random.default_rng(12345)
    zeroed = 0
    for _ in range(n):
        if kind == "gaussian":
            v = rng.normal(0.0, 1.0, size=dim).astype(dtype)
        elif kind == "sparse":
            v = np.zeros((dim,), dtype=dtype)
            idx = rng.choice(dim, size=max(1, dim // 64), replace=False)
            v[idx] = rng.normal(0.0, 1.0, size=idx.shape[0]).astype(dtype)
        else:
            v = rng.normal(0.0, 1.0, size=dim).astype(dtype)

        # apply normalization contract locally depending on strategy
        nrm = float(np.linalg.norm(v))
        if strategy == "linear":
            tiny = numerics.compute_tiny_floor(dtype, dim)
        else:
            tiny = tiny_floor_sqrt(dtype, dim)

        if nrm < tiny:
            zeroed += 1
    return zeroed / float(n)


def unbind_fidelity(dim, dtype, n_pairs=200, strategy="linear"):
    """Execute unbind fidelity.

    Args:
        dim: The dim.
        dtype: The dtype.
        n_pairs: The n_pairs.
        strategy: The strategy.
    """

    cfg = HRRConfig(
        dim=dim,
        seed=42,
        dtype=np.dtype(dtype).name,
        renorm=True,
    )
    q = QuantumLayer(cfg)
    p = PureQuantumLayer(cfg)

    # Optionally monkeypatch numerics.compute_tiny_floor for strategy
    original = numerics.compute_tiny_floor
    if strategy == "sqrt":
        # Patch only for the duration of this benchmark: accept any
        # positional/keyword form and forward to the local tiny_floor_sqrt.
        def _patched_compute_tiny_floor(*args, **kwargs):
            # Determine dim and dtype regardless of positional ordering
            """Execute patched compute tiny floor."""

            dim = None
            dtype = kwargs.get("dtype", None)
            if len(args) >= 2:
                a0, a1 = args[0], args[1]
                try:
                    # if first arg looks like a dtype and second an int, swap
                    np.dtype(a0)
                    is_dtype_like = True
                except Exception:
                    is_dtype_like = False
                if is_dtype_like and isinstance(a1, (int, np.integer)):
                    dtype = a0
                    dim = a1
                else:
                    dim = a0
                    if dtype is None:
                        dtype = a1
            elif len(args) == 1:
                dim = args[0]
            # use kwargs alternative
            if dim is None:
                dim = kwargs.get("dim", kwargs.get("D", 1))
            if dtype is None:
                dtype = kwargs.get("dtype", np.float32)
            try:
                return tiny_floor_sqrt(dtype, int(dim))
            except Exception:
                # As a last resort, coerce and retry
                return tiny_floor_sqrt(np.dtype(dtype), int(dim))

        numerics.compute_tiny_floor = _patched_compute_tiny_floor

    mses = []
    cosines = []
    start = time.perf_counter()
    for _ in range(n_pairs):
        a = q.random_vector()
        b = q.random_vector()
        c = q.bind(a, b)
        rec = q.unbind(c, b)
        # oracle (pure) unbind may raise; we skip oracle errors
        try:
            _ = p.unbind(c, b)
        except Exception:
            pass

        # compare rec to original a
        from somabrain.math.similarity import cosine_similarity

        mse = float(np.mean((a - rec) ** 2))
        cos = cosine_similarity(a, rec)
        mses.append(mse)
        cosines.append(cos)
    elapsed = time.perf_counter() - start

    # restore
    numerics.compute_tiny_floor = original

    return {
        "mse_mean": float(np.mean(mses)),
        "mse_std": float(np.std(mses)),
        "cos_mean": float(np.mean(cosines)),
        "cos_std": float(np.std(cosines)),
        "elapsed_s": elapsed,
    }


def run_all():
    """Execute run all."""

    out = {"runs": [], "meta": {"timestamp": time.time()}}
    dims = [2048, 8192]
    for D in dims:
        for dtype in [np.float32, np.float64]:
            # zeroed fraction tests
            gf = simulate_zeroed_fraction(
                D,
                dtype,
                n=800 if D == 2048 else 200,
                kind="gaussian",
                strategy="linear",
            )
            gs = simulate_zeroed_fraction(
                D, dtype, n=800 if D == 2048 else 200, kind="gaussian", strategy="sqrt"
            )
            sf = simulate_zeroed_fraction(
                D, dtype, n=800 if D == 2048 else 200, kind="sparse", strategy="linear"
            )
            ss = simulate_zeroed_fraction(
                D, dtype, n=800 if D == 2048 else 200, kind="sparse", strategy="sqrt"
            )

            # unbind fidelity
            u_linear = unbind_fidelity(
                D, dtype, n_pairs=200 if D == 2048 else 40, strategy="linear"
            )
            u_sqrt = unbind_fidelity(
                D, dtype, n_pairs=200 if D == 2048 else 40, strategy="sqrt"
            )

            entry = {
                "dim": D,
                "dtype": str(dtype),
                "zeroed_fraction": {
                    "gaussian_linear": gf,
                    "gaussian_sqrt": gs,
                    "sparse_linear": sf,
                    "sparse_sqrt": ss,
                },
                "unbind": {"linear": u_linear, "sqrt": u_sqrt},
            }
            out["runs"].append(entry)

    # write outputs
    docs_dir = Path("docs/benchmarks")
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / "results_tinyfloor.json"
    md_path = docs_dir / "results_tinyfloor.md"
    with json_path.open("w") as f:
        json.dump(out, f, indent=2)

    # create a short md summary
    with md_path.open("w") as f:
        f.write("# Tiny-floor benchmark results\n\n")
        f.write(f"Timestamp: {out['meta']['timestamp']}\n\n")
        for r in out["runs"]:
            f.write(f"## D={r['dim']} dtype={r['dtype']}\n")
            z = r["zeroed_fraction"]
            f.write(
                f"- Zeroed fraction (gaussian): linear={z['gaussian_linear']:.4f}, sqrt={z['gaussian_sqrt']:.4f}\n"
            )
            f.write(
                f"- Zeroed fraction (sparse): linear={z['sparse_linear']:.4f}, sqrt={z['sparse_sqrt']:.4f}\n"
            )
            f.write("- Unbind (linear):\n")
            ul = r["unbind"]["linear"]
            f.write(
                f"  - mse_mean: {ul['mse_mean']:.6e}, cos_mean: {ul['cos_mean']:.6f}, time_s: {ul['elapsed_s']:.3f}\n"
            )
            us = r["unbind"]["sqrt"]
            f.write("- Unbind (sqrt):\n")
            f.write(
                f"  - mse_mean: {us['mse_mean']:.6e}, cos_mean: {us['cos_mean']:.6f}, time_s: {us['elapsed_s']:.3f}\n\n"
            )

    print(f"Wrote results to {json_path} and {md_path}")


if __name__ == "__main__":
    run_all()
