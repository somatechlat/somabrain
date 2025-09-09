"""Pairwise HRR sweep: compare robust runtime vs pure-reference implementations.

Writes a CSV `hrr_paired_results.csv` containing rows for each dim/dtype/eps/mode
with recovery statistics. This is a test-only driver to quantify where pure
algebra succeeds/fails compared to the production, robust implementation.
"""

import csv
from statistics import mean, median

from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.quantum_pure import PureQuantumLayer

OUT = "hrr_paired_results.csv"


def run_paired(dims, dtypes, eps_values, trials=200):
    rows = []
    for dim in dims:
        for dtype in dtypes:
            # robust config
            cfg_r = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True, fft_eps=None)
            q_robust = QuantumLayer(cfg_r)
            # pure config (same contract)
            cfg_p = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True, fft_eps=None)
            q_pure = PureQuantumLayer(cfg_p)

            for eps in eps_values:
                # set eps for robust only; pure ignores it
                cfg_r.fft_eps = eps
                for mode, layer in (("robust", q_robust), ("pure", q_pure)):
                    cosines = []
                    fails = 0
                    for t in range(trials):
                        x = layer.encode_text(f"x_{t}")
                        y = layer.encode_text(f"y_{t}")
                        try:
                            a = layer.bind(x, y)
                            x_rec = layer.unbind(a, y)
                            cos = layer.cosine(x, x_rec)
                            cosines.append(float(cos))
                        except Exception:
                            # record failure as a cosine of -1.0 and keep going
                            fails += 1
                            cosines.append(-1.0)
                    cosines.sort()
                    mu = mean(cosines)
                    med = median(cosines)
                    p5 = cosines[max(0, int(0.05 * len(cosines)) - 1)]
                    p95 = cosines[min(len(cosines) - 1, int(0.95 * len(cosines)))]
                    fail_rate = fails / len(cosines)
                    rows.append(
                        {
                            "dim": dim,
                            "dtype": dtype,
                            "eps": eps,
                            "mode": mode,
                            "mean": mu,
                            "median": med,
                            "p5": p5,
                            "p95": p95,
                            "fail_rate": fail_rate,
                        }
                    )
                    print(f"dim={dim} dtype={dtype} eps={eps:.1e} mode={mode} med={med:.4f} fail_rate={fail_rate:.3f}")

    # write CSV
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("Wrote results to", OUT)


if __name__ == "__main__":
    dims = [2048]
    dtypes = ["float32", "float64"]
    eps_values = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4]
    trials = 200
    run_paired(dims, dtypes, eps_values, trials=trials)
