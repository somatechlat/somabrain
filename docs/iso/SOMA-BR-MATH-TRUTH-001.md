# SOMA-BR-MATH-TRUTH-001: Mathematical Specification As Implemented

> **Standard:** ISO/IEC/IEEE 12207 / ISO 9001 document control — software product technical documentation
> **Owner:** SomaTech Engineering
> **Authority:** CODE IS SOURCE OF TRUTH. This document is extracted from production source. If any paper, proof report, or white paper disagrees with the cited line ranges here, the paper is wrong.

---

## 0. Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Mathematical Specification As Implemented |
| Document Identifier | SOMA-BR-MATH-TRUTH-001 |
| Version | 1.0.0 |
| Date | 2026-09-28 |
| Status | Released |
| Author | SomaTech Engineering (DOC-A2 extraction) |
| Approver | Engineering Lead |
| Classification | Internal |
| Source of truth | Production source under `rust_core/src/` and `somabrain/` |
| Supersedes | (none) |
| Non-authoritative sources | `LEARNING_MATHEMATICAL_PROOF.md`, `SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md` (see Appendix A) |
| Next Review | On any change to a cited file:line range |

### Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | Engineering | Initial extraction of equations, symbols, constants, and invariants from production code only. False-claims appendix for legacy proof docs. |
| 1.1.0 | 2026-10-05 | Engineering | W2 neuromodulation: one store (`runtime/neuromodulators.py`; admin tree deleted), homeostatic law `m ← Π(m+η(δ−m))`, shared ACh/5-HT target laws, 5-HT gate consumer, Supervisor wired on `/act`, Rust ODE deleted. T32 DELETED, T33/T35 rewritten, T35b added. |

### Scope Files (read in full)

| Path | Role |
|---|---|
| `rust_core/src/mathcore.rs` | GMD mathcore: FWHT, quantization, Wiener, BayesianMemory, softmax/entropy |
| `rust_core/src/bhdc.rs` | BHDC encoder, permutation binder, quantum state |
| `rust_core/src/neuro.rs` | Neuromodulators ODE, Amygdala gate |
| `rust_core/src/prediction.rs` | Predictors, consolidation |
| `rust_core/src/adaptation.rs` | Adaptation engine, tau annealing, TD learning |
| `somabrain/math/*.py` | Canonical normalize/similarity, Sinkhorn, FD, Lanczos/Chebyshev, APPR, BHDC bridge |
| `somabrain/admin/core/learning/{math,prediction,salience,scoring}.py` | Learning math surface, predictors, FD salience, unified scorer |
| `somabrain/admin/core/{quantum,quantum_pure,context_hrr,sdr,numerics}.py` | HRR/BHDC layer, pure HRR (test-only), HRR context, SDR/LSH, numeric primitives |
| `somabrain/learning/adaptation/engine.py`, `somabrain/learning/annealing.py`, `somabrain/learning/config.py` | Python adaptation engine, tau annealing/entropy, config dataclasses |
| `somabrain/runtime/neuromodulators.py`, `somabrain/admin/cognitive/amygdala.py`, `somabrain/runtime/supervisor.py`, `somabrain/adaptive/core.py` | THE neuromodulator store, adaptive homeostatic feedback, amygdala salience, free-energy supervisor |
| `somabrain/memory/scoring.py`, `somabrain/memory/wm/wm_salience.py`, `somabrain/context/builder.py` | Recall ranking/recency, WM salience, retrieval weight softmax |
| `somabrain/calibration/temperature_scaling.py` | Temperature scaling, ECE, Brier |
| `somabrain/predictors/base.py` | Heat-diffusion predictor |

### Status Taxonomy (used on every equation)

| Tag | Meaning |
|---|---|
| **LIVE** | Executed by production call paths reachable from in-scope modules |
| **LIVE-FALLBACK** | Executed only when the preferred backend (typically Rust `somabrain_rs`) is unavailable |
| **TEST-ONLY** | Module or symbol is documented/enforced as test-only; not for production services |
| **EXPORTED** | Exposed through the PyO3 ABI (`somabrain_rs`) but no in-scope production caller was found |
| **DEAD-STUB** | Body is a placeholder / constant return; no real math is performed |
| **DOC-DRIFT** | Function exists and is live, but its own docstring/comments state a different formula than the code |

Line ranges are inclusive and refer to the file as read at extraction time.

---

## 1. Symbols Table

| Symbol | Domain / meaning | Default (as coded) | file:line |
|---|---|---|---|
| `D`, `dim`, `n` | hypervector dimension | `SOMABRAIN_HRR_DIM` via `HRRConfig` | `somabrain/admin/core/quantum.py:67-68`; `rust_core/src/mathcore.rs:372` |
| `p`, `sparsity` | active-dimension fraction | `0.1` (`SOMABRAIN_BHDC_SPARSITY`) | `somabrain/settings/cognitive.py:264`; `rust_core/src/bhdc.rs:69` |
| `active_count` | `round(p·D)` active bits | clamped to `[1, D]` | `rust_core/src/bhdc.rs:69,76`; `somabrain/math/bhdc_encoder.py:21-23` |
| `λ`, `lambda`, `lambda_reg` | Wiener ridge regularizer | `compute_wiener_lambda(p, 8)` at production `p` (≈ `5.696e-5` at `p=0.1`); single source everywhere | `rust_core/src/mathcore.rs` (`compute_wiener_lambda`); `somabrain/math/bhdc_encoder.py` (`compute_wiener_lambda`, `production_wiener_lambda`); consumed by `rust_core/src/bhdc.rs`, `somabrain/admin/core/quantum.py`, `somabrain/brain_settings/models.py` (`gmd_lambda_reg`) |
| `Δ` | quantization step on `[-1,1]` | `2/(2^bits − 1)` (`2/255` at 8-bit) | `rust_core/src/mathcore.rs` (`compute_wiener_lambda`, `quantize_8bit`) |
| `η`, `eta` | BayesianMemory learning rate | clamped `[0.01, 0.5]`; `gmd_eta` default `0.08` | `rust_core/src/mathcore.rs:377`; `somabrain/brain_settings/models.py:225-231` |
| `α`, `alpha` | retrieval semantic weight | `1.0` | `somabrain/settings/cognitive.py:178`; `rust_core/src/adaptation.rs:24` |
| `β`, `beta` | retrieval graph weight | `0.2` | `somabrain/settings/cognitive.py:179`; `rust_core/src/adaptation.rs:24` |
| `γ`, `gamma` | retrieval temporal weight | `0.1` | `somabrain/settings/cognitive.py:180`; `rust_core/src/adaptation.rs:24` |
| `τ`, `tau` | retrieval temperature | `0.7` | `somabrain/settings/cognitive.py:181`; `rust_core/src/adaptation.rs:24` |
| `λ_u`, `lambda_` | utility primary weight | `1.0` | `somabrain/learning/config.py:29-31`; `rust_core/src/adaptation.rs:62` |
| `μ`, `mu` | utility secondary weight | `0.1` | `somabrain/learning/config.py:32-34`; `rust_core/src/adaptation.rs:62` |
| `ν`, `nu` | utility tertiary weight | `0.05` | `somabrain/learning/config.py:35-37`; `rust_core/src/adaptation.rs:62` |
| `lr`, `learning_rate` | adaptation step size | `0.05` (`adapt_lr`) | `somabrain/brain_settings/models.py:232-238`; `rust_core/src/adaptation.rs:105` |
| `gain_α…gain_ν` | per-parameter gains | `1.0, -0.5, 1.0, -0.25, -0.25` | `somabrain/learning/config.py:76-90`; `rust_core/src/adaptation.rs:118-122` (Rust defaults `0.1, 0.05, 0.1, 0.05, 0.02`) |
| `w_cosine`, `w_fd`, `w_recency` | unified scorer weights | `0.6`, `0.25`, `0.15` | `somabrain/settings/cognitive.py:170-172` |
| `w_novelty`, `w_error`, `w_fd` | salience weights | constructor; dense defaults `0.6`, `0.4`, `0.0` | `somabrain/admin/core/learning/salience.py:30-32`; `somabrain/admin/cognitive/amygdala.py:66-74` |
| `m = (m₁…m₄)` | dopamine, serotonin, noradrenaline, acetylcholine | see §4 | `somabrain/runtime/neuromodulators.py` (`NeuromodState`); bounds `somabrain/math/contracts.py` (`NEURO_BOUNDS`) |
| `k_d`, `k_r`, `bias`, `u_scale` | neuromod dynamics coefficients | **DELETED** (W2.6 / DEBT-007) | formerly `rust_core/src/neuro.rs`; no dynamics remain in Rust |
| `ε`, `_EPS`, `tiny` | numerical floor | `1e-12` (Python math), `1e-10` (Rust), `1e-6`/`1e-12` (numerics dtype) | see §4 |
| `K` | Chebyshev degree | `24` default; `30` in `PredictorConfig` | `somabrain/math/graph_heat.py:31`; `somabrain/predictors/base.py:52` |
| `m_L`, `lanczos_m` | Lanczos steps | `16`/`20`/`32` by call site | `somabrain/math/lanczos_chebyshev.py:18`; `somabrain/math/graph_heat.py:33,38` |
| `t`, `diffusion_t` | heat diffusion time | `0.5` | `somabrain/predictors/base.py:50` |
| `α_ppr` | APPR teleport | `0.85` | `somabrain/math/appr.py:18` |
| `eps_ot` | Sinkhorn entropy regularization | `1e-2` | `somabrain/math/sinkhorn.py:16` |
| `φ` | golden-section ratio | `(√5−1)/2` | `somabrain/calibration/temperature_scaling.py:68` |
| `T_cal` | calibration temperature | fitted; clamp `[0.05, 10]` | `somabrain/calibration/temperature_scaling.py:89` |
| `b` | quantization bits | honored: `Δ = 2/(2^b − 1)` in `compute_wiener_lambda` | `rust_core/src/mathcore.rs` (`compute_wiener_lambda`); `somabrain/math/bhdc_encoder.py` (`compute_wiener_lambda`) |
| `H` | Shannon entropy of weight distribution | natural log, linear-normalized probs | `rust_core/src/mathcore.rs:218-223`; `somabrain/learning/annealing.py:325` |
| `S` | Frequent-Directions sketch matrix | `0 × d` init | `somabrain/math/fd_rho.py:26` |
| `ℓ` | FD sketch rank | constructor arg | `somabrain/math/fd_rho.py:21-24` |

---

## 2. Equations As Implemented

Numbering is `(T1), (T2), …` grouped by subsystem. Every equation cites an exact line range and a live/dead status.

### 2.1 Binding / Hyperdimensional Encoding

**(T1) FWHT — in-place Walsh–Hadamard, orthonormal scale**
```
h ← 1
while h < n:
  for i in 0..n step 2h:
    for j in i..i+h:
      (v[j], v[j+h]) ← (v[j]+v[j+h], v[j]−v[j+h])
  h ← 2h
v ← v / √n          # only if n is a power of 2; else RAISE ValueError
```
- **file:line** `rust_core/src/mathcore.rs` (`fwht`, `fwht_inplace`); Python mirror `somabrain/math/bhdc_encoder.py` (`fwht`)
- **Status:** LIVE (used by `PermutationBinder` when `mix == "hadamard"`, `rust_core/src/bhdc.rs`)
- **Note (FIXED, W4.4):** Non-power-of-two `n` **raises `ValueError`** in both languages. `PermutationBinder` with `mix="hadamard"` validates `dim` at construction and raises `ValueError` for non-2^r `dim`. The former silent no-op is gone.

**(T2) BHDC active count**
```
active = max(1, min(D, round(sparsity · D)))
```
- **file:line** `rust_core/src/bhdc.rs:69,76`; Python mirror `somabrain/math/bhdc_encoder.py:21-23`
- **Status:** LIVE

