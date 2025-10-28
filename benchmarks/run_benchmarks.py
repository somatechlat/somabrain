"""Run selected benchmark scripts with the repository on sys.path.

This runner ensures the repository root is on sys.path so benchmark scripts
that import top-level modules (arc_cache, etc.) work regardless of install state.
"""

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BENCHES = [
    "benchmarks.numerics_bench",
    "benchmarks.cognition_core_bench",
    "benchmarks.retrieval_bench",
]


def run_module(mod_name: str):
    print(f"Running {mod_name}")
    runpy.run_module(mod_name, run_name="__main__")


def main():
    for m in BENCHES:
        try:
            run_module(m)
        except SystemExit:
            # benchmark may call sys.exit()
            pass
        except Exception as e:
            print(f"Benchmark {m} failed: {e}")


if __name__ == "__main__":
    main()
