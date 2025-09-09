"""Long-run paired HRR sweep: compare runtime (robust) QuantumLayer vs pure test reference.

This script performs a longer-run experiment (more trials, include D=8192) and
writes CSV `hrr_paired_long_results.csv` for later analysis.
"""

import csv
from statistics import mean, median

from somabrain.quantum import HRRConfig, QuantumLayer
from tests.pure_hrr_reference import PureLayer

OUT = "hrr_paired_long_results.csv"


def run_paired_long(dims, dtypes, eps_values, trials=300):
    rows = []
    for dim in dims:
        for dtype in dtypes:
            cfg = HRRConfig(dim=dim, dtype=dtype, seed=123, renorm=True, fft_eps=None)
            qlayer = QuantumLayer(cfg)
            player = PureLayer(cfg)
            for eps in eps_values:
                cfg.fft_eps = eps
                for mode, layer in [("robust", qlayer), ("pure", player)]:
                    cosines = []
                    for t in range(trials):
                        x = layer.encode_text(f"x_{t}")
                        y = layer.encode_text(f"y_{t}")
                        a = layer.bind(x, y)
                        try:
                            x_rec = layer.unbind(a, y)
                            # use cosine if available
                            cos = (
                                layer.cosine(x, x_rec)
                                if hasattr(layer, "cosine")
                                else float((x * x_rec).sum())
                            )
                        except Exception:
                            cos = float("nan")
                        cosines.append(cos)
                    filtered = [c for c in cosines if c == c]
                    mu = mean(filtered) if filtered else float("nan")
                    med = median(filtered) if filtered else float("nan")
                    fail_rate = sum(
                        1 for c in cosines if not (c == c) or c < 0.9
                    ) / len(cosines)
                    rows.append(
                        {
                            "dim": dim,
                            "dtype": dtype,
                            "eps": eps,
                            "mode": mode,
                            "mean": mu,
                            "median": med,
                            "fail_rate": fail_rate,
                        }
                    )
                    print(
                        f"dim={dim} dtype={dtype} eps={eps:.1e} mode={mode} med={med:.6f} fail_rate={fail_rate:.3f}"
                    )
    # write CSV
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print("Wrote paired long results to", OUT)


if __name__ == "__main__":
    dims = [2048, 8192]
    dtypes = ["float32", "float64"]
    eps_values = [1e-12, 1e-10, 1e-8, 1e-6, 1e-4]
    run_paired_long(dims, dtypes, eps_values, trials=300)
