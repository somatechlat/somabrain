"""Module diffusion_predictor_bench."""

from __future__ import annotations
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm

# Try to import matplotlib for plotting; optional.
try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    raise SystemExit(
        "matplotlib is required to run this benchmark. Install it and retry."
    )

from somabrain.predictors.base import (
    HeatDiffusionPredictor,
    PredictorConfig,
    make_line_graph_laplacian,
    matvec_from_matrix,
)

# Benchmark diffusion-backed predictors (Chebyshev/Lanczos) for accuracy and performance.
#
# Artifacts are written under:
# - benchmarks/results/diffusion_predictors/<timestamp>/
# - benchmarks/plots/diffusion_predictors/<timestamp>/
#
# Run:
#   python benchmarks/diffusion_predictor_bench.py


try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    raise SystemExit(
        "matplotlib is required to run this benchmark. Install it and retry."
    )


@dataclass
class TrialResult:
    """Trialresult class implementation."""

    method: str
    n: int
    t: float
    K: int
    m: int
    mse: float
    runtime_ms: float


def _now_tag() -> str:
    """Execute now tag.
        """

    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _ensure_dirs(ts: str) -> Tuple[Path, Path]:
    """Execute ensure dirs.

        Args:
            ts: The ts.
        """

    base = Path("benchmarks")
    res = base / "results" / "diffusion_predictors" / ts
    plots = base / "plots" / "diffusion_predictors" / ts
    res.mkdir(parents=True, exist_ok=True)
    plots.mkdir(parents=True, exist_ok=True)
    return res, plots


def _predict(
    method: str, L: NDArray[np.float_], x0: NDArray[np.float_], t: float, K: int, m: int
) -> Tuple[NDArray[np.float_], float]:
    """Execute predict.

        Args:
            method: The method.
            L: The L.
            x0: The x0.
            t: The t.
            K: The K.
            m: The m.
        """

    n = L.shape[0]
    cfg = PredictorConfig(diffusion_t=t, chebyshev_K=K, lanczos_m=m)
    pred = HeatDiffusionPredictor(apply_A=matvec_from_matrix(L), dim=n, cfg=cfg)
    # monkey-patch method selection via env var
    os.environ["SOMA_HEAT_METHOD"] = method
    t0 = time.perf_counter()
    y = pred.salience(x0)
    dt = (time.perf_counter() - t0) * 1000.0
    return y, dt


def _exact(
    L: NDArray[np.float_], x0: NDArray[np.float_], t: float
) -> NDArray[np.float_]:
    """Execute exact.

        Args:
            L: The L.
            x0: The x0.
            t: The t.
        """

    return expm(-t * L) @ x0


def accuracy_sweep(res_dir: Path, plots_dir: Path) -> Dict[str, List[TrialResult]]:
    """Execute accuracy sweep.

        Args:
            res_dir: The res_dir.
            plots_dir: The plots_dir.
        """

    methods = ["chebyshev", "lanczos"]
    ns = [16, 32]
    ts = [0.1, 0.3, 1.0]
    cheb_Ks = [10, 20, 40, 80]
    lanc_m = [10, 20, 40]
    results: Dict[str, List[TrialResult]] = {"chebyshev": [], "lanczos": []}
    for n in ns:
        L = make_line_graph_laplacian(n)
        for t in ts:
            x0 = np.zeros(n, dtype=float)
            x0[0] = 1.0
            y_exact = _exact(L, x0, t)
            # Chebyshev sweep
            for K in cheb_Ks:
                y, rt = _predict("chebyshev", L, x0, t, K=K, m=20)
                mse = float(np.mean((y - y_exact) ** 2))
                results["chebyshev"].append(
                    TrialResult("chebyshev", n, t, K, 20, mse, rt)
                )
            # Lanczos sweep
            for m in lanc_m:
                y, rt = _predict("lanczos", L, x0, t, K=40, m=m)
                mse = float(np.mean((y - y_exact) ** 2))
                results["lanczos"].append(TrialResult("lanczos", n, t, 40, m, mse, rt))
    # Persist JSON
    with open(res_dir / "accuracy_sweep.json", "w") as f:
        json.dump({k: [asdict(r) for r in v] for k, v in results.items()}, f, indent=2)
    # Plot error vs K/m for n=32, t=0.3
    for method in methods:
        subset = [r for r in results[method] if r.n == 32 and abs(r.t - 0.3) < 1e-9]
        if not subset:
            continue
        plt.figure()
        if method == "chebyshev":
            xs = [r.K for r in subset]
            ys = [r.mse for r in subset]
            plt.plot(xs, ys, marker="o")
            plt.xlabel("Chebyshev K")
        else:
            xs = [r.m for r in subset]
            ys = [r.mse for r in subset]
            plt.plot(xs, ys, marker="o")
            plt.xlabel("Lanczos m")
        plt.ylabel("MSE vs exact expm")
        plt.title(f"Accuracy sweep ({method}) n=32, t=0.3")
        plt.grid(True)
        outp = plots_dir / f"accuracy_{method}_n32_t0.3.png"
        plt.savefig(outp, dpi=140, bbox_inches="tight")
    return results


