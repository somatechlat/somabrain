"""Small wrapper to run the cognition benchmark and ensure artifact outputs.

This script runs the existing `benchmarks/cognition_core_bench.py` and
exposes an exit code and artifact locations for CI.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BENCH = ROOT / "cognition_core_bench.py"


def main():
    if not BENCH.exists():
        print("cognition_core_bench.py not found", file=sys.stderr)
        return 2
    rc = subprocess.call([sys.executable, str(BENCH)])
    # check artifact existence
    artifacts = [
        ROOT / "cognition_quality.csv",
        ROOT / "cognition_latency.csv",
        ROOT / "cognition_cosine.png",
    ]
    missing = [p for p in artifacts if not p.exists()]
    if missing:
        print("Missing artifacts:", missing, file=sys.stderr)
        return 3
    print("Bench completed, artifacts:")
    for p in artifacts:
        print(" -", p)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