**(T3) Sparse hypervector generation (Rust)**
```
Fisher–Yates select `active` indices
if binary_mode == "zero_one":  v[idx] = +1 for active, else 0;  v ← v − mean(v)
else (pm_one):                 v[idx] ∈ {−1,+1} for active, else 0   (zeros on inactive)
```
- **file:line** `rust_core/src/bhdc.rs:166-195`
- **Status:** LIVE
- **DOC-DRIFT vs Python fallback (T3b):** Python `_PythonBHDCEngine._render_sparse_vector` sets inactive entries to `−1.0` in `pm_one` mode (`somabrain/math/bhdc_encoder.py:63-66`), not `0.0`. **The Rust and Python-fallback vectors are not the same distribution.**

**(T3b) Sparse hypervector generation (Python fallback)**
```
pm_one:     v = −1 everywhere;  v[active] = +1
zero_one:   v = 0 everywhere;   v[active] = +1;  v ← v − mean(v)
```
- **file:line** `somabrain/math/bhdc_encoder.py:59-71`
- **Status:** LIVE-FALLBACK

**(T4) Seed bundle (Rust)**
```
bundle_seed = u64_le(SHA256(label ‖ le64(base_seed) ‖ extra_seed ‖ tenant_id ‖ model_version)[0:8])
key_seed    = u64_le(SHA256(key)[0:8]) ⊕ bundle_seed
```
- **file:line** `rust_core/src/bhdc.rs:14-31,34-40,87-90`
- **Status:** LIVE
- **DOC-DRIFT vs Python fallback (T4b):** Python composes `SHA256("base|extra|tenant|model|key")[0:8]` (`somabrain/math/bhdc_encoder.py:49-57,141-151`) — **different hash input, different vectors for the same key.**

**(T4b) Seed composition (Python fallback)**
```
seed = u64_le(SHA256(f"{base_seed}|{extra}|{tenant}|{model}|{key}")[0:8])
```
- **file:line** `somabrain/math/bhdc_encoder.py:49-57,141-151`
- **Status:** LIVE-FALLBACK

**(T5) BHDC elementwise bind / unbind / bundle**
```
bind(a,b)_i   = a_i · b_i
unbind(a,b)_i = a_i / (|b_i| + 1e-8) · signum(b_i)
bundle({v_k}) = normalize( Σ_k v_k )     # L2, skip if ‖·‖ ≤ 1e-10
```
- **file:line** `rust_core/src/bhdc.rs:111-141`
- **Status:** EXPORTED (`BHDCEncoder.bind/unbind/bundle` PyO3 methods). Production `QuantumLayer` does **not** call these; it uses FFT bind (T8) and `PermutationBinder` for unitary roles.

**(T6) PermutationBinder bind**
```
b′ = π(b)                      # fixed random permutation
c  = a ⊙ b′
if mix == "hadamard": c ← FWHT(c)
c  = c / ‖c‖                   # L2 if ‖c‖ > 1e-10
```
- **file:line** `rust_core/src/bhdc.rs:252-268` (perm at `218-241`, `apply_perm` at `334-336`)
- **Status:** LIVE (via `QuantumLayer.bind_unitary`, `somabrain/admin/core/quantum.py:374-406`)

**(T7) PermutationBinder unbind (Wiener-regularized)**
```
if mix == "hadamard": c ← FWHT(c)        # H is self-inverse
b′ = π(b)
v̂_i = (c_i · b′_i) / (b′_i² + λ)        # λ = lambda_reg = λ*(p) = Δ²/(12p(1−p))
v̂  = v̂ / ‖v̂‖                             # if ‖v̂‖ > 1e-10
```
- **file:line** `rust_core/src/bhdc.rs` (`PermutationBinder::unbind`)
- **Status:** LIVE (via `QuantumLayer.unbind_exact_unitary`, `somabrain/admin/core/quantum.py`)
- **Note (FIXED, W4.1):** λ defaults to `compute_wiener_lambda(p, 8)` evaluated at the production sparsity `p` (`SOMABRAIN_BHDC_SPARSITY`, engineering choice 0.1). No hardcoded regularizer constant remains.

**(T7b) PermutationBinder unbind (Python fallback, Wiener)**
```
if mix == "hadamard": c ← FWHT(c)        # same transform as T1
b′ = π(b)
v̂_i = (c_i · b′_i) / (b′_i² + λ)        # identical rule to T7
v̂  = v̂ / ‖v̂‖                             # if ‖v̂‖ > 1e-10
```
- **file:line** `somabrain/math/bhdc_encoder.py` (`_PythonPermutationBinder.unbind`)
- **Status:** LIVE-FALLBACK (FIXED, W4.3/DEBT-015/DEBT-016)
- **Note:** The former plain division `c / π(b)` with a ±1e-12 floor is deleted. Python fallback bind also applies FWHT when `mix == "hadamard"` and L2-normalizes like the Rust path.

**(T8) `QuantumLayer.bind` — FFT circular convolution**
```
c = irfft( rfft(a) · rfft(b), n=D )     # complex128 product
c = normalize_array(c)                  # if cfg.renorm
```
- **file:line** `somabrain/admin/core/quantum.py:238-281` (core at `254-259`)
- **Status:** LIVE
- **DOC-DRIFT:** Class docstring claims "Binary/sparse hypervectors with permutation binding replace legacy FFT" (`quantum.py:1-12`) and `bind` docstring says "classic HRR". The **code** is classic HRR FFT convolution, not BHDC permutation binding. `bind_unitary` (T6) is the permutation path.

**(T9) `QuantumLayer.unbind` — spectral Wiener division**
```
fc = rfft(c);  fb = rfft(b)
λ  = BrainSetting("gmd_lambda_reg") or production_wiener_lambda()
fa = fc · conj(fb) / (|fb|² + λ)
a  = irfft(fa, n=D);  a = normalize_array(a)
```
- **file:line** `somabrain/admin/core/quantum.py` (`QuantumLayer.unbind`)
- **Status:** LIVE
- **Note (FIXED, W4.1):** The former `1e-4` fallback is deleted; both the BrainSetting default (`gmd_lambda_reg`) and the fallback come from `compute_wiener_lambda(p, 8)` at the production sparsity.
- **Note:** Docstring claims `unbind(bind(a,b),b) ≈ a` with "similarity > 0.95" — that threshold is **not** enforced anywhere in this function.

**(T10) Pure HRR bind / unbind (test-only)**
```
bind:   c = irfft( rfft(a)·rfft(b), n=D );  c = normalize_array(c)
unbind: fa = rfft(c) / rfft(b)              # raises ZeroDivisionError if any bin == 0
        a  = irfft(fa, n=D);  a = normalize_array(a)
```
- **file:line** `somabrain/admin/core/quantum_pure.py:121-161`
- **Status:** TEST-ONLY (module contract: "This module is test-only. Do NOT use `PureQuantumLayer` in production", `quantum_pure.py:14-16`)

**(T11) BNDC-style 8-bit quantization `Q(x)`**
```
Q(x) = ( clamp(round((x+1)/2 · 255), 0, 255) / 255 ) · 2 − 1
```
- **file:line** `rust_core/src/mathcore.rs:338-344` (vector map at `348-350`)
- **Status:** EXPORTED (`quantize_8bit`, `quantize_vector`)

**(T12) Optimal sparsity `p*` — DELETED (no theorem)**
```
(no exported function)
p = 0.1 is an ENGINEERING CHOICE (SOMABRAIN_BHDC_SPARSITY default),
not the output of a sparsity theorem.
```
- **Status:** DELETED (FIXED, W4.2 / DEBT-012). The former `compute_optimal_p` implemented `(1 + √clamp(δ, 1e-4, 1−1e-4)) / 2`, which is **always ≥ 0.5** and never recommended the production `p = 0.1`. The formula and the "p* ≈ 0.1" claim were both removed. No false theorem is asserted.

**(T13) Wiener ridge `λ*`**
```
Δ = 2/(2^bits − 1)                # 2/255 at bits=8; `bits` is honored
σ_ε² = Δ² / 12
σ_v² = clamp(p, 0.01, 0.99) · (1 − clamp(p, 0.01, 0.99))
λ*   = σ_ε² / σ_v²                # = Δ² / (12 p (1−p)) ≈ 5.126e-6 / (p(1−p)) at 8-bit
```
- **file:line** `rust_core/src/mathcore.rs` (`compute_wiener_lambda`, `production_wiener_lambda`); Python mirror `somabrain/math/bhdc_encoder.py` (`compute_wiener_lambda`)
- **Status:** EXPORTED — **single source** of every default regularizer (W4.1 / DEBT-011 FIXED)
- **Note:** Defaults are evaluated at the production sparsity `p` (`PRODUCTION_SPARSITY_P = 0.1`, or caller-supplied `p`). At `p = 0.1`, `bits = 8`: `λ* ≈ 5.6958e-5`. The former binder default that equaled `λ*(p=0.5)` and the former `1e-4` quantum fallback are deleted.

**(T14) `ensure_binary`**
```
v_i = +1 if v_i ≥ 0 else −1
```
- **file:line** `rust_core/src/bhdc.rs:418-419`; Python `somabrain/math/bhdc_encoder.py:267-270`
- **Status:** EXPORTED / LIVE (exported surface)

### 2.2 Similarity and Normalization

**(T15) Cosine similarity (canonical Python)**
```
cos(a,b) = 0                                  if ‖a‖ ≤ ε or ‖b‖ ≤ ε
         = clip( (a·b) / (‖a‖ ‖b‖), −1, 1 )   otherwise
```
with `ε = 1e-12`, float64 intermediates.
- **file:line** `somabrain/math/similarity.py:34-93` (core `79-93`)
- **Status:** LIVE (single source of truth; used by `quantum.py:471-473`, `scoring.py:100-102`, `wm_salience.py:21`, `context/builder.py:21`, `quantum_pure.py:28`)

**(T16) Cosine error / distance**
```
cosine_error(a,b)    = clamp(1 − cos(a,b), 0, 1)     # opposite → 1
cosine_distance(a,b) = 1 − cos(a,b)                  # range [0, 2]
```
- **file:line** `somabrain/math/similarity.py:96-135`
- **Status:** LIVE (`cosine_error` used by `somabrain/admin/core/learning/prediction.py:45,92-97`)

**(T17) Batch cosine similarity**
```
s = clip( (C · q) / (‖C‖ ‖q‖), −1, 1 )   # zero-norm rows → 0
```
- **file:line** `somabrain/math/similarity.py:138-182`
- **Status:** LIVE (exported from `somabrain.math`)

**(T18) `normalize_vector`**
```
n = ‖v‖₂
if n ≤ ε:  return 0          # ε = 1e-12
else:      return (v / n).astype(dtype)   # default float32
```
- **file:line** `somabrain/math/normalize.py:37-87`
- **Status:** LIVE (used by `context_hrr.py:137-139`, `lanczos_chebyshev.py:27-35`)

**(T19) `normalize_batch` / `safe_normalize` / `ensure_unit_norm`**
```
normalize_batch:  row-wise T18 along axis, zero rows if ‖·‖ ≤ ε
safe_normalize:   (T18, original norm)
ensure_unit_norm: T18, but skip if |‖v‖ − 1| ≤ 1e-6
```
- **file:line** `somabrain/math/normalize.py:90-200`
- **Status:** LIVE (exported)

**(T20) `normalize_array` (legacy production normalizer)**
```
tiny_amp = max(strategy(D, dtype), TINY_MIN[dtype])
         strategy "sqrt":     eps·√D·scale
         strategy "linear":   eps·D·scale
         strategy "absolute": eps·scale
result = x / √(‖x‖² + tiny_amp²)
if ‖x‖² < tiny_amp²:
    mode "strict":      raise ValueError
    mode "legacy_zero": result ← 0
    mode "robust":      result ← baseline  (ones/√D)
result ← result / ‖result‖                # final unit-norm pass (float64)
non-finite entries ← baseline
```
- **file:line** `somabrain/admin/core/numerics.py:28-91` (tiny floor), `117-282` (normalize)
- **Status:** LIVE (used by `QuantumLayer._renorm`, `quantum.py:171-180`)
- **Note:** Default `mode="robust"`. Docstring of `normalize.py` claims it is "the ONLY implementation of vector normalization in the codebase" (`normalize.py:17-20`) — **false**; this module coexists and is the one used on the HRR path. See Appendix A.

