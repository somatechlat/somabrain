# Density Matrix Maintenance

This appendix details the implementation in `somabrain/memory/density.py` so invariants can be cross-checked with the math.

## 1. Representation
- ρ is stored as a real symmetric matrix with shape `(dim, dim)`.
- Updates operate in the eigenbasis via `numpy.linalg.eigh` for numerical stability.

## 2. Update Rule
Given an observation vector `v` and learning rate `alpha`:

```
ρ' = (1 - alpha) * ρ + alpha * (v vᵀ)
```

Implementation: `DensityMatrix.observe(vec, alpha)` normalizes `vec`, applies the rank-1 update, then reprojects.

## 3. Projection Steps
1. **Trace normalization** – `normalize_trace()` rescales the matrix so `trace(ρ) = 1`.
2. **PSD projection** – `project_psd()` clips negative eigenvalues to 0 and reconstructs the matrix.
3. **Symmetrization** – `symmetrize()` enforces `(ρ + ρᵀ) / 2` to counter floating point drift.

## 4. Metrics
- `somabrain_density_trace_error_total`: increments when normalization was required.
- `somabrain_density_psd_clip_total`: counts eigenvalues clipped during projection.
- `somabrain_density_condition_number`: gauge emitted via Prometheus `GaugeMetricFamily`.

## 5. Tests
- `tests/test_fd_salience.py` ensures the density matrix stays PSD while salience updates run.
- `tests/test_unified_scorer.py` validates the scorer weights remain in bounds when backed by the matrix.
- `tests/test_legacy_purge.py` guards against reintroducing stub-friendly behaviour.

Keep the maths and code in sync: if you change the update rule, patch this file, update metrics, and add/adjust tests.
