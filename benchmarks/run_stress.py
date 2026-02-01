"""Run a focused stress benchmark and write results to benchmarks/results_stress.json.

This runner is safe to execute from the repo root with the project venv.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from somabrain.math import cosine_similarity

OUT = Path(__file__).resolve().parent / "results_stress.json"


def run_stress(metrics_sink: str | None = None):
    """Execute run stress.

    Args:
        metrics_sink: The metrics_sink.
    """

    D_list = [128, 256]
    snr_db_list = [40.0, 20.0, 10.0, 0.0, -10.0, -20.0, -30.0]
    seeds = [0, 1, 2]

    all_rows = []
    for D in D_list:
        for sd in seeds:
            rng = np.random.default_rng(sd)
            a = rng.normal(size=D).astype(np.float32)
            a = a / (np.linalg.norm(a) + 1e-30)
            role_token = f"stress_role_{D}_{sd}"
            from somabrain.apps.core.quantum import HRRConfig, QuantumLayer

            q = QuantumLayer(HRRConfig(dim=D, dtype="float32", renorm=True))
            q.make_unitary_role(role_token)
            c_clean = q.bind_unitary(a, role_token)
            from somabrain.apps.core.numerics import irfft_norm, rfft_norm

            C = rfft_norm(c_clean)
            S = (C * np.conjugate(C)).real
            mean_power = float(np.mean(S)) if S.size else 1.0

            for snr_db in snr_db_list:
                snr_lin = 10.0 ** (snr_db / 10.0)
                noise_power = mean_power / max(snr_lin, 1e-12)
                noise = (
                    rng.normal(size=C.shape) + 1j * rng.normal(size=C.shape)
                ).astype(np.complex128)
                cur_noise_power = float(np.mean((noise * np.conjugate(noise)).real))
                if cur_noise_power <= 0:
                    cur_noise_power = 1.0
                noise = noise * (noise_power / cur_noise_power) ** 0.5

                C_noisy = C.astype(np.complex128) + noise
                c_noisy = irfft_norm(C_noisy, n=D).astype(np.float32)

                a_exact = q.unbind_exact_unitary(c_noisy, role_token)
                a_wien = q.unbind_wiener(c_noisy, role_token, snr_db=snr_db)

                all_rows.append(
                    {
                        "D": D,
                        "seed": int(sd),
                        "snr_db": float(snr_db),
                        "mean_power": mean_power,
                        "exact": {
                            "cosine": cosine_similarity(a, a_exact),
                            "mse": float(np.mean((a - a_exact) ** 2)),
                        },
                        "wiener": {
                            "cosine": cosine_similarity(a, a_wien),
                            "mse": float(np.mean((a - a_wien) ** 2)),
                        },
                    }
                )

    OUT.write_text(
        json.dumps(
            {
                "meta": {"D_list": D_list, "snr_db_list": snr_db_list, "seeds": seeds},
                "results": all_rows,
            },
            indent=2,
        )
    )
    print(f"Wrote stress bench results to {OUT}")
    if metrics_sink:
        try:
            from somabrain.metrics_dump import dump as dump_metrics

            dump_metrics(metrics_sink)
            print(f"Wrote metrics snapshot to {metrics_sink}")
        except Exception as e:
            print(f"Failed to write metrics snapshot: {e}")


if __name__ == "__main__":
    from django.conf import settings

    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-sink", type=str, default=settings.metrics_sink)
    args = parser.parse_args()
    run_stress(metrics_sink=args.metrics_sink)
