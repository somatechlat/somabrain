Numerics Hardening Report
=========================

Summary
-------

This document records the targeted changes made to the numeric core to improve
robustness and determinism for HRR operations used in SomaBrain.

Changes
-------

- Canonicalized `compute_tiny_floor` to return an *amplitude* tiny (L2-norm units).
  Callers that need spectral (per-FFT-bin) power floors must convert with
  `power_per_bin = tiny_amp**2 / D`.
- `normalize_array` now mixes in tiny**2 with sum-of-squares when deciding "subtiny" slices
  and uses a deterministic baseline fallback (`ones / sqrt(D)`) in robust mode.
- Spectral denominators in `somabrain/quantum.py` are formed in power units; the code now
  computes `power_floor_per_bin = tiny_amp**2 / D` before mixing with base spectral eps.

Validation
----------

- Full test suite was executed (`pytest -q`) after edits: all tests passed.
- Bench harness smoke-run completed and wrote `benchmarks/bench_numerics_results.json`.

Next steps
----------

- Run the full benchmark sweep across the recommended D/dtypes/trials and collect
  canonical artifacts (JSON/PNG) for the docs. This step is long-running and will be
  executed only on user approval.
- Add small unit tests asserting the tiny amplitude contract and spectral-floor conversion.

For details and code, see `somabrain/numerics.py` and `somabrain/quantum.py`.