**(T21) Rust cosine similarity**
```
cos(a,b) = 0                    if ‖a‖ < 1e-10 or ‖b‖ < 1e-10
         = (a·b)/(‖a‖‖b‖)       otherwise   (NO clamp to [−1,1])
```
- **file:line** `rust_core/src/mathcore.rs:245-257` (also `bhdc.rs:144-149`, `mathcore.rs:76-81` FNOM)
- **Status:** EXPORTED
- **Note:** No `clip` here, unlike T15. Different epsilon (`1e-10` vs `1e-12`).

**(T22) Tiny floor → spectral power floor**
```
power_per_bin = tiny_amp² / D
```
- **file:line** `somabrain/admin/core/numerics.py:339-358`
- **Status:** LIVE (utility for FFT paths)

### 2.3 Learning / Adaptation

**(T23) Weight update (Python engine)**
```
α ← clamp( α + lr · gain_α · semantic_signal , α_min, α_max )
γ ← clamp( γ + lr · gain_γ · semantic_signal , γ_min, γ_max )
λ ← clamp( λ + lr · gain_λ · utility_signal , λ_min, λ_max )
μ ← clamp( μ + lr · gain_μ · utility_signal , μ_min, μ_max )
ν ← clamp( ν + lr · gain_ν · utility_signal , ν_min, ν_max )
```
with `semantic_signal = reward if reward is not None else utility`, `utility_signal = reward if reward is not None else signal` (`engine.py:336-339`).
- **file:line** `somabrain/learning/adaptation/engine.py:364-391` (constrain at `441-449`; clamp bounds from `somabrain/learning/config.py:124-224`)
- **Status:** LIVE

**(T23b) Weight update (Rust engine)**
```
α ← clamp( α + lr · gain_α · reward , 0.1, 2.0 )
γ ← clamp( γ + lr · gain_γ · reward , 0.0, 1.0 )
λ ← clamp( λ + lr · gain_λ · utility , 0.1, 2.0 )
μ ← clamp( μ + lr · gain_μ · utility , 0.0, 0.5 )
ν ← clamp( ν + lr · gain_ν · utility , 0.0, 0.2 )
```
- **file:line** `rust_core/src/adaptation.rs:165-183` (bounds at `113-117`)
- **Status:** EXPORTED (`AdaptationEngine.apply_feedback`)
- **Note:** Bounds and gains **differ** from Python (T23). Rust `gain_*` defaults `0.1, 0.05, 0.1, 0.05, 0.02` (`adaptation.rs:118-122`) vs Python `1.0, −0.5, 1.0, −0.25, −0.25` (`config.py:76-90`). Not the same learner.

**(T24) Dynamic learning rate (dopamine-scaled)**
```
lr_scale = clamp(0.5 + dopamine, 0.5, 1.2)
lr       = base_lr · lr_scale
```
- **file:line** `somabrain/learning/adaptation/engine.py:350-362`; Rust `rust_core/src/adaptation.rs:230-233`
- **Status:** LIVE in Python only when `enable_dynamic_lr and gains == AdaptationGains.from_settings()` (`engine.py:353-355`); otherwise `lr = base_lr`. Rust version is EXPORTED.
- **Note (FIXED, W2.2 / DEBT-002):** `dopamine` is read from the process-wide store (`bootstrap.singletons.get_neuromodulators().get_state(tenant)`). The former per-call `PerTenantNeuromodulators()` construction (always empty ⇒ constant LR) is gone.

**(T25) Tau annealing (Python, multiplicative)**
```
if mode == "linear":                 τ ← τ · (1 − rate)
if mode ∈ {"exp","exponential"}:     τ ← τ                  # NO per-feedback anneal
if mode == "step" and (step+1) mod interval == 0:
                                     τ ← τ · (1 − rate)
τ ← max(τ_min, τ)                    # only if an anneal was applied
```
- **file:line** `somabrain/learning/annealing.py:169-220` (core `199-212`)
- **Status:** LIVE (called from `engine.py:402-408`)

**(T25b) Tau annealing (Rust `apply_tau_annealing`, additive-linear)**
```
"linear":      τ ← τ − rate
"exponential": τ ← τ · exp(−rate)
"step":        τ ← τ · (1 − rate)  if interval>0 ∧ step mod interval = 0 ∧ step>0
else:          τ ← τ
τ ← max(τ_min, τ)
```
- **file:line** `rust_core/src/adaptation.rs:241-262`
- **Status:** EXPORTED; also mirrored in Python `_rust_apply_tau_annealing` fallback `somabrain/learning/annealing.py:39-53`
- **CONFLICT:** `"linear"` is **subtractive** in Rust and **multiplicative** in (T25). `"exponential"` is a no-op per-feedback in Python (T25) and `τ·e^{−rate}` in Rust. These are not the same schedule.

**(T26) Tau decay (multiplicative, gated)**
```
if not enabled or rate ≤ 0 or was_annealed:  return τ
τ ← max(0.05, τ · (1 − tau_decay_rate))
```
- **file:line** `somabrain/learning/annealing.py:223-263` (core `242-254`)
- **Status:** LIVE
- **Note:** Floor `0.05` is hard-coded at `annealing.py:254`, while `get_annealing_config` default `tau_min` is also `0.05` (`annealing.py:102,108`) and Rust `set_tau` clamps to `[0.01, 10.0]` (`adaptation.rs:202`). Three different tau floors.

**(T27) Linear / exponential tau decay (closed form)**
```
linear:      τ(t) = max(τ_min, τ₀ − α·t)
exponential: τ(t) = τ₀ · exp(−γ·t)
```
- **file:line** Python `somabrain/learning/annealing.py:396-428`; Rust `rust_core/src/adaptation.rs:266-274`; engine wrappers `engine.py:604-610`, `adaptation.rs:185-191`
- **Status:** LIVE (utility API; not the same as T25/T26)

**(T28) Entropy cap + sharpening**
```
vec_i = max(1e-9, w_i)  for w ∈ {α, β, γ, τ}
p_i   = vec_i / Σ vec
H     = −Σ p_i · ln(p_i)                 # natural log, NOT log2, NOT softmax
if H ≤ cap: return unchanged
largest = argmax(vec)
repeat ≤ 10:  vec_i ← vec_i · sharpen_rate   ∀i ≠ largest     # default 0.8
if still H > cap:  vec_i ← vec_i · final_sharpen  ∀i ≠ largest # default 0.05
vec ← vec · (α+β+γ+τ) / Σ vec            # restore original magnitude
```
- **file:line** `somabrain/learning/annealing.py:292-390` (entropy via `_rust_compute_entropy` at `56-61`, `mathcore.rs:218-223`)
- **Status:** LIVE
- **Note:** Probs are **linear-normalized weights**, not softmax (contrast Appendix A claim). Second, independent implementation of the same idea lives in `somabrain/context/builder.py:383-440` with a **different** shrink schedule (`scale = min(0.99, max(0.2, overflow/(cap+1e-9)))`, final `×0.05`).

**(T29) Sutton TD helpers**
```
TD return:     G = R + γ_disc · V(s′)
TD error:      δ = R + γ_disc · V(s′) − V(s)
N-step return: G = R_t + γ_disc·(R_{t+1} + … + γ_disc·V(s_{t+n})…)
eligibility:   e ← e · (γ_disc · λ_e)
```
- **file:line** `rust_core/src/adaptation.rs:281-305`
- **Status:** EXPORTED (`compute_td_return`, `compute_td_error`, `compute_n_step_return`, `decay_eligibility`)

**(T30) Curriculum stage LR**
```
"easy": lr = clamp(base_lr · 1.2, 0.001, 1.0)
"hard": lr = clamp(base_lr · 0.5, 0.001, 1.0)
else:   lr = clamp(base_lr,       0.001, 1.0)
```
- **file:line** `somabrain/learning/adaptation/engine.py:532-541`
- **Status:** LIVE

**(T31) Error-driven tau (update_parameters)**
```
τ ← clamp( τ · (1 − 0.05 · error), 0.01, 10.0 )
```
- **file:line** `somabrain/learning/adaptation/engine.py:571-573`
- **Status:** LIVE

### 2.4 Neuromodulation

**Single store (W2 / DEBT-001 FIXED).** `somabrain/runtime/neuromodulators.py`
is the only implementation. `somabrain/admin/brain/neuromodulators.py` is
deleted. Every consumer — `/act` (`cognitive_loop_service.py`),
`/neuromod/*` (`api/endpoints/neuromod.py`), AdaptationEngine DA→LR
(`engine.py:_get_dopamine_level`), amygdala, Supervisor — goes through
`bootstrap.singletons.get_neuromodulators()` (or a directly constructed store
in tests).

**(T32) Neuromodulator dynamics — DELETED (W2.6 / DEBT-007).** The Rust ODE
```
ẋ_i = k_d[i] · x_i − k_r[i] · m_i + bias[i] + u_scale · u_i
m_i ← m_i + ẋ_i · dt
```
had no production caller (only `scripts/verify_rust_migration.py`). It is
deleted from `rust_core/src/neuro.rs`, together with `set_dynamics` /
`get_dynamics` and the `neuro_k_d_*` / `neuro_k_r_*` / `neuro_u_scale`
brain_settings keys. `Neuromodulators` in Rust is a pure state mirror
(`get_state`/`set_state`/`reset`); dynamics live in Python only.

**Bounds Π (single clamp table).** `somabrain.math.contracts.NEURO_BOUNDS`:
```
dopamine      ∈ [0.2, 0.8]
serotonin     ∈ [0.0, 1.0]
noradrenaline ∈ [0.0, 0.1]
acetylcholine ∈ [0.0, 0.1]
```
- **file:line** `somabrain/math/contracts.py` (`NEURO_BOUNDS`); projection
  `project` / `NeuromodState.clamped` in `somabrain/runtime/neuromodulators.py`
- **Status:** LIVE. `PerTenantNeuromodulators.set_state` and
  `Neuromodulators.set_state` store `state.clamped()` (Π at the store).

**(T33) Homeostatic update law (W2.3 / DEBT-004 FIXED)**
```
m_i ← Π( m_i + η_i (δ_i − m_i) )
```
`δ_i` is a *target level* in the modulator's bounds (not a velocity).
Implemented by `AdaptiveParameter.update` (`somabrain/adaptive/core.py`) and
by `Supervisor.adjust` (gain-limited, EWMA-smoothed variant of the same
mean-revert). Parameters can decrease on adverse evidence and cannot drift
monotonically into a bound.

**Target laws δ_i (shared pure functions in
`somabrain/runtime/neuromodulators.py`):**
```
δ_ACh = Π_ACh( 0.5·novelty + 0.3·pred_error + 0.2·memory_load )   # acetylcholine_target
δ_5HT = 1 − clamp(pred_error, 0, 1)                                # serotonin_target
δ_DA  = Π_DA ( clamp(success, 0, 1) )                              # dopamine_target
δ_NE  = Π_NE ( clamp(arousal, 0, 1) )                              # noradrenaline_target
```
Adaptive feedback wiring (`update_from_performance`):
```
success = success_rate + DOPAMINE_BIAS [+ DOPAMINE_REWARD_BOOST if task=="reward_learning"]
arousal = (1 / max(latency_floor, latency)) · LATENCY_SCALE + URGENCY_FACTOR·[task=="urgent"]
memory_load = MEMORY_FACTOR·[task=="memory"]
δ_DA  = dopamine_target(success)
δ_5HT = serotonin_target(error_rate)
δ_NE  = noradrenaline_target(arousal)
δ_ACh = acetylcholine_target(novelty, pred_error or error_rate, memory_load)
```
- **file:line** `somabrain/runtime/neuromodulators.py` (laws + `_calculate_*_feedback`);
  `somabrain/adaptive/core.py` (`AdaptiveParameter.update`)
- **Status:** LIVE

**ACh law (DEBT-005 FIXED).** ACh is **attention demand**. The same
`acetylcholine_target` is used by the adaptive path and by
`Supervisor.adjust`; given the same `(novelty, pred_error)` both move ACh in
the same direction (property-tested in
`tests/unit/test_neuromod_wiring.py::TestAChLaw`).

**5-HT law (DEBT-006 FIXED).** 5-HT is stability `1 − pred_error` and has a
real consumer: `AmygdalaSalience` gates (T35). No write-only modulator.

