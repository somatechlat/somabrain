# SomaBrain Rust Core

High-performance CPU-bound operations for the SomaBrain cognitive architecture.

## Overview

This crate implements the **GMD MathCore** (Governing Memory Dynamics Mathematical Core)
as specified in the MathCore White Paper v4.4.

## Module Structure

| Module | Description |
|--------|-------------|
| `lib.rs` | Module registration and unit tests |
| `bhdc.rs` | Binary Hyperdimensional Computing (encoder, PermutationBinder) |
| `neuro.rs` | Neuromodulators (dopamine, serotonin, etc.) |
| `prediction.rs` | SlowPredictor / MahalanobisPredictor, Consolidation |
| `mathcore.rs` | GMD Theorems 2-4, BayesianMemory, quantizer, Wiener λ* |
| `adaptation.rs` | AdaptationEngine for weight updates |

## GMD MathCore Theorems (as implemented)

### Sparsity p (engineering choice — no theorem)

Production BHDC sparsity is `p = 0.1` (`SOMABRAIN_BHDC_SPARSITY`, constant
`PRODUCTION_SPARSITY_P`). There is **no** exported `compute_optimal_p` and no
"p*" theorem: the former `(1 + √δ)/2` formula always returned ≥ 0.5 and never
recommended `p = 0.1` (DEBT-012 / SOMA-BR-MATH-TRUTH-001 T12).

### Theorem 2: Bayesian Memory
- `BayesianMemory` class with SNR-optimal recall
- `BayesianMemory::new(dimension, eta, lambda_reg)`
- `update(binding)` — Memory update: m = (1−η)m + ηb
- `compute_snr_at_lag(lag)` — SNR(L) ≈ D · w_L² / (W² − w_L²), w_L = η(1−η)^L
- `estimate_horizon(snr_min)` — largest lag with SNR ≥ snr_min

### Theorem 3: Quantization-Aware Unbinding
- `compute_wiener_lambda(p, bits)` — Optimal λ* = Δ² / (12 p (1−p)) with
  Δ = 2/(2^bits − 1) (Δ = 2/255 for 8-bit). Honors `bits`.
- `quantize_8bit(x)` — 256-level symmetric quantization on [-1, 1]:
  `Q(x) = (clamp(round((x+1)/2 · 255), 0, 255) / 255) · 2 − 1`
- `wiener_unbind(memory, key, lambda)` — MMSE unbinding `(c ⊙ k) / (k² + λ)`

### Theorem 4: Fast Walsh-Hadamard Transform
- `fwht(v)` — O(D log D), orthonormal scale 1/√D
- Raises `ValueError` unless `len(v)` is a power of two (never a silent no-op)

## Building

```bash
cd rust_core
maturin build --release
pip install target/wheels/somabrain_rs-*.whl
```

`maturin` enables the `extension-module` feature (see `pyproject.toml`), so the
wheel is a proper Python extension module.

## Testing

```bash
cargo test
```

Plain `cargo test` links libpython (the `extension-module` feature is opt-in);
the unit-test binary therefore runs without a special feature flag.

## Usage from Python

```python
import somabrain_rs as rs

# Wiener ridge λ* at sparsity p (8-bit quantizer: Δ = 2/255)
lam = rs.compute_wiener_lambda(0.1, 8)  # → 5.695814999928801e-05

# Bayesian Memory (Theorem 2)
mem = rs.BayesianMemory(2048, eta=0.08, lambda_reg=lam)
mem.update(binding)
recalled = mem.recall(key)
horizon = mem.estimate_horizon(1.0)
snr = mem.compute_snr_at_lag(0)

# Wiener unbind (Theorem 3)
v = rs.wiener_unbind(memory, key, lam)

# FWHT (Theorem 4) — raises ValueError on non-2^r length
rotated = rs.fwht(vector)

# AdaptationEngine (18x faster than Python)
engine = rs.AdaptationEngine(learning_rate=0.05)
engine.apply_feedback(utility_signal=0.8, reward=0.5)
alpha, beta, gamma, tau = engine.get_retrieval()
```

## License

Proprietary - SomaTech
