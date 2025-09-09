"""
Superposition sweep: test recall quality when superposing k bound key/value pairs.
Run with project venv python.
"""

import csv
from statistics import mean, median

from somabrain.quantum import HRRConfig, QuantumLayer

OUT = "hrr_superpose_results.csv"


def run_sweep(dim=2048, dtypes=None, eps_values=None, k_values=None, trials=200):
    if dtypes is None:
        dtypes = ["float32", "float64"]
    if eps_values is None:
        eps_values = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]
    if k_values is None:
        k_values = list(range(2, 9))  # 2..8
    rows = []
    for dtype in dtypes:
        cfg = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True, fft_eps=None)
        layer = QuantumLayer(cfg)
        for eps in eps_values:
            cfg.fft_eps = eps
            for k in k_values:
                cosines = []
                for t in range(trials):
                    # build k key/value pairs
                    keys = [layer.encode_text(f"k_{t}_{i}") for i in range(k)]
                    vals = [layer.encode_text(f"v_{t}_{i}") for i in range(k)]
                    binds = [layer.bind(keys[i], vals[i]) for i in range(k)]
                    memory = layer.superpose(*binds)
                    # try to recall each value by unbinding with its key
                    for i in range(k):
                        rec = layer.unbind(memory, keys[i])
                        cos = layer.cosine(rec, vals[i])
                        cosines.append(float(cos))
                # compute statistics over all recalls
                cosines.sort()
                mu = mean(cosines)
                med = median(cosines)
                p5 = cosines[max(0, int(0.05 * len(cosines)) - 1)]
                p25 = cosines[max(0, int(0.25 * len(cosines)) - 1)]
                p75 = cosines[min(len(cosines) - 1, int(0.75 * len(cosines)))]
                p95 = cosines[min(len(cosines) - 1, int(0.95 * len(cosines)))]
                fail_rate = sum(1 for c in cosines if c < 0.75) / len(cosines)
                rows.append(
                    {
                        "dim": dim,
                        "dtype": dtype,
                        "eps": eps,
                        "k": k,
                        "mean": mu,
                        "median": med,
                        "p5": p5,
                        "p25": p25,
                        "p75": p75,
                        "p95": p95,
                        "fail_rate": fail_rate,
                    }
                )
                print(
                    f"dtype={dtype} eps={eps:.1e} k={k} med={med:.4f} fail_rate={fail_rate:.3f}"
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