**(T34) Amygdala salience (dense + FD)**
```
w_err = clamp(dopamine, 0.2, 0.8)
s = w_novelty·novelty + w_error·pred_error
s ← s + (w_err − w_error)·pred_error
if method=="fd":
    residual, capture = FD.observe(wm_vector)
    fd_boost = w_fd · max(0, residual)
    if capture < fd_energy_floor:  fd_boost += w_fd·(fd_energy_floor − capture)
    s ← s + fd_boost
s ← s + acetylcholine          # ACh = attention demand raises salience
s = clamp(s, 0, 1)
```
- **file:line** `somabrain/admin/cognitive/amygdala.py` (`AmygdalaSalience.score`)
- **Status:** LIVE

**(T35) Amygdala gates (NE + 5-HT smoothing)**
```
stability = clamp(serotonin, 0, 1)
hyst      = hysteresis · (1 + stability)             # 5-HT response smoothing
th_store = threshold_store + noradrenaline − hyst·[last_store]
th_act   = threshold_act   + noradrenaline − hyst·[last_act]
hard:  do_store = (s ≥ th_store);  do_act = (s ≥ th_act)
soft:  p = σ( (s − th) / T ),  T = max(1e-4, soft_temperature · (1 + stability))
       σ(x) = 1/(1+e^{−x}) with x clamped to [−20, 20]
       do_* = (p ≥ 0.5)
```
- **file:line** `somabrain/admin/cognitive/amygdala.py` (`_thresholds`, `gate_probs`)
- **Status:** LIVE. Higher 5-HT widens hysteresis and the soft sigmoid
  (decisions flap less). Documented consumer of serotonin.

**(T35b) Supervisor free-energy P-controller (W2.6 wired)**
```
F = α_err · pred_error + β_nov · novelty
δ_DA  = dopamine_target(1 − pred_error)
δ_ACh = acetylcholine_target(novelty, pred_error)
δ_NE  = noradrenaline_target(0.5 · (pred_error + novelty))
δ_5HT = serotonin_target(pred_error)
d_m   = clip(g · (δ_m − m), −lim, lim)      then EWMA-smoothed, then Π
```
- **file:line** `somabrain/runtime/supervisor.py` (`Supervisor.adjust`)
- **Status:** LIVE when `SOMABRAIN_USE_META_BRAIN=True` — `get_supervisor()`
  is wired into `POST /cognitive/act` (`api/endpoints/cognitive.py`).
  Default-off is a product flag, not a missing wire.

**(T36) Rust Amygdala linear salience / gate**
```
salience = w₀·novelty + w₁·error + w₂·energy
gate     = (salience > threshold)
```
- **file:line** `rust_core/src/neuro.rs` (`Amygdala`)
- **Status:** EXPORTED

### 2.5 Memory / Scoring / Salience

**(T37) Dense salience (learning package)**
```
s = clamp( w_novelty·novelty + w_error·error, 0, 1 )
```
- **file:line** `somabrain/admin/core/learning/salience.py:35-39` (weights `26-32`)
- **Status:** LIVE

**(T38) FD salience sketch**
```
energy = ‖v‖²
residual_ratio = clamp( ‖v‖² − ‖Bᵀv‖²  /  ‖v‖² , 0, 1 )   # B = low-rank basis
capture_ratio  = clamp( captured_energy / total_energy , 0, 1 )   # 1.0 if total ≤ ε
decay: S ← S·√decay;  energies ← energy·decay
projection:  p = √α ⊙ (Bᵀ v)
```
- **file:line** `somabrain/admin/core/learning/salience.py:71-192` (observe `71-90`, residual `102-116`, capture `165-172`, project `182-192`)
- **Status:** LIVE

**(T39) Unified scorer**
```
terms   = [(w_cosine, cos(q,c))]
        + [(w_fd, cos(Pq, Pc))]     if FD backend present
        + [(w_recency, R(age))]     if age_seconds is not None
score   = clamp( Σ w_i·v_i / Σ w_i , 0, 1 )      # renormalised over ACTIVE terms
```
with `cos` from (T15); `P` = FD projection (T38); `R` = stretched-exponential recency (T41). Weights come from the **constructor** (factory reads `SOMABRAIN_SCORER_W_*` and passes them in) and are clamped to `[weight_min, weight_max]`. The class never re-reads settings.
- **file:line** `somabrain/admin/core/learning/scoring.py:123-167` (components `96-121`, weights `43-68`)
- **Status:** LIVE
- **Note (FIXED, W5b / DEBT-022/023):** Constructor args are the sole weight source. Missing backends/terms are dropped and remaining weights renormalised, so the ceiling is always 1.0.

**(T40) Working-memory salience**
```
novelty  = 1 − max_i cos(q, v_i)                 # 1.0 if empty / zero-norm
recency  = 1 − cos(q, v_last)                    # query salience
s_query  = clamp( α·novelty + β·reward + γ·recency, 0, 1 )
s_item   = clamp( α·novelty + γ·item.recency, 0, 1 )
s_evict  = clamp( α·novelty + γ·R(age), 0, 1 )
```
`item.recency` and `R(age)` both come from the single kernel (T41).
- **file:line** `somabrain/memory/wm/wm_salience.py:27-58` (query), `108-140` (item), `143-179` (evict), novelty `82-105`
- **Status:** LIVE (FIXED, W5b — one kernel)

**(T41) Canonical recency kernel (stretched exponential)**
```
R(age) = clamp( exp( −(age/scale)^sharpness ) , floor , 1 )
recency_steps = min( log1p(age/scale)·sharpness , cap )
```
defaults from `somabrain.math.contracts`: `scale=RECENCY_SCALE=60` (`SOMABRAIN_WM_RECENCY_TIME_SCALE`),
`cap=RECENCY_CAP=1000`, `sharpness=RECENCY_SHARPNESS=1.2`, `floor=RECENCY_FLOOR=0.05`.
- **file:line** `somabrain/math/recency.py:19-95`; wrappers `memory/scoring.py:135-154`, `memory/client/ranking.py:251-266`, `admin/core/learning/scoring.py:111-121`, `memory/wm/wm_salience.py:178`, `memory/wm/wm_eviction.py:89`, `memory/wm/core.py:578`, `context/builder.py:489-502`
- **Status:** LIVE — **single kernel** (FIXED, W5b / DEBT-020). The former `exp(-age/τ)` scorer path and the three conflicting `WM_RECENCY_TIME_SCALE` defaults are deleted.

**(T42) Density factor**
```
if margin ≥ target:  f = 1
else:  deficit = (target − margin)/target
       f = clamp(1 − weight·deficit, floor, 1)
```
defaults: `target=0.2`, `floor=0.6`, `weight=0.35`.
- **file:line** `somabrain/memory/scoring.py:164-202`; parallel `somabrain/context/builder.py:539-564`
- **Status:** LIVE

**(T43) Rank / rescore**
```
base = sign(s)·log1p(|s|)   if |s| > 1 else s
final_rank_key = base·weight_factor + lex_bonus
new_score = scorer.score(...) · recency_boost · density_factor
new_score = clamp(new_score, 0, 1)
```
`lex_bonus` is the single implementation (T43b).
- **file:line** `somabrain/memory/client/ranking.py:187-217` (rank), `381+` (rescore); re-exported by `memory/scoring.py:227-266`
- **Status:** LIVE

**(T43b) Lexical bonus (single formula)**
```
bonus = 0
for field in {task, text, content, what, fact, headline, summary}:
    if field == query:            bonus = max(bonus, 1.5)
    elif query in field:          bonus = max(bonus, 1.0)
token_matches = #{query tokens of length ≥ 3 appearing in any field}
bonus += min(0.25 · token_matches, 1.0)
```
- **file:line** `somabrain/memory/client/ranking.py:152-184`
- **Status:** LIVE — **one implementation** (FIXED, W5b / DEBT-021). The `hit_processing.py` `max(0.3+0.1·n)` copy is deleted.

**(T44) Retrieval weight softmax + tau adaptation (context builder)**
```
combined_i = ( α·cos(q, e_i) + β·graph_score_i + γ·age_penalty_i ) · density_i
w = softmax( (combined − max(combined)) / max(τ, 1e-6) )
dup_ratio = 1 − |unique ids| / n
if dup_ratio > dup_threshold:  τ ← min(τ + inc_up·(dup_ratio−dup_threshold), τ_max)
else:                          τ ← max(τ − inc_down·(dup_threshold−dup_ratio), τ_min)
then entropy-cap sharpen on (α,β,γ,τ)  (see T28b)
residual = normalize( Σ_i w_i · e_i )
```
- **file:line** `somabrain/context/builder.py:315-464` (softmax `355-361`, tau adapt `363-381`, residual `493-517`)
- **Status:** LIVE

**(T28b) Entropy cap (context-builder variant)**
```
H = −Σ p ln p   on linear-normalized (α,β,γ,τ)
while H > cap and attempts < 10:
    scale = min(0.99, max(0.2, (H−cap)/(cap+1e-9)))
    vec_i ← vec_i · (1−scale)   ∀ i ≠ largest;  renormalize
if still H > cap:  vec_i ← vec_i · 0.05  ∀ i ≠ largest;  renormalize
```
- **file:line** `somabrain/context/builder.py:383-440`
- **Status:** LIVE
- **Note:** Different shrink law from (T28). Two live entropy-cap implementations.

**(T45) HRR context decay and novelty**
```
context ← context · exp(−λ_decay · Δt)          # if λ_decay > 0
admit:  context ← normalize(context + v)
novelty(v) = clamp(1 − cos(v, context), 0, 1)
cleanup score_i = cos(q, v_i) · exp(−λ_decay · age_i)   # weight=1 if λ_decay=0
margin = max(0, best − second)
if best < min_confidence: return ("", 0.0, second)
```
- **file:line** `somabrain/admin/core/context_hrr.py:92-105` (decay), `144-165` (admit), `167-175` (novelty), `177-239` (cleanup)
- **Status:** LIVE

**(T46) Context SNR metric**
```
noise = √(anchor_count / max(1, D))
snr_db = 20 · log10( max(‖context‖/noise, 1e-12) )     # 0.0 if either ≤ 1e-12
```
- **file:line** `somabrain/admin/core/context_hrr.py:107-128`
- **Status:** LIVE (observability only)

### 2.6 Annealing (cross-refs)

Already specified as **(T25)–(T28)**, **(T28b)**. Additional standalone Rust schedules:

**(T47) `apply_tau_decay` (Rust engine method)**
```
τ ← max(min_tau, τ · (1 − decay_rate))
```
- **file:line** `rust_core/src/adaptation.rs:193-195`
- **Status:** EXPORTED

**(T48) Softmax-temperature leader selection**
```
τ_safe = max(τ, 0.01)
p_i    = exp(s_i/τ_safe − max) / Σ exp(·)
H      = −Σ_{p>1e-10} p · ln p
exceeded = (entropy_cap > 0) ∧ (H > entropy_cap)
```
- **file:line** `rust_core/src/mathcore.rs:205-241`
- **Status:** EXPORTED (`softmax_temperature`, `compute_entropy`, `softmax_leader_selection`)

### 2.7 Prediction

**(T49) SlowPredictor error (Rust)**
```
e = clamp(1 − cos(pred, actual), 0, 1)     # identical to (T16) cosine_error; no |cos|
e = 1                                      if either norm == 0
```
- **file:line** `rust_core/src/prediction.rs` (`SlowPredictor::error`)
- **Status:** EXPORTED (FIXED, W4.6 / DEBT-019 — the former `1 − |cos|` is deleted; antipodal vectors score 1.0, matching Python)

**(T50) Python `SlowPredictor` / `BudgetedPredictor` / `LLMPredictor`**
```
SlowPredictor:   predicted = expected;  err = cosine_error(expected, actual)   # after sleep(delay_ms)
BudgetedPredictor: run inner in thread;  join(timeout_ms);  raise TimeoutError if alive
LLMPredictor:    base = cosine_error;  adj = HTTP POST {"signal": base} → clamp(data.error, 0, 1)
```
- **file:line** `somabrain/admin/core/learning/prediction.py:100-245` (slow), `148-245` (budgeted), `350-423` (LLM)
- **Status:** LIVE (control flow); math is (T16) + clamp

