"""
Run randomized HRR bind/unbind recovery sweeps and emit CSV results.
Run with the project's venv python.
"""

import csv
from statistics import mean, median

from somabrain.quantum import HRRConfig, QuantumLayer

OUT = "hrr_sweep_results.csv"


def run_sweep(dims, dtypes, eps_values, trials=200):
    rows = []
    for dim in dims:
        for dtype in dtypes:
            cfg = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True, fft_eps=None)
            layer = QuantumLayer(cfg)
            for eps in eps_values:
                cfg.fft_eps = eps
                cosines = []
                for t in range(trials):
                    # deterministic per trial
                    x = layer.encode_text(f"x_{t}")
                    y = layer.encode_text(f"y_{t}")
                    a = layer.bind(x, y)
                    x_rec = layer.unbind(a, y)
                    cos = layer.cosine(x, x_rec)
                    cosines.append(float(cos))
                cosines.sort()
                mu = mean(cosines)
                med = median(cosines)
                p5 = cosines[max(0, int(0.05 * len(cosines)) - 1)]
                p25 = cosines[max(0, int(0.25 * len(cosines)) - 1)]
                p75 = cosines[min(len(cosines) - 1, int(0.75 * len(cosines)))]
                p95 = cosines[min(len(cosines) - 1, int(0.95 * len(cosines)))]
                fail_rate = sum(1 for c in cosines if c < 0.9) / len(cosines)
                rows.append(
                    {
                        "dim": dim,
                        "dtype": dtype,
                        "eps": eps,
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
                    f"dim={dim} dtype={dtype} eps={eps:.1e} med={med:.4f} fail_rate={fail_rate:.3f}"
                )
    # write CSV
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("\nWrote results to", OUT)


if __name__ == "__main__":
    dims = [2048]
    dtypes = ["float32", "float64"]
    eps_values = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]
    trials = 300
    run_sweep(dims, dtypes, eps_values, trials=trials)
