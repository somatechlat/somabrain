"""
Capacity Curves Benchmark
-------------------------

Measures recall cosine vs number of superposed items (k) for different D and dtypes.
Outputs JSON with mean cosine for each (D, dtype, k) and saves plots.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from somabrain.math.similarity import cosine_similarity
from somabrain.apps.core.quantum import HRRConfig, QuantumLayer


def run(
    out: Path,
    Ds=(256, 1024),
    ks=(1, 2, 4, 8, 16, 32, 64),
    trials=64,
    dtype="float32",
    accuracy_thresholds=(0.7, 0.8, 0.9),
):
    """Execute run.

    Args:
        out: The out.
        Ds: The Ds.
        ks: The ks.
        trials: The trials.
        dtype: The dtype.
        accuracy_thresholds: The accuracy_thresholds.
    """

    results = {
        "meta": {
            "D": list(Ds),
            "ks": list(ks),
            "trials": int(trials),
            "dtype": dtype,
            "accuracy_thresholds": [float(t) for t in accuracy_thresholds],
        },
        "data": [],
    }
    for D in Ds:
        cfg = HRRConfig(dim=int(D), seed=42, dtype=dtype)
        q = QuantumLayer(cfg)
        for k in ks:
            cosines = []
            margins = []
            for _ in range(int(trials)):
                # Create k random items and a random role; superpose items and bind with role
                items = [q.random_vector() for _ in range(int(k))]
                role = q.random_vector()
                superposed = q.superpose(items)
                bound = q.bind(superposed, role)
                # Unbind and cleanup by selecting best cosine against items
                est = q.unbind(bound, role)
                scores = [cosine_similarity(est, it) for it in items]
                scores.sort(reverse=True)
                best = scores[0]
                second = scores[1] if len(scores) > 1 else best
                cosines.append(best)
                margins.append(max(0.0, best - second))
            accuracy = {
                f"{thr:.2f}": float(np.mean([c >= thr for c in cosines]))
                for thr in accuracy_thresholds
            }
            entry = {
                "D": int(D),
                "k": int(k),
                "mean_cosine": float(np.mean(cosines)),
                "std_cosine": float(np.std(cosines)),
                "median_margin": float(np.median(margins)) if margins else 0.0,
                "accuracy": accuracy,
            }
            results["data"].append(entry)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    # Optional plotting
    try:
        import matplotlib.pyplot as plt

        for D in Ds:
            xs = [int(k) for k in ks]
            ys = [e["mean_cosine"] for e in results["data"] if e["D"] == int(D)]
            plt.figure()
            plt.plot(xs, ys, marker="o")
            plt.xlabel("k (superposed items)")
            plt.ylabel("mean cosine (best item)")
            plt.title(f"Capacity curve D={D}")
            plt.grid(True)
            plot_dir = Path("benchmarks/plots")
            plot_dir.mkdir(parents=True, exist_ok=True)
            plt.savefig(plot_dir / f"capacity_D{D}.png", dpi=150)
            plt.close()
    except Exception:
        pass


if __name__ == "__main__":
    run(Path("benchmarks/capacity_curves.json"))
