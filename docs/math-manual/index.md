# Mathematical Foundations Manual

**The Complete Mathematical Blueprint of SomaBrain's Cognitive Architecture**

---

## 📐 Purpose

This manual provides rigorous mathematical documentation of SomaBrain's core algorithms, complete with:
- **Formal definitions** and theorems
- **Visual diagrams** of operations
- **Worked examples** with real data
- **Performance characteristics** and complexity analysis
- **Verification proofs** of invariants

**Audience:** Researchers, mathematicians, ML engineers, and anyone who wants to understand the REAL math behind SomaBrain.

---

## 📚 Table of Contents

### Core Mathematical Frameworks

1. **[Binary Hyperdimensional Computing (BHDC)](01-bhdc-foundations.md)**
   - Vector space properties
   - Binding and unbinding operations
   - Spectral invariants
   - Permutation-based composition

2. **[Governed Superposition & Memory Traces](02-superposition-traces.md)**
   - Exponential decay dynamics
   - Rotation matrices for tenant isolation
   - Cleanup indexes and nearest-neighbor search
   - Interference bounds

3. **[Unified Scoring & Multi-Signal Fusion](03-unified-scoring.md)**
   - Cosine similarity in high-dimensional spaces
   - Frequent-Directions subspace projection
   - Exponential recency decay
   - Adaptive temperature control

4. **[Adaptive Learning Dynamics](04-adaptive-learning.md)**
   - Weight update rules
   - Decoupled gain parameters
   - Entropy caps and diversity control
   - Convergence guarantees

5. **[Frequent-Directions Sketching](05-fd-sketching.md)**
   - Online covariance approximation
   - SVD compression algorithm
   - Error bounds and guarantees
   - Subspace projection

6. **[Heat Diffusion on Graphs](06-heat-diffusion.md)**
   - Graph Laplacian operators
   - Matrix exponential approximation
   - Chebyshev vs Lanczos methods
   - Belief propagation dynamics

7. **[Neuromodulation & Control Theory](07-neuromodulation.md)**
   - Dopamine-modulated learning rates
   - Serotonin smoothing
   - Noradrenaline gain control
   - Acetylcholine attention gating

---

## 🎨 Visual Guide

### Memory Operations Flow
```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY LIFECYCLE                          │
└─────────────────────────────────────────────────────────────┘

INPUT TEXT                    EMBEDDING                    STORAGE
    │                            │                            │
    ▼                            ▼                            ▼
┌────────┐    encode()    ┌──────────┐   bind()      ┌──────────┐
│"Paris  │───────────────▶│ [0.2,    │──────────────▶│Superposed│
│is the  │                │  0.8,    │               │  Trace   │
│capital"│                │  -0.1,   │               │   M_t    │
└────────┘                │  ...]    │               └──────────┘
                          │ 2048-D   │                     │
                          └──────────┘                     │
                                                           ▼
QUERY                     RETRIEVAL                    CLEANUP
    │                         │                            │
    ▼                         ▼                            ▼
┌────────┐    embed()   ┌──────────┐   unbind()    ┌──────────┐
│"capital│──────────────▶│ q_vec    │──────────────▶│ Nearest  │
│ France"│               │ 2048-D   │               │ Neighbor │
└────────┘               └──────────┘               │  Search  │
                                                    └──────────┘
                                                          │
                                                          ▼
                                                    ┌──────────┐
                                                    │ "Paris"  │
                                                    │ score:   │
                                                    │  0.94    │
                                                    └──────────┘
```

---

## 🔬 Mathematical Notation Guide

| Symbol | Meaning | Example |
|--------|---------|---------|
| `⊙` | Binding (elementwise product) | `c = a ⊙ b` |
| `⊕` | Superposition (normalized sum) | `s = a ⊕ b ⊕ c` |
| `‖·‖` | L2 norm | `‖v‖ = √(Σv_i²)` |
| `⟨·,·⟩` | Inner product | `⟨a,b⟩ = Σa_i·b_i` |
| `η` | Decay/injection factor | `0 < η ≤ 1` |
| `τ` | Temperature parameter | `τ ∈ [τ_min, τ_max]` |
| `α,β,γ` | Retrieval weights | Learned parameters |
| `λ,μ,ν` | Utility weights | Learned parameters |
| `L` | Graph Laplacian | `L = D - A` |
| `exp(-tL)` | Heat kernel | Matrix exponential |