**(T51) Mahalanobis-like bounded surprise (Python)**
```
μ ← (1−α)μ + α x
σ² ← max( (1−α)σ² + α (x−μ_new)² , 1e-6 )
d² = Σ (x−μ)² / σ²
surprise = d² / (d² + dim)                     ∈ [0, 1)
err = clamp( 0.8 · cosine_error + 0.2 · surprise, 0, 1 )
```
- **file:line** `somabrain/admin/core/learning/prediction.py:275-347` (stats `275-297`, distance `299-318`, blend `344`)
- **Status:** LIVE

**(T52) Mahalanobis distance (Rust)**
```
# first update:  μ ← x,  σ² ← 0.1
μ    ← (1−α)·μ + α·x
σ²   ← max( (1−α)·σ² + α·(x−μ_new)² , 1e-6 )       # diagonal only
d(x) = sqrt( Σ_i (x_i − μ_i)² / σ_i² )             # true diagonal Mahalanobis
```
- **file:line** `rust_core/src/prediction.rs` (`MahalanobisPredictor::update`, `::distance`)
- **Status:** EXPORTED (FIXED, W4.6 / DEBT-018)
- **Note:** The name now equals the math: diagonal covariance whitening is implemented (same EWMA mean/var as (T51)), and `distance` returns `sqrt((x−μ)ᵀ Σ⁻¹ (x−μ))` for `Σ = diag(σ²)`. The former Euclidean `‖x−μ‖₂` with a dead `covariance` field is deleted.

**(T53) Consolidation**
```
NREM:  summary = mean_k episodic_k
REM:   pair_out = (a + b)/2
MultiConsolidation:  mean over rows
Hebbian:  W ← W + η · pre ⊗ post ;  out = W · input
```
- **file:line** `rust_core/src/prediction.rs:131-216`
- **Status:** EXPORTED

**(T54) Rust `SlowPredictor.predict`**
```
predict(x) = last(history)   if history ≠ ∅
           = 0               otherwise
```
- **file:line** `rust_core/src/prediction.rs:23-28`
- **Status:** EXPORTED (trivial persistence predictor)

**(T55) Rust `LLMPredictor.predict`**
```
predict(x) = [0.0]           # constant; no I/O
```
- **file:line** `rust_core/src/prediction.rs:109-111`
- **Status:** DEAD-STUB

**(T56) Rust `BudgetedPredictor`**
```
if timeout_ms < 10: raise ValueError("Timeout exceeded")
else: return input
```
- **file:line** `rust_core/src/prediction.rs:57-62`
- **Status:** DEAD-STUB (no timing; returns input unchanged)

### 2.8 Calibration

**(T57) Temperature scaling fit**
```
p ← clip(p, 1e-8, 1−1e-8);  logits = log(p/(1−p))
NLL(T) = −mean( y·log σ(z) + (1−y)·log(1−σ(z)) ),  z = logits/T,  T ≥ 1e-6
golden-section search on [0.1, 5.0], φ = (√5−1)/2, tol=1e-4, ≤80 iters
candidates = {a, b, c, d, 1.0};  T* = argmin NLL
T = clamp(T*, 0.05, 10.0)
```
- **file:line** `somabrain/calibration/temperature_scaling.py:33-91`
- **Status:** LIVE (requires ≥ `min_samples`=50, else returns `1.0`)

**(T58) Apply temperature**
```
if not fitted or p ≤ 0 or p ≥ 1: return p
logit = log( p / (1 − p + 1e-10) )
return 1 / (1 + exp( −logit/T ))
```
- **file:line** `somabrain/calibration/temperature_scaling.py:93-100`
- **Status:** LIVE

**(T59) ECE / Brier / reliability**
```
ECE = Σ_bins (n_b/N) · |mean_conf_b − mean_acc_b|     # n_bins=10, ≤10 samples → 0.0
Brier = mean( (conf − acc)² )
```
- **file:line** `somabrain/calibration/temperature_scaling.py:103-200`
- **Status:** LIVE

### 2.9 Cognition / Spectral / Graph

**(T60) Lanczos spectral interval**
```
m-step Lanczos on A:  T = tridiag(α, β);  (a,b) = (λ_min(T), λ_max(T))
early stop if β = 0
```
- **file:line** `somabrain/math/lanczos_chebyshev.py:17-54`
- **Status:** LIVE (via `graph_heat_chebyshev`)

**(T61) Chebyshev heat apply**
```
(a, b) ← expand(a, b) = (max(0, a−ε), b+ε)     # ε = SPECTRAL_INTERVAL_EPSILON = 0.1
A′ = (2A − (b+a)I)/(b−a)
nodes_k = cos( π(k−0.5)/K ),  k=1..K
λ_k = (b−a)/2 · nodes_k + (b+a)/2
f_k = exp(−t λ_k)
c_k = (2/K) Σ f_j cos(k · arccos(nodes_j));  c_0 ← c_0/2
y = Σ_{k=0}^{K} c_k T_k(A′) x        # Clenshaw recurrence
```
- **file:line** `somabrain/math/lanczos_chebyshev.py:57-113` (coeffs `93-103`, Clenshaw `105-113`); expansion `somabrain/math/graph_heat.py:17-33,50-53`
- **Status:** LIVE (FIXED, W5b / DEBT-017 — Lanczos Ritz bounds are expanded by ε before the affine map)

**(T62) Lanczos expv (Krylov heat)**
```
y = ‖x‖ · V exp(−t T) e₁
```
- **file:line** `somabrain/math/lanczos_chebyshev.py:116-164`
- **Status:** LIVE (via `graph_heat_lanczos`)

**(T63) Heat method selection**
```
y = exp(−t L) x0
method = "lanczos" if settings.HEAT_METHOD == "lanczos" else "chebyshev"
err = MSE(y, observed)
conf = exp(−α_conf · max(0, err))
```
- **file:line** `somabrain/predictors/base.py:21-32` (select), `76-123` (salience/error/confidence), defaults `46-53`
- **Status:** LIVE

**(T64) Laplacian from adjacency**
```
L = diag(A·1) − A
```
- **file:line** `somabrain/predictors/base.py:184-194`
- **Status:** LIVE

**(T65) APPR push**
```
r[seed] = 1
while ∃ u: r_u > eps:
    p_u += α · r_u
    remain = (1−α)·r_u
    r_v   += remain · w_uv / Σ_v w_uv      # for neighbors of u
    r_u    = 0
```
default `α = 0.85`, `eps = settings.TRUTH_APPR_EPS` (default `"1e-4"`).
- **file:line** `somabrain/math/appr.py:15-54`
- **Status:** LIVE (exported utility)

**(T66) Sinkhorn (log-domain)**
```
K = −C/ε
u ← log a − LSE_rows(K + v)
v ← log b − LSE_cols(K + u)
P = exp(K + u ⊕ v)
err = max( ‖P1 − a‖_∞ , ‖Pᵀ1 − b‖_∞ )
```
defaults `ε=1e-2`, `niter=1000`, `tol=1e-6`.
- **file:line** `somabrain/math/sinkhorn.py:12-81`
- **Status:** LIVE (via bridge)

**(T67) Sinkhorn bridge cost**
```
C_ij = ‖x_i‖² + ‖y_j‖² − 2 x_i·y_j      # squared Euclidean
a = 1/n,  b = 1/m
```
- **file:line** `somabrain/math/bridge.py:15-43`
- **Status:** LIVE

**(T68) Frequent-Directions compress**
```
SVD: S = U Σ Vᵀ
δ = σ_min²
σ′ = √max(σ² − δ, 0)
S ← diag(σ′_{1:k}) · V_{1:k,:}          # k = min(ℓ, ·)
approx_cov = Sᵀ S
```
- **file:line** `somabrain/math/fd_rho.py:40-55`
- **Status:** LIVE

**(T69) SDR encode + LSH band hash**
```
k = max(1, int(D · density))
active indices: blake2b(f"{token}:{salt}") mod D,  salt = 0,1,… until |idx| = k
band hash: FNV-style  acc ^= i + 0x9E3779B97F4A7C15;  acc = (acc · 1099511628211) mod 2^64
```
- **file:line** `somabrain/admin/core/sdr.py:50-127` (encode), `171-201` (band hash)
- **Status:** LIVE

**(T70) Softmax (Rust, max-shifted)**
```
p_i = exp(v_i − max v) / Σ exp(v_j − max v)
```
- **file:line** `rust_core/src/mathcore.rs:172-176,196-201`
- **Status:** EXPORTED

**(T71) BatchNorm inference / running stats**
```
y_i = γ_i · (x_i − μ_i) / √(σ_i² + ε) + β_i
μ ← m·μ + (1−m)·batch_mean;  σ² ← m·σ² + (1−m)·batch_var
```
- **file:line** `rust_core/src/mathcore.rs:107-122,178-186,259-268`
- **Status:** EXPORTED

**(T72) Inverted dropout**
```
y_i = 0                 if U(0,1) < rate
    = x_i / (1−rate)    otherwise
```
seed fixed at 42 unless `set_seed`.
- **file:line** `rust_core/src/mathcore.rs:141-146`
- **Status:** EXPORTED

**(T73) FNOM spectrum encode**
```
spectrum[i] = SHA256(key‖value)[i mod 32] / 255
sim(v1,v2)  = cos(v1, v2)      # zero-norm → 0, no clamp
```
- **file:line** `rust_core/src/mathcore.rs:56-81`
- **Status:** EXPORTED

**(T74) BayesianMemory (GMD Theorem 2/3, as coded)**
```
update:   m ← (1−η)·m + η·b
          cov ← (1−η)²·cov + 1e-6
recall:   v̂_i = (m_i · k_i) / (k_i² + λ);   v̂ ← v̂/‖v̂‖
SNR(L):   w_L = η(1−η)^L ;  W2 = η²/(2η − η²)
          SNR = D · w_L² / (W2 − w_L²)      # ∞ if denom ≤ 0
horizon:  L* = max { L : SNR(L) ≥ snr_min }   by linear scan, cap 10000
```
- **file:line** `rust_core/src/mathcore.rs:386-455`
- **Status:** EXPORTED (`BayesianMemory`)
- **Note:** `alpha = 640.0` field is set but unused in the update/recall/SNR path (`mathcore.rs:379`, comment "Deprecated in v4.4 but kept for ABI compat").

**(T75) HRR unitary roles**
```
seed_val = u64(SHA256("role|"+token)) ⊕ cfg.seed
role = make_unitary_role(D, seed_val);  role = normalize_array(role)
non-unitary path: role = normalize(N(0,1)^D) with seed64
```
- **file:line** `somabrain/admin/core/quantum.py:327-372`
- **Status:** LIVE

**(T76) Cleanup (QuantumLayer)**
```
score = cos(query, anchor)
if density_matrix present:
    score = α · density.score(q, a) + (1−α) · score
return argmax score
```
`α = BrainSetting("cleanup_alpha", "default")` — **note:** second arg is the string `"default"` (tenant), not a numeric default (`quantum.py:496-497`).
- **file:line** `somabrain/admin/core/quantum.py:475-517`
- **Status:** LIVE

**(T77) `QuantumLayer.unbind_wiener`**
```
snr_db, k_est, alpha, whiten are IGNORED
if b is str:  return unbind_exact_unitary(c, b)     # T7
else:         return unbind(c, b)                    # T9
```
- **file:line** `somabrain/admin/core/quantum.py:433-454`
- **Status:** LIVE (thin alias; parameters are dead)

---

## 3. Per-Equation Status Index

