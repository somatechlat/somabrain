import argparse
import json
import os
from pathlib import Path
import numpy as np
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.numerics import irfft_norm, rfft_norm
from somabrain.metrics_dump import dump as dump_metrics
from common.logging import logger

"""Run a focused stress benchmark and write results to benchmarks/results_stress.json.

This runner is safe to execute from the repo root with the project venv.
"""



OUT = Path(__file__).resolve().parent / "results_stress.json"


def run_stress(metrics_sink: str | None = None):
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

            q = QuantumLayer(HRRConfig(dim=D, dtype="float32", renorm=True))
            q.make_unitary_role(role_token)
            c_clean = q.bind_unitary(a, role_token)

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

def cosine(a1, b1):
                    a1 = a1.astype(np.float64)
                    b1 = b1.astype(np.float64)
                    na = float(np.linalg.norm(a1))
                    nb = float(np.linalg.norm(b1))
                    if na == 0 or nb == 0:
                        return 0.0
                    return float(np.dot(a1, b1) / (na * nb))

                all_rows.append(
                    {
                        "D": D,
                        "seed": int(sd),
                        "snr_db": float(snr_db),
                        "mean_power": mean_power,
                        "exact": {
                            "cosine": cosine(a, a_exact),
                            "mse": float(np.mean((a - a_exact) ** 2)),
                        },
                        "wiener": {
                            "cosine": cosine(a, a_wien),
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
            indent=2, )
    )
    print(f"Wrote stress bench results to {OUT}")
    if metrics_sink:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise

            dump_metrics(metrics_sink)
            print(f"Wrote metrics snapshot to {metrics_sink}")
        except Exception as e:
            logger.exception("Exception caught: %s", e)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metrics-sink", type=str, default=os.environ.get("SOMABRAIN_METRICS_SINK")
    )
    args = parser.parse_args()
    run_stress(metrics_sink=args.metrics_sink)
