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

from somabrain.quantum import HRRConfig, QuantumLayer


def run(
    out: Path, Ds=(256, 1024), ks=(1, 2, 4, 8, 16, 32, 64), trials=64, dtype="float32"
):
    results = {
        "meta": {"D": list(Ds), "ks": list(ks), "trials": int(trials), "dtype": dtype},
        "data": [],
    }
    for D in Ds:
        cfg = HRRConfig(dim=int(D), seed=42, dtype=dtype)
        q = QuantumLayer(cfg)
        for k in ks:
            cosines = []
            for _ in range(int(trials)):
                # Create k random items and a random role; superpose items and bind with role
                items = [q.random_vector() for _ in range(int(k))]
                role = q.random_vector()
                superposed = q.superpose(items)
                bound = q.bind(superposed, role)
                # Unbind and cleanup by selecting best cosine against items
                est = q.unbind(bound, role)
                best = max(
                    float(np.dot(est, it) / (np.linalg.norm(est) * np.linalg.norm(it)))
                    for it in items
                )
                cosines.append(best)
            entry = {
                "D": int(D),
                "k": int(k),
                "mean_cosine": float(np.mean(cosines)),
                "std_cosine": float(np.std(cosines)),
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