| Eq | Subsystem | Status | Primary site |
|---|---|---|---|
| T1 | binding | LIVE | `mathcore.rs` (`fwht`) — raises on non-2^r (W4.4) |
| T2 | binding | LIVE | `bhdc.rs` (`BHDCEncoder::new`) |
| T3 | binding | LIVE | `bhdc.rs` (`vector_from_rng`) |
| T3b | binding | LIVE-FALLBACK | `bhdc_encoder.py` (`_PythonBHDCEngine._render_sparse_vector`) |
| T4 | binding | LIVE | `bhdc.rs` (`build_seed_bundle`, `seed_to_uint64`) |
| T4b | binding | LIVE-FALLBACK | `bhdc_encoder.py` (`_compose_seed`) |
| T5 | binding | EXPORTED | `bhdc.rs` (`bind`/`unbind`/`bundle`) |
| T6 | binding | LIVE | `bhdc.rs` (`PermutationBinder::bind`) |
| T7 | binding | LIVE | `bhdc.rs` (`PermutationBinder::unbind`) — λ* from formula (W4.1) |
| T7b | binding | LIVE-FALLBACK | `bhdc_encoder.py` (`_PythonPermutationBinder.unbind`) — Wiener + FWHT (W4.3) |
| T8 | binding | LIVE | `quantum.py` (`QuantumLayer.bind`) |
| T9 | binding | LIVE | `quantum.py` (`QuantumLayer.unbind`) — same λ* source (W4.1) |
| T10 | binding | TEST-ONLY | `quantum_pure.py` |
| T11 | binding | EXPORTED | `mathcore.rs` (`quantize_8bit`) — 256-level |
| T12 | binding | DELETED | no `compute_optimal_p`; p = 0.1 is an engineering choice (W4.2) |
| T13 | binding | EXPORTED | `mathcore.rs` (`compute_wiener_lambda`) — bits honored (W4.1) |
| T14 | binding | EXPORTED | `bhdc.rs` (`ensure_binary`) |
| T15 | similarity | LIVE | `similarity.py:34-93` |
| T16 | similarity | LIVE | `similarity.py:96-135` |
| T17 | similarity | LIVE | `similarity.py:138-182` |
| T18 | similarity | LIVE | `normalize.py:37-87` |
| T19 | similarity | LIVE | `normalize.py:90-200` |
| T20 | similarity | LIVE | `numerics.py:117-282` |
| T21 | similarity | EXPORTED | `mathcore.rs:245-257` |
| T22 | similarity | LIVE | `numerics.py:339-358` |
| T23 | learning | LIVE | `engine.py:364-391` |
| T23b | learning | EXPORTED | `adaptation.rs:165-183` |
| T24 | learning | LIVE* | `engine.py:350-362` |
| T25 | learning | LIVE | `annealing.py:169-220` |
| T25b | learning | EXPORTED | `adaptation.rs:241-262` |
| T26 | learning | LIVE | `annealing.py:223-263` |
| T27 | learning | LIVE | `annealing.py:396-428` |
| T28 | learning | LIVE | `annealing.py:292-390` |
| T28b | learning | LIVE | `builder.py:383-440` |
| T29 | learning | EXPORTED | `adaptation.rs:281-305` |
| T30 | learning | LIVE | `engine.py:532-541` |
| T31 | learning | LIVE | `engine.py:571-573` |
| T32 | neuromod | DELETED | Rust ODE removed (W2.6 / DEBT-007); homeostatic law is T33 |
| T33 | neuromod | LIVE | `runtime/neuromodulators.py` (target laws) + `adaptive/core.py` (`m ← Π(m+η(δ−m))`) |
| T34 | neuromod | LIVE | `amygdala.py` (`AmygdalaSalience.score`) |
| T35 | neuromod | LIVE | `amygdala.py` (`_thresholds`, `gate_probs`) — 5-HT smoothing |
| T35b | neuromod | LIVE* | `runtime/supervisor.py` (`Supervisor.adjust`) — gated `SOMABRAIN_USE_META_BRAIN` |
| T36 | neuromod | EXPORTED | `neuro.rs` (`Amygdala`) |
| T37 | memory | LIVE | `learning/salience.py:35-39` |
| T38 | memory | LIVE | `learning/salience.py:71-192` |
| T39 | memory | LIVE | `learning/scoring.py:123-167` — constructor weights + FD-off renormalise (W5b) |
| T40 | memory | LIVE | `wm_salience.py:27-179` — uses T41 kernel (W5b) |
| T41 | memory | LIVE | `math/recency.py` — **single kernel** (W5b) |
| T42 | memory | LIVE | `memory/scoring.py:164-202` |
| T43 | memory | LIVE | `memory/client/ranking.py` — LIVE ranker (W5b) |
| T43b | memory | LIVE | `memory/client/ranking.py:152-184` — **one lexical bonus** (W5b) |
| T44 | memory | LIVE | `builder.py:315-464` |
| T45 | memory | LIVE | `context_hrr.py:92-239` |
| T46 | memory | LIVE | `context_hrr.py:107-128` |
| T47 | annealing | EXPORTED | `adaptation.rs:193-195` |
| T48 | annealing | EXPORTED | `mathcore.rs:205-241` |
| T49 | prediction | EXPORTED | `prediction.rs` (`SlowPredictor::error`) — `1 − cos` (W4.6) |
| T50 | prediction | LIVE | `learning/prediction.py:100-423` |
| T51 | prediction | LIVE | `learning/prediction.py:275-347` |
| T52 | prediction | EXPORTED | `prediction.rs` (`MahalanobisPredictor`) — diagonal Mahalanobis (W4.6) |
| T53 | prediction | EXPORTED | `prediction.rs:131-216` |
| T54 | prediction | EXPORTED | `prediction.rs:23-28` |
| T55 | prediction | DEAD-STUB | `prediction.rs:109-111` |
| T56 | prediction | DEAD-STUB | `prediction.rs:57-62` |
| T57 | calibration | LIVE | `temperature_scaling.py:33-91` |
| T58 | calibration | LIVE | `temperature_scaling.py:93-100` |
| T59 | calibration | LIVE | `temperature_scaling.py:103-200` |
| T60 | cognition | LIVE | `lanczos_chebyshev.py:17-54` |
| T61 | cognition | LIVE | `lanczos_chebyshev.py:57-113` + `graph_heat.py` ε-expansion (W5b) |
| T62 | cognition | LIVE | `lanczos_chebyshev.py:116-164` |
| T63 | cognition | LIVE | `predictors/base.py:76-123` |
| T64 | cognition | LIVE | `predictors/base.py:184-194` |
| T65 | cognition | LIVE | `appr.py:15-54` |
| T66 | cognition | LIVE | `sinkhorn.py:12-81` |
| T67 | cognition | LIVE | `bridge.py:15-43` |
| T68 | cognition | LIVE | `fd_rho.py:40-55` |
| T69 | cognition | LIVE | `sdr.py:50-201` |
| T70 | cognition | EXPORTED | `mathcore.rs:172-176` |
| T71 | cognition | EXPORTED | `mathcore.rs:107-122` |
| T72 | cognition | EXPORTED | `mathcore.rs:141-146` |
| T73 | cognition | EXPORTED | `mathcore.rs:56-81` |
| T74 | cognition | EXPORTED | `mathcore.rs:386-455` |
| T75 | cognition | LIVE | `quantum.py:327-372` |
| T76 | cognition | LIVE | `quantum.py:475-517` |
| T77 | cognition | LIVE | `quantum.py:433-454` |

\* T24 is live only when `enable_dynamic_lr` is true **and** gains are unmodified from settings.

---

## 4. Constants Table

Values are the coded defaults. "Appears in" lists every site found in the scope files (and settings sources they read). **As of W1b**, shared constants have a single home: `somabrain/math/contracts.py`. Consumers import from there; duplicates are deleted.

