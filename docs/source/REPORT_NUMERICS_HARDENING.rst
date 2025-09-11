Numerics Hardening Report
=========================

Summary
-------

This short report records the controlled numeric hardening applied to SomaBrain's
HRR primitives to improve determinism and numerical robustness.

Changes
-------

- compute_tiny_floor: canonicalized to return an amplitude (L2) tiny. Spectral callers
  must convert via power_per_bin = tiny_amp**2 / D.
- normalize_array: float64 accumulation, explicit tiny**2 mixing into denominators,
  and a deterministic fallback baseline (``ones/sqrt(D)``) in robust mode.
- Spectral denominators (deconvolution) use power units. Code now forms
  power_floor_per_bin = tiny_amp**2 / D before mixing with other spectral eps.

Validation
----------

- Unit tests added and run; new numerics tests pass locally.
- Smoke bench runs executed and generated bench artifacts.

Next steps
----------

- Optionally run the full benchmark sweep and attach canonical artifacts (JSON/PNG)
  to the release notes (requires longer compute time).
- Decide whether to make ``normalize_array`` default mode "robust" (behavioral change).

For implementation details see ``somabrain/numerics.py`` and ``somabrain/quantum.py``.

Production readiness
--------------------

Why these changes make SomaBrain production-ready
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Predictability: deterministic seeding and deterministic tiny-floor fallbacks remove
  a large class of non-deterministic outcomes that make debugging and incident response
  difficult in production.
- Robustness: unitary FFTs, float64 accumulation, and conservative tiny-floor policies
  mitigate numerical breakdowns (underflow/overflow, divide-by-zero) across hardware and
  BLAS/FFT implementations.
- Observability & auditability: explicit unit conversions (amplitude -> power) and
  clear numeric contracts make it straightforward to audit algorithms and validate
  behavior against test benches and metrics.
- Compatibility: the conservative defaults are safe for production but remain configurable
  for high-performance research runs; they preserve backward compatibility with older data
  while making failures explicit.

These improvements are low-risk and focused on correctness and observability — they are
the core prerequisites for promoting the numerics stack to production use.
