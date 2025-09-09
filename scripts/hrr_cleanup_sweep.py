"""
Cleanup-based recall sweep: test retrieval accuracy when superposing k bound key/value pairs,
using nearest-neighbor cleanup against the true value anchors.
Run with project venv python.
"""

import csv
from statistics import mean

from somabrain.quantum import HRRConfig, QuantumLayer

OUT = "hrr_cleanup_results.csv"


def run_sweep(dim=2048, dtypes=None, eps_values=None, k_values=None, trials=200):
    if dtypes is None:
        dtypes = ["float32", "float64"]
    if eps_values is None:
        eps_values = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]
    if k_values is None:
        k_values = list(range(2, 9))  # 2..8
    rows = []
    for dtype in dtypes:
        cfg = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True)
        layer = QuantumLayer(cfg)
        for eps in eps_values:
            cfg.fft_eps = eps
            for k in k_values:
                successes = 0
                scores = []
                for t in range(trials):
                    # build k key/value pairs
                    keys = [layer.encode_text(f"k_{t}_{i}") for i in range(k)]
                    vals = [layer.encode_text(f"v_{t}_{i}") for i in range(k)]
                    binds = [layer.bind(keys[i], vals[i]) for i in range(k)]
                    memory = layer.superpose(*binds)
                    # anchors for cleanup
                    anchors = {f"v_{i}": vals[i] for i in range(k)}
                    # try to recall each value by unbinding with its key and cleaning up
                    for i in range(k):
                        rec = layer.unbind(memory, keys[i])
                        best_id, best_score = layer.cleanup(rec, anchors)
                        scores.append(best_score)
                        if best_id == f"v_{i}":
                            successes += 1
                total = trials * k
                recall = successes / total
                avg_score = mean(scores) if scores else 0.0
                rows.append(
                    {
                        "dim": dim,
                        "dtype": dtype,
                        "eps": eps,
                        "k": k,
                        "recall": recall,
                        "avg_score": avg_score,
                    }
                )
                print(
                    f"dtype={dtype} eps={eps:.1e} k={k} recall={recall:.3f} avg_score={avg_score:.3f}"
                )
    # write CSV
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("\nWrote results to", OUT)


if __name__ == "__main__":
    run_sweep(trials=200)
