# ADR-003: BHDC Memory Core and Unified Scoring Stack

## Status

Accepted – October 14, 2025

## Context

The legacy FFT/mask-composer memory math relied on dense hypervectors, Wiener
recovery, and separate density-matrix scoring. It incurred high latency,
required large FFT kernels, and complicated memory binding with floating-point
artifacts. Lane A of the "Faster ⇒ Smarter" roadmap mandates migrating to the
BHDC stack (binary/sparse hypervectors, permutation binder, FD salience, unified
scorer) before downstream context/meta work begins.

Goals:

- Deterministic, sparse binary hypervectors with permutation binding/unbinding.
- Frequent-Directions salience sketch that captures ≥0.9 spectral energy.
- Unified scorer combining cosine, FD projection, and recency with bounded
  weights and telemetry.
- Explicit smoking-guns that prevent mask-composer regressions from returning.

## Decision

1. Adopt `somabrain.math.bhdc_encoder.BHDCEncoder` and
   `PermutationBinder` as the only binding implementation. `HRRConfig.binding_method`
   now rejects any value other than `bhdc`, and `mask_composer` modules raise
   `ImportError` so legacy code fails fast.
2. Replace the dense salience routine with
   `somabrain.salience.FDSalienceSketch`, feeding residual/capture ratios into
   `AmygdalaSalience` and exposing Prometheus metrics
   (`somabrain_fd_energy_capture_ratio`, `somabrain_fd_residual_ratio`).
3. Introduce `somabrain.scoring.UnifiedScorer`, weighting cosine, FD projection,
   and recency with clamped coefficients, and track contributions/final scores
   through new metrics (`somabrain_scorer_component`, `somabrain_scorer_final`,
   `somabrain_scorer_weight_clamped_total`). Working-memory structures receive a
   shared scorer instance.
4. Update CI (`.github/workflows/hybrid-ci.yml`) to run math-core tests:
   `test_bhdc_binding`, `test_fd_salience`, `test_unified_scorer`, and the new
   `test_legacy_purge` guard that ensures disallowed modules/methods error out.
5. Document the change and guard rails in this ADR. README/ROADMAP now reflect
   the BHDC-era stack; the prior mask composer references are removed.

## Consequences

- Binding/unbinding now uses sparse binary vectors, reducing latency and memory
  footprint and aligning with hardware acceleration plans.
- Salience scoring leverages low-rank FD sketches, improving selectivity while
  preserving energy-capture guarantees and observability.
- Unified scoring provides a single O(D + r) path with configurable weights, and
  telemetry makes it auditable in production.
- Any attempt to re-enable mask composer or FFT methods fails at import time or
  during configuration, with tests and CI enforcing the ban.
- Future work in Lane A/B can depend exclusively on the BHDC stack without
  branching for legacy codepaths.
