# Governing Memory Dynamics (GMD): A Truthful Mathematical Framework for Agentic High‑Dimensional Memory

**SomaBrain MathCore – Agentic Formulation**
**Version 4.4 (Mathematically Consistent Model)**
**Date:** February 2026
**Implementation Target:** Deterministic Rust Runtime

---

# 0. Mathematical Model (Single Source of Truth)

This document defines one precise representation so every theorem is internally consistent and suitable for deterministic agentic execution.

## 0.1 Sparse Encoding Model

Let raw sparse vectors be

s ∈ {0,1}^D  with iid Bernoulli(p) entries (or exact K=pD hot).

We define the standardized representation used everywhere in the system:

x = (s − p) / sqrt(p(1−p))

Properties:

E[x_i] = 0
Var(x_i) = 1
Coordinates are bounded and sub‑Gaussian.

This removes scale dependence from sparsity and makes all similarity math stable.

---

## 0.2 Similarity Definition

Similarity is defined as a normalized dot product:

sim(x,y) = (1/D) x^T y

Because ||x|| ≈ sqrt(D), this behaves like cosine similarity but is cheaper and deterministic.

---

## 0.3 Binding Operator

Binding is element‑wise multiplication on standardized vectors:

b = k ⊙ v

Unbinding uses the same operator.

---

## 0.4 Memory Update Rule

Memory evolves via exponential decay:

m_t = (1 − η) m_{t−1} + η b_t

Unrolled form:

m_t = Σ_{i=0..∞} w_i b_{t−i}

with weights

w_i = η (1 − η)^i

---

# 1. Sparse Encoding and Collision Behaviour

## Theorem 1 — Concentration of Similarity

Let x and y be independent standardized sparse vectors defined above.

Then:

E[ sim(x,y) ] = 0

Var( sim(x,y) ) = 1/D

and the tail probability satisfies

P(|sim(x,y)| > τ) ≤ 2 exp( −c D τ^2 )

for some constant c ≈ 1/2 depending on boundedness assumptions.

### Consequence

After proper centering and variance normalization, sparsity p does NOT directly control collision probability. Dimension D controls distinguishability.

### Practical Interpretation

Parameter p should therefore be chosen for:

• computational efficiency
• quantization stability
• binding robustness

rather than for collision suppression.

---

# 2. Bayesian Memory Dynamics and Signal‑to‑Noise Ratio

## 2.1 Weight Energy

Weights are

w_L = η (1 − η)^L

Total squared weight energy is

W2 = Σ w_i^2 = η^2 / (2η − η^2)

This is exact.

---

## Theorem 2 — Lag‑Dependent SNR

Consider recalling item inserted at lag L.

Unbinding gives:

u_L = k_{t−L} ⊙ m_t
= w_L v_{t−L} + Σ_{i≠L} w_i noise_i

Signal amplitude ∝ w_L

Noise variance ∝ (W2 − w_L^2)

A truthful SNR scaling is therefore

SNR(L) ≈ D · w_L^2 / (W2 − w_L^2)

where D appears because signal power grows linearly with dimension while noise grows sub‑linearly.

---

## 2.2 Agentic Memory Horizon

Define a minimum acceptable SNR_min.

The usable recall horizon L* satisfies

SNR(L*) ≥ SNR_min

This replaces fixed "capacity" with a truthful age‑dependent recall boundary.

---

# 3. Quantization‑Aware Unbinding

## 3.1 Quantization Model

Assume 8‑bit symmetric quantization with step

Δ = 2 / 255

Noise model:

ε ~ Uniform[−Δ, Δ]

Variance:

σ_ε^2 = Δ^2 / 12 ≈ 5.126 × 10⁻⁶

---

## Theorem 3 — Optimal Ridge Regularizer

Observation model per dimension:

y = k v + ε

Assume value prior variance σ_v^2.

The linear minimum‑MSE estimator yields ridge parameter

λ* = σ_ε^2 / σ_v^2

Unbinding rule:

v̂ = ( Q(b) ⊙ k ) / ( k² + λ* )

### Important Truth

The optimal λ depends on VALUE variance — not key energy.

If values are standardized (σ_v^2 = 1):

λ* ≈ 5.13 × 10⁻⁶

If values retain sparse variance p(1−p):

λ* ≈ 5.126×10⁻⁶ / (p(1−p))

For p = 0.1:

λ* ≈ 5.70 × 10⁻⁵

---

# 4. Orthogonal Mixing via Fast Walsh‑Hadamard Transform

## Theorem 4 — Deterministic Orthogonal Rotation

FWHT applies an exact orthogonal transform with complexity

Operations ≈ D log2(D)

(+ D multiplications if normalization is applied).

For D = 2048:

Add/Sub operations = 2048 × 11 = 22,528
Normalization mults ≈ 2,048

Total ≈ 24,576 operations.

---

## Agentic Interpretation

Dense orthogonal matrix multiplication costs O(D²).

FWHT therefore provides a practical speedup of hundreds× while remaining deterministic and memory‑safe.

---

# 5. Final Parameter Recommendations (Agentic Formulation)

| Parameter     | Value       | Mathematical Role                          |
| ------------- | ----------- | ------------------------------------------ |
| Dimension D   | 2048        | Controls similarity concentration          |
| Sparsity p    | 0.1         | Compute + quantization stability           |
| Decay η       | 0.05–0.08   | Defines weight spectrum and memory horizon |
| Regularizer λ | σ_ε² / σ_v² | Optimal quantization ridge                 |
| Mixing        | FWHT        | Deterministic orthogonalization            |

---

# 6. Summary of Truthful Properties

1. Collision probability depends primarily on D after standardization.
2. Memory recall is fundamentally age‑dependent via exponential weights.
3. Quantization regularization is determined by noise‑to‑signal variance ratio.
4. FWHT provides deterministic orthogonal mixing at O(D log D) cost.

This formulation removes ambiguous scaling factors and ensures that every equation corresponds directly to executable agentic behaviour.