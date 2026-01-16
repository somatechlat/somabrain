"""Run a full sweep: stress + capacity experiments, dump JSON, metrics, and plots.

This script is intended to run in the project venv from the repo root and
produce artifacts under `benchmarks/`:
- results_full.json
- metrics_dump.json
- plots/*.png
"""

from __future__ import annotations

import json
from pathlib import Path
import os

from benchmarks.numerics_workbench import extended_snr_capacity_run
from benchmarks.run_stress import run_stress

OUT = Path(__file__).resolve().parent / "results_full.json"
METRICS = Path(__file__).resolve().parent / "metrics_dump.json"


def run_all():
    # run stress
    """Execute run all."""

    run_stress(metrics_sink=str(METRICS))
    # run extended capacity (writes results_numerics.json)
    extended_snr_capacity_run()
    # merge results
    merged = {
        "meta": {"note": "merged stress + extended"},
        "stress": json.loads(
            Path(__file__).resolve().parent.joinpath("results_stress.json").read_text()
        ),
        "extended": json.loads(
            Path(__file__).resolve().parent.joinpath("results_numerics.json").read_text()
        ),
    }
    OUT.write_text(json.dumps(merged, indent=2))
    print(f"Wrote full results to {OUT}")
    # attempt to plot using existing plot_results.py which expects results_numerics.json
    try:
        import subprocess
        import sys

        repo_root = Path(__file__).resolve().parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root)
        subprocess.check_call(
            [sys.executable, str(repo_root / "benchmarks/plot_results.py")],
            cwd=str(repo_root),
            env=env,
        )
        print("Plots generated (see benchmarks/plots)")
    except Exception as e:
        print("Plot generation failed:", e)


if __name__ == "__main__":
    run_all()