| Constant | Value | Symbol | Appears in | Duplicate? |
|---|---|---|---|---|
| Wiener λ default | `compute_wiener_lambda(p, 8)` at production `p` (≈ `5.696e-5` at `p=0.1`) | `lambda_reg` | `somabrain/math/contracts.py` (`compute_wiener_lambda`); consumed by `bhdc_encoder.py`, `bhdc.rs`, `quantum.py`, `brain_settings/models.py` (`gmd_lambda_reg`) | **No** — single formula source in contracts (W4.1 + W1b FIXED) |
| λ\* closed form | `Δ² / (12 p (1−p))`, `Δ = 2/(2^bits − 1)` | `λ*` | `somabrain/math/contracts.py` (`compute_wiener_lambda`); Rust mirror `rust_core/src/mathcore.rs` | formula only; no constant |
| Quantization Δ | `2/(2^bits − 1)` (`2/255` at 8-bit) | `Δ` | `somabrain/math/contracts.py` (`QUANT_STEP`); `rust_core/src/mathcore.rs` | **No** — `contracts.QUANT_STEP` |
| Quantization bits | `8` | `bits` | `somabrain/math/contracts.py` (`QUANT_BITS`); `brain_settings/models.py` (`gmd_quantization_bits`) | **No** — `contracts.QUANT_BITS` |
| BHDC sparsity | `0.1` | `p` | `somabrain/math/contracts.py` (`BHDC_P`); `settings/cognitive.py:264` | **No** — `contracts.BHDC_P` (W1b) |
| HRR dim | `8192` | `D` | `somabrain/math/contracts.py` (`BHDC_D`); `settings/cognitive.py` (`SOMABRAIN_HRR_DIM`, `HRR_DIM`) | **No** — `contracts.BHDC_D` (W1b DEF-10 FIXED) |
| Adaptation gains (Python) | `1.0, −0.5, 1.0, −0.25, −0.25` | `gain_*` | `somabrain/math/contracts.py` (`ADAPT_GAINS`); `learning/config.py`; `settings/cognitive.py` | **No** — `contracts.ADAPT_GAINS` (W1b DEF-13 FIXED) |
| Adaptation bounds (Python) | α∈[0.1,5], γ∈[0,1], λ∈[0.1,5], μ∈[0.01,5], ν∈[0.01,5] | — | `somabrain/math/contracts.py` (`ADAPT_BOUNDS`); `learning/config.py` | **No** — `contracts.ADAPT_BOUNDS` (W1b) |
| Adaptation gains (Rust) | `0.1, 0.05, 0.1, 0.05, 0.02` | `gain_*` | `rust_core/src/adaptation.rs:118-122` | **CONFLICT with Python** (DEBT-008, W3) |
| tau floor | `0.1` | `τ_min` | `somabrain/math/contracts.py` (`TAU_FLOOR`); `settings/cognitive.py` (`SOMABRAIN_TAU_MIN`); `learning/annealing.py`; `tasks/temperature_anneal.py` | **No** — `contracts.TAU_FLOOR` (W1b DEF-05 FIXED) |
| tau decay factor | `0.95` | — | `somabrain/math/contracts.py` (`TAU_DECAY_FACTOR`); `tasks/temperature_anneal.py` | **No** — `contracts.TAU_DECAY_FACTOR` (W1b DEF-06 FIXED) |
| tau anneal interval | `60.0` | — | `somabrain/math/contracts.py` (`TAU_INTERVAL`); `tasks/temperature_anneal.py` | **No** — `contracts.TAU_INTERVAL` (W1b) |
| Recency scale | `60.0` | `scale` | `somabrain/math/contracts.py` (`RECENCY_SCALE`); `settings/cognitive.py`; `memory/scoring.py` | **No** — `contracts.RECENCY_SCALE` (W1b DEF-02 FIXED) |
| Recency sharpness | `1.2` | `sharpness` | `somabrain/math/contracts.py` (`RECENCY_SHARPNESS`); `memory/scoring.py`; `builder.py` | **No** — `contracts.RECENCY_SHARPNESS` (W1b) |
| Recency floor | `0.05` | `floor` | `somabrain/math/contracts.py` (`RECENCY_FLOOR`); `memory/scoring.py`; `builder.py` | **No** — `contracts.RECENCY_FLOOR` (W1b) |
| Scorer weights | `0.6 / 0.25 / 0.15` | `w_*` | `somabrain/math/contracts.py` (`SCORER_WEIGHTS`); `settings/cognitive.py` | **No** — `contracts.SCORER_WEIGHTS` (W1b) |
| Promotion θ / ticks | `0.85` / `3` | — | `somabrain/math/contracts.py` (`PROMOTE_THETA`, `PROMOTE_TICKS`); `memory/promotion.py` | **No** — `contracts.*` (W1b) |
| Neuromod clamps | DA [0.2,0.8], 5HT [0,1], NE [0,0.1], ACh [0,0.1] | — | `somabrain/math/contracts.py` (`NEURO_BOUNDS`); `neuro.rs:84-87`; `settings/neuro.py` | **No** — `contracts.NEURO_BOUNDS` (W1b) |
| adapt_lr | `0.05` (min 0, max 0.25) | `lr` | `brain_settings/models.py:232-238`; `adaptation.rs:105` | — |
| Scorer weights | `0.6 / 0.25 / 0.15` from `contracts.SCORER_WEIGHTS` | `w_*` | `somabrain/math/contracts.py`; `settings/cognitive.py:191-195`; factory `bootstrap/singletons.py:232-241` | **No** — constructor honors args (W5b) |
| Recency scale | `60.0` (`contracts.RECENCY_SCALE`) | `scale` | `math/contracts.py`; `settings/cognitive.py:149-151` | **No** — one key (W5b) |
| Recency sharpness | `1.2` (`contracts.RECENCY_SHARPNESS`) | `sharpness` | `math/contracts.py`; `settings/cognitive.py:203` | **No** (W5b) |
| Recency floor | `0.05` (`contracts.RECENCY_FLOOR`) | `floor` | `math/contracts.py`; `settings/cognitive.py:204` | **No** (W5b) |
| Recency cap | `1000` (`contracts.RECENCY_CAP`) | `cap` | `math/contracts.py`; `settings/cognitive.py:152` | **No** (W5b) |
| Salience dense weights | `0.6 / 0.4 / 0.0` | `w_novelty, w_error, w_fd` | `learning/salience.py:30-32` | — |
| Amygdala soft T | settings default `0.1`, floor `1e-4` | `T` | `amygdala.py:79-82,244` | — |
| Amygdala FD energy floor | `0.9` | `fd_energy_floor` | `amygdala.py:83-86` | — |
| Dopamine base | `0.4` (settings; the live store default) | `m₁` | `settings/neuro.py:10`; `runtime/neuromodulators.py` | Rust mirror init `0.5` is overwritten by the first `set_state` sync |
| Serotonin base | `0.5` | `m₂` | `settings/neuro.py:11-13` | consistent |
| Noradrenaline base | `0.0` (settings) | `m₃` | `settings/neuro.py:14` | Rust mirror init `0.05` overwritten on sync |
| Acetylcholine base | `0.0` (settings) | `m₄` | `settings/neuro.py:15` | Rust mirror init `0.05` overwritten on sync |
| Neuromod clamps | DA [0.2,0.8], 5HT [0,1], NE [0,0.1], ACh [0,0.1] | Π | `math/contracts.py` (`NEURO_BOUNDS`); `runtime/neuromodulators.py` (`project`); `settings/neuro.py:18-31` | **No** — `contracts.NEURO_BOUNDS` |
| Neuromod `k_d` / `k_r` / `u_scale` | **DELETED** | — | formerly `neuro.rs`, `brain_settings/models.py` | removed with the dead ODE (W2.6 / DEBT-007) |
| Entropy sharpen rate | `0.8` | `sharpen_rate` | `annealing.py:339`; `brain_settings/models.py:399` | builder variant uses adaptive scale (T28b) |
| Entropy final sharpen | `0.05` | `final_sharpen` | `annealing.py:340`; `brain_settings/models.py:400`; `builder.py:424` | consistent |
| tau_min | **`0.05`** / **`0.01`** | `τ_min` | `annealing.py:254,102,108` vs `adaptation.rs:202` vs `engine.py:571-573` | **CONFLICT (3 values)** |
| Recency half-life | `60.0` (`contracts.RECENCY_SCALE`) | `scale` | `math/recency.py`; `settings/cognitive.py:149-151` | **No** — single source (W5b) |
| Recency sharpness | `1.2` | `sharpness` | `math/recency.py`; `contracts.py` | consistent |
| Recency floor | `0.05` | `floor` | `math/recency.py`; `contracts.py` | consistent |
| Density target/floor/weight | `0.2 / 0.6 / 0.35` | — | `memory/scoring.py:176-178`; `builder.py:150-156` | consistent |
| Sinkhorn ε / tol / niter | `1e-2 / 1e-6 / 1000` (solver), maxiter `5000` (bridge) | `eps, tol` | `sinkhorn.py:16-17`; `bridge.py:35-40` | niter differs (1000 vs 5000) |
| APPR α / eps | `0.85` / `TRUTH_APPR_EPS` default `"1e-4"` | `α` | `appr.py:18,32`; `settings/cognitive.py:516` | — |
| Chebyshev K | `24` (graph_heat) / `30` (PredictorConfig) / `settings.TRUTH_CHEBYSHEV_K` | `K` | `graph_heat.py:31`; `base.py:52`; `lanczos_chebyshev.py:75` | **CONFLICT (24 vs 30)** |
| Lanczos m | `16` / `20` / `32` by call site | `m` | `lanczos_chebyshev.py:18,117`; `graph_heat.py:33,38`; `base.py:53` | multiple defaults |
| Diffusion t | `0.5` | `t` | `base.py:50` | — |
| Confidence α | `2.0` | `α` | `base.py:51` | — |
| Python math `_EPS` | `1e-12` | `ε` | `normalize.py:32`; `similarity.py:29`; `scoring.py:12` | consistent |
| Rust norm floor | `1e-10` | — | `mathcore.rs:252`; `bhdc.rs:148,362` | **CONFLICT with 1e-12** |
| numerics TINY_MIN | f32 `1e-6`, f64 `1e-12` | `TINY_MIN` | `numerics.py:18-21` | — |
| Calibration T clamp | `[0.05, 10]` | `T` | `temperature_scaling.py:89` | search bracket `[0.1, 5.0]` (line 67) |
| Calibration min_samples | `50` | — | `temperature_scaling.py:26` | — |
| Mahalanobis blend | `0.8 · cos_err + 0.2 · surprise` | — | `learning/prediction.py:344` | hard-coded |
| Mahalanobis α | `0.01` (Python) / ctor arg (Rust) | `α` | `learning/prediction.py:264`; `prediction.rs:76` | — |
| Mahalanobis var floor | `1e-6` | — | `learning/prediction.py:297` | — |
| FWHT scale | `1/√n` | — | `mathcore.rs:303` | — |
| BayesianMemory cov floor | `1e-6` | — | `mathcore.rs:394` | — |
| SDR dim / sparsity | `16384` / `0.01` (settings defaults, docstring) | `D, p` | `admin/core/sdr.py:16-17` (doc), read from settings at `58-65` | docstring vs settings key names |
| LSH bands / rows | `8 / 16` | — | `sdr.py:155` | — |
| LSH FNV constants | `1469598103934665603`, `0x9E3779B97F4A7C15`, `1099511628211` | — | `sdr.py:196-199` | — |
| Sigmoid clamp | `x ∈ [−20, 20]` | — | `amygdala.py:256` | — |
| Softmax τ floor | `0.01` | `τ_safe` | `mathcore.rs:209` | — |
| Entropy p floor | `1e-10` (Rust) / `1e-9` (annealing vec) | — | `mathcore.rs:220`; `annealing.py:316-319` | **CONFLICT** |

---

## 5. Invariants Actually Enforced

These are clamps/floors/guards present in code.

1. **Unit L2 norm after bind/unbind/bundle** — `rust_core/src/bhdc.rs:260-266,301-307,133-139`; `quantum.py:171-180` via `normalize_array` final pass (`numerics.py:263-273`).
2. **Cosine clipped to [−1, 1]** — `somabrain/math/similarity.py:93` and `182` (Python canonical only; Rust T21 does **not** clip).
3. **Cosine zero-norm → 0.0** — `similarity.py:84-85`; `mathcore.rs:252-253`; `bhdc.rs:148`.
4. **normalize_vector zero-norm → zero vector** — `normalize.py:82-83` (`eps=1e-12`).
5. **Wiener denominator regularized** — `k² + λ` with `λ > 0` (`bhdc.rs:296`; `quantum.py:316`).
6. **Unbind division-by-zero guarded (Python fallback)** — signed `1e-12` floor (`bhdc_encoder.py:123-124`).
7. **Unbind exact-zero frequency raises (test-only pure path)** — `quantum_pure.py:150-157`.
8. **Neuromodulator clamps** — DA [0.2, 0.8], 5HT [0, 1], NE [0, 0.1], ACh [0, 0.1] (`neuro.rs:84-87`).
9. **Adaptation weight clamps** — Python `_constrain` (`engine.py:441-449`) + `UtilityWeights.clamp` (`config.py:39-57`); Rust `.clamp(...)` (`adaptation.rs:169-179`).
10. **Tau floors** — Python `max(tau_min, ·)` after anneal (`annealing.py:212`); decay floor `0.05` (`annealing.py:254`); Rust `max(tau_min, ·)` (`adaptation.rs:261`); `set_tau` clamp [0.01, 10] (`adaptation.rs:202`); error-driven τ clamp [0.01, 10] (`engine.py:571-573`).
11. **Scorer weights clamped to [weight_min, weight_max]** — `learning/scoring.py:70-89`.
12. **Scorer total clamped to [0, 1]** after renormalisation over active terms — `learning/scoring.py:151-162` (FIXED, W5b — FD-off ceiling is 1.0).
13. **Salience clamped to [0, 1]** — `learning/salience.py:39`; `amygdala.py:183`; `wm_salience.py:58,140,179`.
14. **Recency boost clamped to [floor, 1]** — `math/recency.py:55` (single kernel, W5b).
15. **Density factor clamped to [floor, 1]** — `memory/scoring.py:202`; `builder.py:564`.
16. **Rescored hit score clamped to [0, 1]** — `memory/scoring.py:434`.
17. **FD residual/capture ratios clamped to [0, 1]** — `learning/salience.py:84,169-172`.
18. **FD decay ∈ (0, 1]** — constructor check `learning/salience.py:60-61`.
19. **Entropic sharpening never crashes** — `annealing.py:292-390` always returns; `engine.py:416` comment "INTEGRAL".
20. **Temperature fit clamped to [0.05, 10]** — `temperature_scaling.py:89`; NLL input `T ≥ 1e-6` (`:59`).
21. **Confidence/error blends clamped to [0, 1]** — `learning/prediction.py:344,416`.
22. **Amygdala soft-temperature floor `1e-4`** — `amygdala.py:244`; sigmoid input clamp ±20 (`:256`).
23. ~~**`compute_optimal_p` input clamp**~~ — function deleted (W4.2 / DEBT-012); no `p*` theorem exists.
24. **`compute_wiener_lambda` p clamp** — `p ∈ [0.01, 0.99]` (`mathcore.rs:325`).
25. **`quantize_8bit` output clamp** — scaled to [0, 255] (`mathcore.rs:341`).
26. **BayesianMemory η clamp** — `[0.01, 0.5]` (`mathcore.rs:377`).
27. **BHDC active_count clamp** — `[1, D]` (`bhdc.rs:76`; `bhdc_encoder.py:23`).
28. **FWHT power-of-two guard** — non-power-of-two length raises `ValueError` (`mathcore.rs` `fwht_inplace`; `bhdc_encoder.py` `fwht`). Never a silent no-op (FIXED, W4.4).
29. **Reciprocal-tau guard** — `max(tau, 1e-6)` in softmax weights (`builder.py:357`).
30. **Finite-value repair** — non-finite normalizer outputs replaced by baseline (`numerics.py:275-280`).

---

## 6. Invariants Docs Claim but Code Does NOT Enforce

