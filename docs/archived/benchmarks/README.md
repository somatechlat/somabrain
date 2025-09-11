Benchmarks
==========

This folder contains canonical benchmark artifacts used in the documentation.

Do not commit large raw CSVs here; prefer small representative CSVs and PNGs.

Repro steps (local):

```bash
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install matplotlib
python benchmarks/cognition_core_bench.py
python benchmarks/tinyfloor_bench.py
```

After running, copy representative PNG/CSV files from `benchmarks/` into this folder and commit them to the docs branch.
