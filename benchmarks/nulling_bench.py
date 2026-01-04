"""Nulling bench: zero a fraction of frequency bins in role vector and measure
reconstruction quality for exact, robust, and wiener unbinds.

Produces JSON results and a PNG plot (if matplotlib is available).
"""

import argparse
import json
from pathlib import Path

import numpy as np

from somabrain.math import cosine_similarity
from somabrain.numerics import irfft_norm, rfft_norm
from somabrain.quantum import HRRConfig, QuantumLayer


def run_bench(
    out_path: Path,
    D_list=(512, 1024),
    null_fracs=(0.0, 0.1, 0.2, 0.3, 0.5),
    seeds=(0, 1, 2),
):
    """Execute run bench.

        Args:
            out_path: The out_path.
            D_list: The D_list.
            null_fracs: The null_fracs.
            seeds: The seeds.
        """

    results = {
        "meta": {
            "D_list": list(D_list),
            "null_fracs": list(null_fracs),
            "seeds": list(seeds),
        },
        "data": [],
    }
    for D in D_list:
        cfg = HRRConfig(dim=D)
        q = QuantumLayer(cfg)
        # n_bins not required directly here (kept for clarity originally)
        for seed in seeds:
            rng = np.random.default_rng(seed)
            a = q.random_vector()
            b = q.random_vector()
            fb_orig = rfft_norm(b, n=D)
            for nf in null_fracs:
                fb = fb_orig.copy()
                n_null = int(nf * fb.shape[-1])
                if n_null > 0:
                    idx = rng.choice(fb.shape[-1], size=n_null, replace=False)
                    fb[idx] = 0.0
                b_null = irfft_norm(fb, n=D)
                bound = q.bind(a, b_null)
                est_exact = q.unbind_exact(bound, b_null)
                est_robust = q.unbind(bound, b_null)
                est_wiener = q.unbind_wiener(bound, b_null)

                def mse(x, y):
                    """Execute mse.

                        Args:
                            x: The x.
                            y: The y.
                        """

                    return float(np.mean((x - y) ** 2))

                entry = {
                    "D": int(D),
                    "seed": int(seed),
                    "null_frac": float(nf),
                    "cosine_exact": cosine_similarity(a, est_exact),
                    "cosine_robust": cosine_similarity(a, est_robust),
                    "cosine_wiener": cosine_similarity(a, est_wiener),
                    "mse_exact": mse(a, est_exact),
                    "mse_robust": mse(a, est_robust),
                    "mse_wiener": mse(a, est_wiener),
                }
                results["data"].append(entry)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))

    # Try to plot if matplotlib is available
    try:
        import matplotlib.pyplot as plt

        # aggregate mean cosine per null_frac and method for each D
        for D in D_list:
            subset = [e for e in results["data"] if e["D"] == D]
            nulls = sorted(set(e["null_frac"] for e in subset))
            mean_exact = [
                np.mean([e["cosine_exact"] for e in subset if e["null_frac"] == nf])
                for nf in nulls
            ]
            mean_robust = [
                np.mean([e["cosine_robust"] for e in subset if e["null_frac"] == nf])
                for nf in nulls
            ]
            mean_wiener = [
                np.mean([e["cosine_wiener"] for e in subset if e["null_frac"] == nf])
                for nf in nulls
            ]

            plt.figure()
            plt.plot(nulls, mean_exact, marker="o", label="exact")
            plt.plot(nulls, mean_robust, marker="o", label="robust")
            plt.plot(nulls, mean_wiener, marker="o", label="wiener")
            plt.xlabel("null fraction")
            plt.ylabel("mean cosine")
            plt.title(f"Nulling bench D={D}")
            plt.legend()
            out_png = out_path.parent / f"nulling_D{D}.png"
            plt.savefig(out_png, dpi=150)
            plt.close()
    except Exception:
        pass


def main():
    """Execute main.
        """

    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("benchmarks/nulling_results.json"))
    args = p.parse_args()
    run_bench(args.out)


if __name__ == "__main__":
    main()