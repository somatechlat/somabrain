Numerics Hardening Report

Numerics Hardening Report

Summary
-------

This report summarizes the numeric hardening applied to the HRR primitives and
documents the exact choices implemented in the code.

What changed
------------

- `somabrain/numerics.py`
  - compute_tiny_floor: returns an amplitude tiny (L2 units). Default strategy
    is ``strategy='sqrt'`` (tiny ~ eps * sqrt(D)).
  - normalize_array: uses float64 accumulation, mixes tiny_amp**2 into the
    denominator, and provides three fallback modes: ``legacy_zero``, ``robust``
    (default deterministic baseline ones/sqrt(D)), and ``strict`` which raises
    on subtiny slices.
  - Final float64 renormalization to enforce unit L2 and replacement of
    non-finite entries with the deterministic baseline.

- Benchmarks
  - `benchmarks/numerics_bench.py` (compare strategies)
  - `benchmarks/numerics_bench_multi.py` (sweep)

Test results
------------

- Unit tests (local) covering the changes were executed; the suite passed in
  the working environment.

Microbenchmarks (sample)
------------------------

Selected sample numbers from local runs (D=2048, N=500):

- normalize per-call: 0.0361s
- normalize batched: 0.0351s
- rfft per-call: 0.0167s
- rfft batched: 0.0039s

Interpretation: batched FFTs give strong throughput wins; normalization is
cheap but benefits slightly from batching in large N regimes.

Recommendations
---------------

1. Merge after review. If exact backwards behavior is required for a release,
   preserve ``legacy_zero`` as the default during a short migration window.
2. For production: prefer batched APIs, pin FFT/BLAS builds where reproducibility
   matters, and add runtime metrics for subtiny events and NaN/Inf counts.
3. Add a CI job that runs a small cross-platform numeric regression suite to
   detect L2/invariance regressions.

Next steps I can take
---------------------

- Prepare a PR with changelog and explicit tests asserting the fallback modes.
- Expand benchmarks and store canonical artifacts (JSON/PNG) for release notes.
- Add a small example alias `normalize_safe` if helpful and deprecate ambiguous
  positional signatures.

Report generated: 2025-09-09
