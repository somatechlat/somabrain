NUMERICS: Mathematical Specification

This document records the precise numeric contracts used by SomaBrain's HRR
primitives. It is intentionally concise and rigorous so implementations across
platforms produce predictable and auditable behavior.

1. Unitary FFT contract

- Functions: `rfft_norm(x, n=None, axis=-1)` and `irfft_norm(X, n, axis=-1)`.
- Contract: for real-valued x, irfft_norm(rfft_norm(x)) == x within round-trip
  floating point error. Both use `norm='ortho'` (unitary transform) so
  Parseval's identity holds exactly in floating-point arithmetic up to
  rounding: ||x||_2^2 == ||R(x)||_2^2 where R(x) is rfft_norm(x).

2. Tiny-floor policy

- Function: `compute_tiny_floor(D, dtype=np.float32, strategy='sqrt', scale=1.0)`
- Default: tiny = max(eps(dtype) * sqrt(max(1,D)) * scale, TINY_MIN[dtype])
  where eps(dtype) = np.finfo(dtype).eps and TINY_MIN provides small
  dtype-specific lower bounds (float32->1e-6, float64->1e-12).
- Rationale: L2 norm of random vectors scales ~sqrt(D); floor scales with
  the same factor to avoid false "subtiny" flags.

3. Normalization semantics

- Function: `normalize_array(x, axis=-1, keepdims=False, tiny_floor_strategy='sqrt', dtype=np.float32, strict=False, mode='legacy_zero')`
- Modes:
  - `legacy_zero`: when norm < tiny, return zero-vector (backwards compatible).
  - `robust`: when norm < tiny, replace by deterministic baseline vector
     (ones/sqrt(D)) which preserves unit norm and avoids zeros/NaNs.
  - `strict`: raise ValueError on subtiny norms.
- Implementation notes:
  - Reductions are performed in float64 for stability, then results are cast
    back to the requested dtype.
  - Final pass enforces exact unit L2-norm per-slice in float64 to reduce
    rounding drift.

4. Deterministic seeding

- Seed utilities create reproducible RNGs from integer seeds using numpy's
  PCG64/SeedSequence. Callers must pass explicit seeds for reproducibility.

5. Wiener (Tikhonov) deconvolution

- Use lambda-regularized inverse: X * conj(Y) / (|Y|^2 + lambda) as the
  Wiener deconvolution in frequency domain. Lambda selection is heuristic
  from SNR; defaults are conservative.

6. Compatibility & portability

- Floating point drift is expected across different BLAS/FFT vendors and
  CPU architectures. Define numeric tolerances for invariants (example: relative
  error <= 1e-6 for unit-norm checks) and add cross-platform CI checks.

7. Performance guidance

- Batch multiple vectors into an NxD array and call `rfft_norm` once to get
  significant speedups versus N python-level calls.
- Pre-allocate buffers for hot paths to avoid allocation churn.


Small theorem (informal): Let x be real of length D and R the unitary rfft.
Then ||x||_2 == ||R(x)||_2 up to rounding. Using normalization and tiny-floor
policy above preserves L2 geometry for downstream binding/unbinding.


Document version: 1.0
