"""Plot benchmark artifacts produced by the evaluation scripts.

Usage:
  python benchmarks/plot_benchmarks.py

This looks for latest `learning_speed_*.json` and `retrieval_precision_*.json` in
`artifacts/benchmarks/` and writes `learning_curve.png` and `precision_hist.png`.
"""

import glob
import json
import os

try:
    import matplotlib.pyplot as plt
except Exception:
    raise SystemExit("matplotlib is required to run this script. Install it and retry.")


def latest(path_pattern):
    paths = sorted(glob.glob(path_pattern))
    return paths[-1] if paths else None


def plot_learning_curve():
    path = latest("artifacts/benchmarks/learning_speed_*.json")
    if not path:
        print("No learning_speed artifact found.")
        return
    with open(path) as f:
        j = json.load(f)
    xs = [r["n"] for r in j["results"]]
    ys = [r["precision_at_1"] for r in j["results"]]
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xscale("log")
    plt.xlabel("# training items (log scale)")
    plt.ylabel("Precision@1")
    plt.title("Learning curve: Precision@1 vs #items")
    out = "artifacts/benchmarks/learning_curve.png"
    plt.grid(True)
    plt.savefig(out)
    print(f"Wrote {out}")


def plot_precision_hist():
    path = latest("artifacts/benchmarks/retrieval_precision_*.json")
    if not path:
        print("No retrieval_precision artifact found.")
        return
    with open(path) as f:
        j = json.load(f)
    vals = [
        r.get("precision@k", 0.0) for r in j.get("results", []) if isinstance(r, dict)
    ]
    if not vals:
        print("No precision values found in artifact.")
        return
    plt.figure()
    plt.hist(vals, bins=20)
    plt.xlabel("precision@5")
    plt.ylabel("count")
    plt.title("Distribution of precision@5 across queries")
    out = "artifacts/benchmarks/precision_hist.png"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    os.makedirs("artifacts/benchmarks", exist_ok=True)
    plot_learning_curve()
    plot_precision_hist()
