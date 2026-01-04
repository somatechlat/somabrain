"""Colored-noise bench: generate colored (1/f) noise for the filler/channel and
measure reconstruction quality across exact/robust/wiener unbinds.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from somabrain.numerics import irfft_norm
from somabrain.quantum import HRRConfig, QuantumLayer


def make_colored_noise_spectrum(n_bins, exponent=1.0, seed=0):
    """Execute make colored noise spectrum.

    Args:
        n_bins: The n_bins.
        exponent: The exponent.
        seed: The seed.
    """

    rng = np.random.default_rng(seed)
    freqs = np.arange(1, n_bins + 1)
    power = 1.0 / (freqs**exponent)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins)
    spec = np.sqrt(power) * np.exp(1j * phases)
    return spec


def run_bench(
    out_path: Path, D_list=(512, 1024), exponents=(0.5, 1.0, 2.0), seeds=(0, 1, 2)
):
    """Execute run bench.

    Args:
        out_path: The out_path.
        D_list: The D_list.
        exponents: The exponents.
        seeds: The seeds.
    """

    results = {
        "meta": {
            "D_list": list(D_list),
            "exponents": list(exponents),
            "seeds": list(seeds),
        },
        "data": [],
    }
    for D in D_list:
        cfg = HRRConfig(dim=D)
        q = QuantumLayer(cfg)
        n_bins = D // 2 + 1
        for seed in seeds:
            a = q.random_vector()
            b = q.random_vector()
            for e in exponents:
                spec_noise = make_colored_noise_spectrum(n_bins, exponent=e, seed=seed)
                # create noise in time-domain
                noise = irfft_norm(spec_noise, n=D)
                b_noisy = q.bind(b, noise) if True else b + noise
                bound = q.bind(a, b_noisy)
                est_exact = q.unbind_exact(bound, b_noisy)
                est_robust = q.unbind(bound, b_noisy)
                est_wiener = q.unbind_wiener(bound, b_noisy)

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
                    "exponent": float(e),
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

    # Try to plot if matplotlib available
    try:
        import matplotlib.pyplot as plt

        for D in D_list:
            subset = [e for e in results["data"] if e["D"] == D]
            exps = sorted(set(e["exponent"] for e in subset))
            mean_exact = [
                np.mean([e["cosine_exact"] for e in subset if e["exponent"] == ex])
                for ex in exps
            ]
            mean_robust = [
                np.mean([e["cosine_robust"] for e in subset if e["exponent"] == ex])
                for ex in exps
            ]
            mean_wiener = [
                np.mean([e["cosine_wiener"] for e in subset if e["exponent"] == ex])
                for ex in exps
            ]

            plt.figure()
            plt.plot(exps, mean_exact, marker="o", label="exact")
            plt.plot(exps, mean_robust, marker="o", label="robust")
            plt.plot(exps, mean_wiener, marker="o", label="wiener")
            plt.xlabel("spectral exponent")
            plt.ylabel("mean cosine")
            plt.title(f"Colored-noise bench D={D}")
            plt.legend()
            out_png = out_path.parent / f"colored_noise_D{D}.png"
            plt.savefig(out_png, dpi=150)
            plt.close()
    except Exception:
        pass


def main():
    """Execute main."""

    p = argparse.ArgumentParser()
    p.add_argument(
        "--out", type=Path, default=Path("benchmarks/colored_noise_results.json")
    )
    args = p.parse_args()
    run_bench(args.out)


if __name__ == "__main__":
    main()
