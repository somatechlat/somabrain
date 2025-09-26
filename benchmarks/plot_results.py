"""Plot bench results for numerics (cosine & MSE vs SNR) and save PNGs.

Reads `benchmarks/results_numerics.json` produced by `numerics_workbench.py`.
Saves PNG files under `benchmarks/plots/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

IN = Path(__file__).resolve().parent / "results_numerics.json"
OUTDIR = Path(__file__).resolve().parent / "plots"

if not IN.exists():
    print(f"Input results not found: {IN}. Run benchmarks/numerics_workbench.py first.")
    raise SystemExit(1)

data = json.loads(IN.read_text())
rows = data.get("results", [])

# group by D
byD = {}
for r in rows:
    D = int(r["D"])
    byD.setdefault(D, []).append(r)

OUTDIR.mkdir(parents=True, exist_ok=True)

try:
    import matplotlib.pyplot as plt

    for D, items in sorted(byD.items()):
        snrs = sorted({float(r["snr_db"]) for r in items})
        mean_exact = [
            mean([r["exact"]["cosine"] for r in items if float(r["snr_db"]) == s])
            for s in snrs
        ]
        mean_wien = [
            mean([r["wiener"]["cosine"] for r in items if float(r["snr_db"]) == s])
            for s in snrs
        ]
        plt.figure(figsize=(6, 4))
        plt.plot(snrs, mean_exact, marker="o", label="Exact")
        plt.plot(snrs, mean_wien, marker="o", label="Wiener")
        plt.xlabel("SNR (dB)")
        plt.ylabel("Cosine similarity")
        plt.title(f"Recovery cosine vs SNR (D={D})")
        plt.grid(True)
        plt.legend()
        outpng = OUTDIR / f"cosine_D{D}.png"
        plt.savefig(outpng, bbox_inches="tight", dpi=150)
        plt.close()

        # MSE plot
        mean_mse_exact = [
            mean([r["exact"]["mse"] for r in items if float(r["snr_db"]) == s])
            for s in snrs
        ]
        mean_mse_wien = [
            mean([r["wiener"]["mse"] for r in items if float(r["snr_db"]) == s])
            for s in snrs
        ]
        plt.figure(figsize=(6, 4))
        plt.plot(snrs, mean_mse_exact, marker="o", label="Exact")
        plt.plot(snrs, mean_mse_wien, marker="o", label="Wiener")
        plt.xlabel("SNR (dB)")
        plt.ylabel("MSE")
        plt.title(f"Recovery MSE vs SNR (D={D})")
        plt.yscale("log")
        plt.grid(True)
        plt.legend()
        outpng2 = OUTDIR / f"mse_D{D}.png"
        plt.savefig(outpng2, bbox_inches="tight", dpi=150)
        plt.close()

    print(f"Saved plots to {OUTDIR}")
except Exception as e:
    print("matplotlib not available or plotting failed:", e)
    print("You can inspect the JSON at:", IN)
    raise
