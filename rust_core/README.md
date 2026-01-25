# SomaBrain Rust Core

High-performance CPU-bound operations for the SomaBrain cognitive architecture.

## Overview

This crate implements the **GMD MathCore** (Governing Memory Dynamics Mathematical Core)
as specified in the MathCore White Paper v4.0.

## Module Structure

| Module | Lines | Description |
|--------|-------|-------------|
| `lib.rs` | 179 | Module registration and unit tests |
| `bhdc.rs` | 175 | Binary Hyperdimensional Computing |
| `neuro.rs` | 126 | Neuromodulators (dopamine, serotonin, etc.) |
| `prediction.rs` | 217 | Slow/Fast predictors, Consolidation |
| `mathcore.rs` | 402 | GMD Theorems 1-4, BayesianMemory |
| `adaptation.rs` | 234 | AdaptationEngine for weight updates |

## GMD MathCore Theorems

### Theorem 1: Optimal Encoding
- `compute_optimal_p(delta)` - Optimal sparsity: p* = (1 + √δ) / 2
- `compute_capacity_theorem1(D, p, delta, epsilon)` - Capacity: N = √(2εDδp/(1-p))

### Theorem 2: Bayesian Memory
- `BayesianMemory` class with SNR-optimal recall
- `update(binding)` - Memory update: m = (1-η)m + ηb
- `compute_snr(p)` - Signal-to-noise ratio
- `compute_gamma(p)` - Recall quality: γ = √(SNR/(1+SNR))
- `estimate_capacity()` - Capacity: N = D/(α·η)

### Theorem 3: Quantization-Aware Unbinding
- `compute_wiener_lambda(p, bits)` - Optimal λ* for Wiener filter
- `quantize_8bit(x)` - 8-bit quantization: Q(x) = round(127(x+1))/127 - 1
- `wiener_unbind(memory, key, lambda)` - MMSE unbinding

### Theorem 4: Fast Walsh-Hadamard Transform
- `fwht(v)` - O(D log D) complexity, 127,000× faster than QR decomposition

## Performance

| Operation | Speed | Compared to Python |
|-----------|-------|-------------------|
| FWHT(2048) | 11,865/sec | 127,000× vs QR |
| AdaptationEngine.apply_feedback | 5.9M/sec | 18.4× |
| BayesianMemory.recall | ~10K/sec | N/A (new) |

## Building

```bash
cd rust_core
maturin build --release
pip install target/wheels/somabrain_rs-*.whl
```

## Testing

```bash
cargo test
```

## Usage from Python

```python
import somabrain_rs as rs

# GMD Theorem 1: Optimal sparsity
p_star = rs.compute_optimal_p(0.01)  # → 0.55

# GMD Theorem 2: Bayesian Memory
mem = rs.BayesianMemory(2048, eta=0.08)
mem.update(binding)
recalled = mem.recall(key)
capacity = mem.estimate_capacity()  # → 40
snr = mem.compute_snr(0.1)  # → 183.96

# GMD Theorem 3: Wiener unbind
v = rs.wiener_unbind(memory, key, 2.05e-5)

# GMD Theorem 4: FWHT
rotated = rs.fwht(vector)

# AdaptationEngine (18x faster than Python)
engine = rs.AdaptationEngine(learning_rate=0.05)
engine.apply_feedback(utility_signal=0.8, reward=0.5)
alpha, beta, gamma, tau = engine.get_retrieval()
```

## License

Proprietary - SomaTech