---

## 📊 Key Theorems & Guarantees

### **Theorem 1: Spectral Preservation**
For any binding operation `c = bind(a, b)` using permutation-based BHDC:
```
‖FFT(c)‖ ≈ ‖FFT(a)‖ · ‖FFT(b)‖
```
**Proof:** See [BHDC Foundations](01-bhdc-foundations.md#spectral-preservation)

### **Theorem 2: Bounded Interference**
For exponential decay with factor `η`, the interference from memory `i` after `t` steps:
```
I_i(t) ≤ (1-η)^t · ‖M_i‖
```
**Proof:** See [Superposition Traces](02-superposition-traces.md#interference-bounds)

### **Theorem 3: FD Approximation Error**
For Frequent-Directions sketch with rank `ℓ`:
```
‖X^T X - S^T S‖_2 ≤ (‖X‖_F² / ℓ)
```
**Proof:** See [FD Sketching](05-fd-sketching.md#error-bounds)

### **Theorem 4: Heat Kernel Convergence**
For Chebyshev approximation with degree `K`:
```
‖exp(-tL)x - C_K(L)x‖ ≤ ε(K,t,λ_max)
```
**Proof:** See [Heat Diffusion](06-heat-diffusion.md#convergence-analysis)

---

## 🎯 Quick Reference: Complexity Analysis

| Operation | Time Complexity | Space Complexity | Notes |
|-----------|----------------|------------------|-------|
| Bind/Unbind | O(D) | O(D) | D = dimension (2048) |
| Superpose | O(nD) | O(D) | n = number of vectors |
| Cleanup | O(k·D) | O(k·D) | k = anchor count |
| FD Insert | O(ℓ²D) | O(ℓD) | ℓ = sketch rank |
| Heat Diffusion (Chebyshev) | O(K·E) | O(N) | K = degree, E = edges |
| Heat Diffusion (Lanczos) | O(m²N) | O(mN) | m = Krylov dimension |
| Unified Scoring | O(D) | O(1) | Per candidate |
| Adaptation Update | O(1) | O(1) | Per feedback |

---

## 🧪 Verification & Testing

All mathematical claims in this manual are:
- ✅ **Implemented** in production code
- ✅ **Tested** with property-based tests
- ✅ **Verified** with real-time invariant checking
- ✅ **Benchmarked** with performance measurements
- ✅ **Monitored** via Prometheus metrics

**Code References:**
- Core implementations: `somabrain/quantum.py`, `somabrain/memory/`, `somabrain/math/`
- Tests: `tests/core/`, `tests/benchmark/`
- Benchmarks: `benchmarks/`
- Metrics: `somabrain/metrics.py`, `somabrain/metrics_extra/`

---

## 📖 How to Use This Manual

**For Researchers:**
- Start with [BHDC Foundations](01-bhdc-foundations.md) for the core algebra
- Read [Superposition Traces](02-superposition-traces.md) for memory dynamics
- Study [Heat Diffusion](06-heat-diffusion.md) for graph-based reasoning

**For Engineers:**
- Focus on [Unified Scoring](03-unified-scoring.md) for retrieval tuning
- Review [Adaptive Learning](04-adaptive-learning.md) for feedback loops
- Check [FD Sketching](05-fd-sketching.md) for dimensionality reduction

**For Mathematicians:**
- All theorems include formal proofs
- Complexity analysis provided for each algorithm
- Error bounds and convergence guarantees documented

---

## 🔗 Related Documentation

- **[Technical Manual](../technical-manual/)** - System architecture and deployment
- **[User Manual](../user-manual/)** - API usage and feature guides
- **[Development Manual](../development-manual/)** - Code structure and contribution
- **[Benchmarks](../../benchmarks/)** - Performance measurements and plots

---

## 📝 Contributing

Found an error? Want to add a proof? See [Development Manual](../development-manual/contribution-process.md).

All mathematical content must include:
1. Formal definition with notation
2. Visual diagram or example
3. Complexity analysis
4. Code reference
5. Test coverage reference

---

**Last Updated:** 2025-01-20  
**Version:** 1.0.0  
**Maintainers:** SomaBrain Core Team
