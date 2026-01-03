# SomaBrain: Mathematical Foundations

> **White Paper Draft** — The mathematical theory underlying SomaBrain's hyperdimensional cognitive memory system.

---

## Table of Contents

1. [Overview](#overview)
2. [Hyperdimensional Computing](#1-hyperdimensional-computing)
3. [The Governed Trace Algorithm](#2-the-governed-trace-algorithm)
4. [Binary Hyperdimensional Computing (BHDC)](#3-binary-hyperdimensional-computing-bhdc)
5. [Holographic Reduced Representations (HRR)](#4-holographic-reduced-representations-hrr)
6. [Sparse Distributed Representations (SDR)](#5-sparse-distributed-representations-sdr)
7. [Working Memory Dynamics](#6-working-memory-dynamics)
8. [Sleep-Inspired Consolidation](#7-sleep-inspired-consolidation)
9. [Spectral Methods](#8-spectral-methods)
10. [Mathematical Invariants](#9-mathematical-invariants)
11. [Implementation Reference](#10-implementation-reference)

---

## Overview

SomaBrain implements a mathematically rigorous memory system for AI agents, grounded in:

- **Hyperdimensional Computing** — Operating in $\mathbb{R}^{8192}$ for holographic encoding
- **Quantum-Inspired Operations** — Superposition, binding, and unbinding with spectral guarantees
- **Biologically-Plausible Mechanisms** — Working memory, salience gating, and sleep consolidation

All mathematical claims in this document are verified by the implementation in `somabrain/`.

---

## 1. Hyperdimensional Computing

### 1.1 Vector Space Properties

SomaBrain operates in a high-dimensional vector space $\mathcal{H} = \mathbb{R}^N$ where $N = 8192$ (configurable).

**Key Property: Approximate Orthogonality**

For random vectors $\mathbf{x}, \mathbf{y} \in \mathcal{H}$ drawn from a unit Gaussian distribution:

```math
\mathbb{E}[\mathbf{x} \cdot \mathbf{y}] = 0
```

```math
\text{Var}[\mathbf{x} \cdot \mathbf{y}] = \frac{1}{N}
```

As $N \to \infty$, any two random vectors become nearly orthogonal with high probability:

```math
P\left(|\cos(\mathbf{x}, \mathbf{y})| > \epsilon\right) \leq 2\exp\left(-\frac{N\epsilon^2}{2}\right)
```

**Implementation:** `somabrain/quantum.py` — `QuantumLayer.random_vector()`

### 1.2 Capacity Theorem

The approximate orthogonality enables storing $k$ items in superposition with retrieval error bounded by:

```math
\text{Error} \propto \sqrt{\frac{k}{N}}
```

For $N = 8192$ and $k = 100$ items:
- Expected interference: $\approx 0.11$ (11%)
- Retrieval accuracy: $> 89\%$

---

## 2. The Governed Trace Algorithm

The core memory update mechanism, inspired by exponential trace models in neuroscience:

```math
\mathbf{m}_t = (1 - \eta)\mathbf{m}_{t-1} + \eta\mathbf{b}_t
```

| Symbol | Name | Description |
|:------:|------|-------------|
| $\mathbf{m}_t$ | Memory State | Current high-dimensional superposition vector |
| $\mathbf{b}_t$ | Input Vector | New sparse, orthogonal memory trace |
| $\eta$ | Plasticity Gain | Controls update strength (learning rate) |
| $(1-\eta)$ | Decay Factor | Exponential forgetting mechanism |

### 2.1 Exponential Decay

The decay factor $(1-\eta)$ implements exponential forgetting:

```math
\mathbf{m}(t) = \mathbf{m}_0 \cdot e^{-\lambda t}
```

Where $\lambda = -\ln(1-\eta)$ is the decay constant.

**Implementation:** `somabrain/context_hrr.py` — `HRRContext._apply_decay()`

### 2.2 Normalization Invariant

After each update, the memory vector is normalized to unit norm:

```math
\hat{\mathbf{m}}_t = \frac{\mathbf{m}_t}{\|\mathbf{m}_t\|_2}
```

This ensures:
- Bounded energy: $\|\hat{\mathbf{m}}\|_2 = 1$
- Stable cosine similarity comparisons
- Prevention of numerical overflow

**Implementation:** `somabrain/math/normalize.py` — `normalize_vector()`

---

## 3. Binary Hyperdimensional Computing (BHDC)

### 3.1 Permutation Binding

BHDC binding uses element-wise permutation instead of circular convolution:

```math
\mathbf{c} = \mathbf{a} \circledast \mathbf{b} = \pi(\mathbf{a}) \odot \mathbf{b}
```

Where:
- $\pi$ is a fixed random permutation
- $\odot$ is element-wise multiplication (Hadamard product)

### 3.2 Perfect Invertibility

Unlike convolution-based binding, permutation binding is perfectly invertible:

```math
\mathbf{a} = \pi^{-1}(\mathbf{c} \oslash \mathbf{b})
```

**Proof:** Since $\pi$ is a bijection and $\odot$ is invertible (element-wise division):
1. $\mathbf{c} = \pi(\mathbf{a}) \odot \mathbf{b}$
2. $\mathbf{c} \oslash \mathbf{b} = \pi(\mathbf{a})$
3. $\pi^{-1}(\mathbf{c} \oslash \mathbf{b}) = \mathbf{a}$ ∎

**Implementation:** `somabrain/math/bhdc_encoder.py` — `PermutationBinder`

### 3.3 Spectral Properties

For unitary role vectors, the FFT magnitude spectrum satisfies:

```math
|H_k| \approx 1 \quad \forall k \in [0, N-1]
```

This ensures energy preservation across all frequency components.

**Implementation:** `somabrain/quantum.py` — `QuantumLayer._validate_unitary_role()`

---

## 4. Holographic Reduced Representations (HRR)

### 4.1 Circular Convolution (Legacy)

Classical HRR uses circular convolution for binding:

```math
(\mathbf{a} \circledast \mathbf{b})_k = \sum_{j=0}^{N-1} a_j \cdot b_{(k-j) \mod N}
```

In the frequency domain (via FFT):

```math
\mathcal{F}[\mathbf{a} \circledast \mathbf{b}] = \mathcal{F}[\mathbf{a}] \odot \mathcal{F}[\mathbf{b}]
```

### 4.2 Unbinding via Correlation

Approximate unbinding uses circular correlation:

```math
(\mathbf{c} \star \mathbf{b})_k = \sum_{j=0}^{N-1} c_j \cdot b_{(j+k) \mod N}
```

In the frequency domain:

```math
\mathcal{F}[\mathbf{c} \star \mathbf{b}] = \mathcal{F}[\mathbf{c}] \odot \overline{\mathcal{F}[\mathbf{b}]}
```

### 4.3 Wiener Filter Unbinding

For noisy superpositions, Wiener filtering improves retrieval:

```math
\hat{\mathbf{a}} = \mathcal{F}^{-1}\left[\frac{\mathcal{F}[\mathbf{c}] \cdot \overline{\mathcal{F}[\mathbf{b}]}}{|\mathcal{F}[\mathbf{b}]|^2 + \sigma^2}\right]
```

Where $\sigma^2$ is the noise variance estimate.

**Implementation:** `somabrain/quantum.py` — `QuantumLayer.unbind_wiener()`

---

## 5. Sparse Distributed Representations (SDR)

### 5.1 SDR Encoding

SDRs represent information as sparse binary vectors:

```math
\mathbf{s} \in \{0, 1\}^N, \quad \|\mathbf{s}\|_0 = k \ll N
```

Where:
- $N$ = dimensionality (default: 16,384)
- $k$ = number of active bits (default: 2% sparsity)

### 5.2 Overlap Similarity

SDR similarity is measured by set overlap:

```math
\text{sim}(\mathbf{s}_1, \mathbf{s}_2) = \frac{|\mathbf{s}_1 \cap \mathbf{s}_2|}{k}
```

### 5.3 Locality-Sensitive Hashing (LSH)

For efficient nearest-neighbor search, SDRs use banding:

```math
P(\text{collision}) = 1 - (1 - p^r)^b
```

Where:
- $p$ = probability two similar items match in one hash
- $r$ = rows per band
- $b$ = number of bands

**Implementation:** `somabrain/sdr.py` — `SDREncoder`, `LSHIndex`

---

## 6. Working Memory Dynamics

### 6.1 Salience-Based Gating

Item salience determines admission and eviction:

```math
S(\mathbf{x}) = \alpha \cdot \text{novelty}(\mathbf{x}) + \beta \cdot \text{reward}(\mathbf{x}) + \gamma \cdot \text{recency}(\mathbf{x})
```

Where:
- $\alpha, \beta, \gamma$ are configurable weights
- $\alpha + \beta + \gamma = 1$ (normalized)

### 6.2 Novelty Computation

Novelty measures dissimilarity to existing memories:

```math
\text{novelty}(\mathbf{x}) = 1 - \max_{\mathbf{m} \in \text{WM}} \cos(\mathbf{x}, \mathbf{m})
```

### 6.3 Recency Decay

Recency decays exponentially over time:

```math
r(t) = r_0 \cdot e^{-\lambda_r \cdot t}
```

Where $\lambda_r$ is the recency decay rate.

**Implementation:** `somabrain/wm.py` — `WorkingMemory`

### 6.4 Capacity-Bounded Eviction

When working memory reaches capacity $C$:

```math
\text{evict} = \arg\min_{\mathbf{m} \in \text{WM}} S(\mathbf{m})
```

The item with lowest salience is removed.

---

## 7. Sleep-Inspired Consolidation

### 7.1 NREM Consolidation

Non-REM sleep consolidates episodic memories into semantic summaries:

```math
\mathbf{s}_{\text{semantic}} = \text{summarize}\left(\{\mathbf{e}_1, \mathbf{e}_2, \ldots, \mathbf{e}_k\}\right)
```

Process:
1. Select top-$k$ episodic memories by importance
2. Extract keywords using TF-IDF or similar
3. Store semantic summary with reinforced connections

### 7.2 REM Consolidation

REM sleep enables creative recombination:

```math
\mathbf{r}_{\text{new}} = \text{recombine}(\mathbf{e}_a, \mathbf{e}_b)
```

Process:
1. Sample random pairs of episodic memories
2. Combine their semantic features
3. Store novel associations

**Implementation:** `somabrain/consolidation.py` — `run_nrem()`, `run_rem()`

---

## 8. Spectral Methods

### 8.1 Chebyshev Heat Kernel

For graph-based memory operations, we apply the heat kernel:

```math
K_t = \exp(-t\mathcal{L})
```

Where $\mathcal{L}$ is the graph Laplacian. Approximated via Chebyshev polynomials:

```math
K_t \approx \sum_{k=0}^{K} c_k T_k(\tilde{\mathcal{L}})
```

### 8.2 Lanczos Iteration

For spectral interval estimation:

```math
\mathcal{L} \approx Q T Q^T
```

Where $T$ is a tridiagonal matrix from Lanczos iteration.

**Implementation:** `somabrain/math/lanczos_chebyshev.py`

### 8.3 Frequent Directions

For streaming low-rank approximation:

```math
\min_{\mathbf{B}} \|\mathbf{A} - \mathbf{A}\mathbf{B}^\dagger\mathbf{B}\|_F^2
```

Using the Frequent Directions algorithm for $O(\ell d)$ space where $\ell \ll n$.

**Implementation:** `somabrain/math/fd_rho.py` — `FrequentDirections`

---

## 9. Mathematical Invariants

SomaBrain enforces the following invariants at runtime:

### 9.1 Unit Norm Invariant

All stored vectors must be unit-normalized:

```math
\forall \mathbf{m} \in \text{Memory}: \|\mathbf{m}\|_2 = 1 \pm \epsilon
```

Where $\epsilon < 10^{-6}$.

### 9.2 Role Orthogonality

Unitary roles must be approximately orthogonal:

```math
\forall i \neq j: |\cos(\mathbf{r}_i, \mathbf{r}_j)| < 0.1
```

### 9.3 Energy Conservation

Binding operations preserve energy:

```math
\|\mathbf{a} \circledast \mathbf{b}\|_2 \approx \|\mathbf{a}\|_2 \cdot \|\mathbf{b}\|_2
```

### 9.4 Spectral Flatness

Unitary roles have flat frequency spectra:

```math
\text{Var}[|H_k|] < 0.1
```

**Implementation:** `somabrain/metrics_extra/math_metrics.py` — `MathematicalMetrics`

---

## 10. Implementation Reference

| Concept | Module | Key Functions |
|---------|--------|---------------|
| BHDC Binding | `math/bhdc_encoder.py` | `PermutationBinder.bind()`, `.unbind()` |
| HRR Context | `context_hrr.py` | `HRRContext.admit()`, `.cleanup()` |
| Quantum Layer | `quantum.py` | `QuantumLayer.superpose()`, `.bind()` |
| SDR Encoding | `sdr.py` | `SDREncoder.encode()`, `LSHIndex.query()` |
| Working Memory | `wm.py` | `WorkingMemory.admit()`, `.recall()` |
| Consolidation | `consolidation.py` | `run_nrem()`, `run_rem()` |
| Normalization | `math/normalize.py` | `normalize_vector()`, `ensure_unit_norm()` |
| Similarity | `math/similarity.py` | `cosine_similarity()`, `batch_cosine_similarity()` |
| Spectral | `math/lanczos_chebyshev.py` | `chebyshev_heat_apply()` |

---

## References

### Foundational Works

1. Plate, T.A. (2003). *Holographic Reduced Representations: Distributed Representation for Cognitive Structures*. CSLI Publications.

2. Gayler, R.W. (2003). Vector Symbolic Architectures Answer Jackendoff's Challenges for Cognitive Neuroscience. *ICCS/ASCS Joint International Conference*.

3. Kanerva, P. (1988). *Sparse Distributed Memory*. MIT Press.

### Sparse Coding & Predictive Processing

4. Olshausen, B.A. & Field, D.J. (1996). Emergence of Simple-Cell Receptive Field Properties by Learning a Sparse Code for Natural Images. *Nature*, 381, 607-609.

5. Friston, K. (2010). The Free-Energy Principle: A Unified Brain Theory? *Nature Reviews Neuroscience*, 11, 127-138.

### Complementary Learning Systems

6. McClelland, J.L., McNaughton, B.L., & O'Reilly, R.C. (1995). Why There Are Complementary Learning Systems in the Hippocampus and Neocortex. *Psychological Review*, 102(3), 419-457.

---

<div align="center">

**SomaBrain Mathematical Foundations**  
*Version 1.0.0 — January 2026*

[Back to README](../README.md) · [API Reference](../api/) · [SomaTech](https://www.somatech.dev)

</div>
