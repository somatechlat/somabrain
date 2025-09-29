# Math Verification Report (Current State)

## 1. Scope
Covers HRR binding/unbinding (robust, exact, Wiener), role generation determinism and spectrum, normalization stability, tiny-floor scaling.

## 2. Property Tests Implemented
| Area | Test | Assertion |
|------|------|-----------|
| Roles | role_spectrum_unitarity_and_determinism | |H_k|≈1, deterministic, norm preservation through bind |
| Bind/Unbind | bind_unbind_roundtrip | cosine ≥ 0.97 (small dim) / 0.985 (≥512) |
| Wiener | wiener_improves_with_higher_snr | cos(60dB) ≥ cos(40dB) ≥ cos(20dB) > 0.9 |
| Exact vs Robust | exact_not_worse_than_robust | exact cosine ≥ robust cosine |
| Normalization | normalize_array_idempotent | normalize twice == once |
| Tiny Floor | tiny_floor_scaling | t ~ sqrt(D); ratio within ±20% band |
| Determinism | role & text encoding tests | repeatable arrays (1e-7 atol) |
| Baseline Fallback | numerics properties | zero vector → baseline / strict raises |

## 3. Key Invariants Confirmed
- Unitary role spectra preserved.
- FFT-based unbinding stable with adaptive spectral floor.
- Deterministic seeding pipeline intact across role and text encodings.
- Norm preservation in unitary bind within 0.05% tolerance.

## 4. Fixes Applied
- Dimension validation for cached roles (prevents cross-dim contamination).

## 5. Residual Risks / Next Targets
| Risk | Mitigation Candidate |
|------|----------------------|
| Large-dim (>16k) cache memory growth | Add LRU for role cache or on-disk mmap rotation |
| Missing Sinkhorn marginal regression | Add sinkhorn property test (planned) |
| No spectral heat-kernel error bound test | Add Chebyshev vs Lanczos delta check |
| Wiener floor instrumentation | Optional: expose eps_used in return tuple (deferred) |

## 6. Operational Signals to Monitor
| Metric | Interpretation |
|--------|---------------|
| UNBIND_EPS_USED | Jump indicates spectral instability or dim too low |
| HRR_CLEANUP_SCORE | Drop signals anchor drift / capacity nearing saturation |
| RECALL_MARGIN_TOP12 | Quality proxy for retrieval discrimination |

## 7. Acceptance Criteria Met
- All implemented property tests pass on baseline environment.
- No NaNs or norm explosions encountered.
- Role determinism confirmed with 1e-7 tolerance.

## 8. Pending (Optional) Enhancements
1. Sinkhorn marginal L∞ test (n=m=32 synthetic).
2. Spectral exp(-tA) parity test (Chebyshev K=24 vs Lanczos m=32).
3. Unbind API optional artifact: `(vector, eps_used)`.

Keep this report concise—update only when invariants or coverage meaningfully expand.
