Numerics Hardening Report

Summary
-------
I hardened the core numeric primitives used by the HRR cognition core and
validated them with unit tests and microbenchmarks. Changes are on branch
`numerics/hardening`.

What changed
------------
- `somabrain/numerics.py`
  - Added caching for `compute_tiny_floor`.
  - Use float64 intermediates for reductions to reduce rounding error.
  - Added final float64 renormalization to enforce unit L2 norm more robustly.
  - Added `mode` to `normalize_array` with choices: `legacy_zero` (default),
    `robust` (baseline unit-vector), and `strict` (raise on subtiny).
  - Backwards-compatible padding/truncation when callers pass dimension D.
- `somabrain/batch.py`
  - Already provided batched helpers; `rfft_norm`/`irfft_norm` used directly.
- Benchmarks
  - `benchmarks/numerics_bench.py` (quick compare)
  - `benchmarks/numerics_bench_multi.py` (sweep across D and N)
- Docs
  - `docs/NUMERICS_MATH_SPEC.md` describes the math contracts and choices.

Test results
------------
- Ran full pytest suite in `.venv` — all tests passed.

Microbenchmarks (sample)
------------------------
Results from `benchmarks/numerics_bench.py` (D=2048, N=500)
- normalize per-call: 0.0361s
- normalize batched: 0.0351s
- rfft per-call: 0.0167s
- rfft batched: 0.0039s

Results from `benchmarks/numerics_bench_multi.py` (selected rows)
D=2048 N=1024: normalize 0.0409s, rfft 0.0059s
D=8192 N=1024: normalize 0.2322s, rfft 0.0314s

Interpretation: batched FFTs show large relative improvements; normalization
is cheaper but benefits from batching when N is large.

Recommendations
---------------
1. Merge `numerics/hardening` after review. The default `mode='legacy_zero'`
   preserves existing behavior while allowing migration to `robust`.
2. For production at scale:
   - Use batched APIs and pre-allocated buffers for hot paths.
   - Vendor/pin FFT and BLAS builds where possible to reduce cross-host
     numerical drift.
   - Add runtime metrics for subtiny/NaN events and vector checksums for
     cross-host validation.
3. Consider adding a CI job that runs the small cross-platform regression
   tests (unit-norm invariants) on multiple platforms.

Next steps I can take
---------------------
- Prepare a PR with changelog and tests that assert the `mode` behaviours.
- Expand benchmarks (memory profiling, pre-alloc reuse patterns).
- Add an example `normalize_safe` alias and deprecate ambiguous positional
  arguments.


Report generated: 2025-09-09