| Claim | Where claimed | What code actually does |
|---|---|---|
| "Perfect binding invertibility" | `somabrain/admin/core/quantum.py:8-9` | Production `bind` is FFT convolution (T8) with Wiener-regularized inverse (T9); recoverability is approximate and λ-dependent. `unbind(bind(a,b),b) ≈ a` is documented with "similarity > 0.95" (`quantum.py:287`) but **no assertion or check** enforces 0.95. |
| "\|H_k\| ≈ 1 for all operations" | `quantum.py:8` | `bind`/`unbind` normalize output L2 norm to 1; they do **not** enforce unit spectral magnitude per frequency bin. Spectral checks only *record metrics* (`quantum.py:261-263,538-544`). |
| "Role orthogonality" | `quantum.py:10` | Roles are only *checked* via cosine metric emission (`quantum.py:358-369`); non-orthogonal roles are still cached and used. No rejection. |
| "normalize.py is the ONLY implementation of vector normalization" | `somabrain/math/normalize.py:17-20` | `normalize_array` in `somabrain/admin/core/numerics.py:117-282` is live on the HRR path and is *not* a redirect to `normalize.py`. |
| "similarity.py is the ONLY implementation of cosine similarity" | `somabrain/math/similarity.py:15-18` | Rust `cosine_similarity` (`mathcore.rs:245-257`) and `BHDCEncoder::similarity` (`bhdc.rs:144-149`) implement cosine with a different ε and no clamp. |
| Binding is "BHDC permutation binding" | `quantum.py:1-12` | `QuantumLayer.bind` uses FFT circular convolution (`quantum.py:254-258`). Permutation binding is only in `bind_unitary` (`quantum.py:392`). |
| λ\* = Δ² / (12 p (1−p)) at production p | `bhdc.rs`, `bhdc_encoder.py`, `quantum.py`, `brain_settings/models.py` | **FIXED (W4.1).** All regularizer defaults come from `compute_wiener_lambda(p, 8)`. The former p=0.5-only constant and the former `1e-4` fallback are deleted. |
| Monotonic annealing `τ_{t+1} ≤ τ_t` "always" | `LEARNING_MATHEMATICAL_PROOF.md:374` | Python linear anneal multiplies by (1−rate) only when mode is configured (`annealing.py:192-212`); exponential mode is a **no-op** per feedback (`annealing.py:199-201`); tau can also *increase* under builder diversity adaptation (`builder.py:373-376`) and be restored by entropy sharpening magnitude restore (`annealing.py:368-370`). |
| Entropy `H = −Σ p log₂ p` with `p = softmax(w)` | `LEARNING_MATHEMATICAL_PROOF.md:185-190` | Code uses `p_i = w_i/Σw` (linear) and natural log (`annealing.py:315-325`; `mathcore.rs:218-223`). |
| "Mahalanobis distance" | `prediction.rs` (`MahalanobisPredictor`); `learning/prediction.py:247-253` docstring | **FIXED (W4.6).** Rust implements the diagonal Mahalanobis `sqrt(Σ (x−μ)²/σ²)` with EWMA mean/var (same rule as Python). Python `_mahal_bounded` squashes `d²` to `[0,1)`; both are the diagonal metric. |
| `compute_wiener_lambda(p, bits)` honors `bits` | `mathcore.rs` (`compute_wiener_lambda`) | **FIXED (W4.1).** `Δ = 2/(2^bits − 1)`; `bits` is read. |
| Unbind is Wiener on all paths | `bhdc.rs` docs | **FIXED (W4.3).** Python fallback `_PythonPermutationBinder.unbind` is `(c ⊙ π(b)) / (π(b)² + λ*)` plus optional FWHT — identical to the Rust rule. |
| Deterministic BHDC vectors across backends | `bhdc_encoder.py:3-7` "matches Python API" | Seed composition (T4 vs T4b) and `pm_one` inactive fill (T3 vs T3b) differ between Rust and Python fallback. Same key → different vector. |
| "Perfect binding invertibility" for sparse BHDC | `quantum.py:9`; `bhdc.rs:245-250` comments | Sparse `{−1,0,+1}` products are **not** algebraically invertible under zeros; T7 exists precisely because of this. |
| Confidence `exp(-α·error)` uses MSE of salience | `base.py:63` contract | Implemented as stated (T63) — **this claim matches**; listed only to confirm. No issue. |
| Entropy cap "never crashes" and preserves semantics | `annealing.py:301-302` | It does not crash, but magnitude restore uses `α+β+γ+τ` (`annealing.py:369-370`) which **changes** relative scale of τ vs weights; builder variant does **not** restore magnitude (`builder.py:428-438`). Two behaviors, one claim. |
| `SlowPredictor` "predictor" semantics (Rust) | `prediction.rs:23-28` | Returns the **last input**, not a model prediction. |
| `BudgetedPredictor` enforces a time budget (Rust) | `prediction.rs:46-62` | No timer; returns input if `timeout_ms ≥ 10`. |
| `LLMPredictor` predicts via LLM (Rust) | `prediction.rs:96-112` | Returns constant `[0.0]`. |

---

## Appendix A — FALSE CLAIMS in Existing Proof Documents

> The following documents are **not** sources of truth. Each claim is quoted and contradicted by the cited code.

### A.1 `LEARNING_MATHEMATICAL_PROOF.md`

| # | Quoted claim | Contradicting code |
|---|---|---|
| A1.1 | "`p_i = exp(w_i) / Σ exp(w_j)`" and "`H = -Σ p_i × log₂(p_i)`" (lines 185-190) | Code computes `p_i = vec_i / sum(vec)` with `vec = max(1e-9, w)` — **linear normalization, not softmax** (`somabrain/learning/annealing.py:315-322`). Entropy uses `p.ln()` / `math.log` — **natural log, not log2** (`rust_core/src/mathcore.rs:218-223`; `annealing.py:61,325`). |
| A1.2 | "τ_{t+1} = max(τ_floor, τ_t × (1 - anneal_rate))" presented as **the** temperature annealing law (lines 50-52, 128-131) | Python `"linear"` mode is `τ·(1−rate)` (`annealing.py:202-204`) but `"exponential"` mode is a **no-op** per feedback (`annealing.py:199-201`). Rust `"linear"` is **`τ − rate`** (subtractive) (`rust_core/src/adaptation.rs:250`). The document presents one law where code has three inconsistent ones. |
| A1.3 | "Monotonic Annealing: `τ_{t+1} <= τ_t` (always)" (line 374) | τ can **increase** when duplicate-ratio is high: `τ ← min(τ + inc_up·excess, τ_max)` (`somabrain/context/builder.py:373-376`). Entropy sharpening restores magnitude by `×(α+β+γ+τ)` (`annealing.py:368-370`), which can raise τ above its pre-sharpen value. |
| A1.4 | Worked example "α: 1.0 → 1.025" with `gain_α = 0.5` (lines 104-124) | Coded `gain_α` default is **1.0**, not 0.5 (`somabrain/learning/config.py:76-78`; `settings/cognitive.py:350-352`). Rust default is **0.1** (`rust_core/src/adaptation.rs:118`). Neither is 0.5. |
| A1.5 | "α ≈ 2.25" after 50 positive rewards; "final_alpha ≈ 2.25 (125% increase)" (lines 157-176, 330-333) | Update is `α ← clamp(α + lr·gain_α·signal, 0.1, 5.0)` (`engine.py:369-372`). With lr=0.05, gain=1.0, signal=1.0: after 50 steps α = 1.0 + 50×0.05 = **3.5**, then clamped path differs if τ/entropy intervenes. 2.25 is not produced by the coded formula for any default combination in scope. |
| A1.6 | "gamma: 0.1 → 0.1025 (increased by 2.5%)" with positive reward (lines 137-138) | Coded `gain_γ` default is **−0.5** (`learning/config.py:79-81`; `settings/cognitive.py:353-355`). Positive reward **decreases** γ under defaults. |
| A1.7 | "Constraints … α_max=5.0" example clamps (lines 122-123, 269-277) | Python bounds match ([0.1, 5.0], `config.py:139-144`) but Rust engine clamps α to **[0.1, 2.0]** and λ to **[0.1, 2.0]** (`rust_core/src/adaptation.rs:113-116`). Document quotes only one of the two live/ABI learners. |
| A1.8 | "Temperature annealing makes the brain exploit more over time" with P = exp(score/τ)/Σ (lines 213-245) | Softmax-with-τ is implemented in `mathcore.rs:205-214` and `builder.py:355-357`, but the adaptation engine's τ **does not feed those formulas in the cited learning path**; τ annealing in `engine.py:393-429` mutates τ with no corresponding probability distribution in that module. |
| A1.9 | "Verified across 1500+ random test cases with zero failures" / "Success rate: 100% (19/19 tests passed)" (lines 326, 383, 410) | Not an equation claim. Tests, if present, do not change the fact that the formulas quoted in A1.1–A1.6 are not the formulas in production source. Code is source of truth. |
| A1.10 | "delta = lr × gain × signal" as "the" learning formula (lines 26-28, 322-326) | There is no standalone `delta` function. The update is an inline five-parameter clamp at `engine.py:369-386` / `adaptation.rs:169-179`, with **different gains and bounds** in each. |

### A.2 `SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md`

| # | Quoted claim | Contradicting code |
|---|---|---|
| A2.1 | "Tau Exponential Annealing: `tau_{t+1} = max(floor, tau_t × (1 - rate))`" (lines 144-167, 203) | That multiplicative law is the Python **`"linear"`** mode (`annealing.py:202-204`) or Rust **`"step"`** mode (`adaptation.rs:252-257`). Coded exponential is `τ·exp(−rate)` (Rust, `adaptation.rs:251`) or a **no-op** (Python, `annealing.py:199-201`). The label "exponential" is false. |
| A2.2 | "Learning Adaptation MATHEMATICALLY PROVEN" / "mathematically proven to work correctly" (lines 11-17, 278) | Property tests can only assert the formula they encode. The formulas they quote (A2.1) are not the production formulas (T25 vs T25b). Proof of the wrong identity is not proof of the system. |
| A2.3 | "Conflict = 1 - recall_strength" / "Policy.use_graph = True when conflict > threshold" / "inhibit_act = (conflict >= 0.9)" (lines 42-44, 207-209) | No such equations appear in the DOC-A2 scope files. These belong to cognition workbench code outside the extracted math surface and are **unverified here**; they must not be treated as part of the verified math core. |
| A2.4 | "Round-Trip Preservation: `recall(remember(x)) ≈ x` (Verified ✅)" (line 213) | Production unbind is Wiener-regularized (T9) or regularized permutation division (T7); both are approximate and λ-dependent. `≈` is not quantified and no tolerance is enforced in code. |
| A2.5 | "No mocks. No fakes. No bullshit." (lines 5, 19, 287) | `rust_core/src/prediction.rs:109-111` (`LLMPredictor`) returns constant `[0.0]`; `BudgetedPredictor` (`prediction.rs:57-62`) returns its input without timing. Those are stubs in the same math core this report claims is production-verified. |
| A2.6 | "19/19 Core Tests PASSED" as evidence the brain "WORKS FLAWLESSLY" (lines 3, 13) | Passing tests that encode A2.1's wrong anneal identity cannot certify (T25)/(T25b). See A2.1. |
| A2.7 | "Brier score (0-1, lower is better)" implied as verified calibration (report §memory/calibration context) | Coded Brier is `mean((conf−acc)²)` (`temperature_scaling.py:164`) with no bound enforcement in the function; inputs are clipped only in `fit` (`:47`). |

### A.3 Summary for math-perfection work

The following are the **highest-priority discrepancies** if the goal is to make SomaBrain WORK:

1. **Two live annealing laws** (T25 vs T25b) with different `linear` semantics and different `exponential` behavior.
2. **Two live entropy-cap sharpeners** (T28 vs T28b) with different shrink schedules and magnitude handling.
3. ~~**Two live Wiener λ constants**~~ — **RESOLVED (W4.1):** one formula source `compute_wiener_lambda(p, 8)` everywhere.
4. **Two live binding algebras** under one class: FFT HRR (T8/T9) vs permutation BHDC (T6/T7), with a docstring that claims the latter for the former.
5. **Rust vs Python fallback disagree** on seeds (T4/T4b) and vector fill (T3/T3b). Unbind now agrees (W4.3).
6. **Rust vs Python adaptation disagree** on gains and bounds (T23 vs T23b).
7. **Neuromodulator baselines disagree** (Rust 0.5/0.05/0.05 vs settings 0.4/0.0/0.0).
8. **Entropy of weights is not softmax entropy** (linear-normalized natural log) — any prior "proof" using softmax/log2 is void.

---

*End of document SOMA-BR-MATH-TRUTH-001 v1.0.0. Every equation above maps to a cited line range in production source. No aspirational mathematics is included in §§1–5.*