def runtime_sweep(res_dir: Path, plots_dir: Path) -> List[TrialResult]:
    """Execute runtime sweep.

        Args:
            res_dir: The res_dir.
            plots_dir: The plots_dir.
        """

    ns = [16, 32, 64, 128]
    t = 0.3
    cfgs = [("chebyshev", 40, 20), ("lanczos", 40, 20)]
    results: List[TrialResult] = []
    for n in ns:
        L = make_line_graph_laplacian(n)
        x0 = np.zeros(n, dtype=float)
        x0[n // 2] = 1.0
        for method, K, m in cfgs:
            y, rt = _predict(method, L, x0, t, K=K, m=m)
            # Skip exact for large n to keep it fast; record mse=nan
            mse = float("nan")
            if n <= 64:
                y_exact = _exact(L, x0, t)
                mse = float(np.mean((y - y_exact) ** 2))
            results.append(TrialResult(method, n, t, K, m, mse, rt))
    with open(res_dir / "runtime_sweep.json", "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    # Plot runtime vs n
    plt.figure()
    for method in ("chebyshev", "lanczos"):
        xs = [r.n for r in results if r.method == method]
        ys = [r.runtime_ms for r in results if r.method == method]
        plt.plot(xs, ys, marker="o", label=method)
    plt.xlabel("n (graph size)")
    plt.ylabel("runtime (ms)")
    plt.title("Runtime vs n (t=0.3; K=40; m=20)")
    plt.legend()
    plt.grid(True)
    outp = plots_dir / "runtime_vs_n.png"
    plt.savefig(outp, dpi=140, bbox_inches="tight")
    return results


def example_heatmap(res_dir: Path, plots_dir: Path) -> None:
    """Execute example heatmap.

        Args:
            res_dir: The res_dir.
            plots_dir: The plots_dir.
        """

    n = 32
    t = 0.3
    L = make_line_graph_laplacian(n)
    x0 = np.zeros(n, dtype=float)
    x0[n // 4] = 1.0
    y_cheb, _ = _predict("chebyshev", L, x0, t, K=40, m=20)
    y_lanc, _ = _predict("lanczos", L, x0, t, K=40, m=20)
    y_exact = _exact(L, x0, t)
    # Stack and plot
    M = np.vstack([y_exact, y_cheb, y_lanc])
    plt.figure(figsize=(6, 3))
    plt.imshow(M, aspect="auto", cmap="viridis")
    plt.yticks([0, 1, 2], ["exact", "chebyshev", "lanczos"])
    plt.colorbar(label="salience")
    plt.title("Salience snapshot (n=32, t=0.3)")
    outp = plots_dir / "salience_heatmap.png"
    plt.savefig(outp, dpi=140, bbox_inches="tight")


def main() -> None:
    """Execute main.
        """

    ts = _now_tag()
    res_dir, plots_dir = _ensure_dirs(ts)
    # Write a pointer to latest
    latest_txt = res_dir.parent / "latest.txt"
    latest_txt.write_text(ts + "\n")
    print(f"Writing results to {res_dir}")
    print(f"Writing plots to   {plots_dir}")
    accuracy_sweep(res_dir, plots_dir)
    runtime_sweep(res_dir, plots_dir)
    example_heatmap(res_dir, plots_dir)
    print("Benchmark complete.")


if __name__ == "__main__":
    main()