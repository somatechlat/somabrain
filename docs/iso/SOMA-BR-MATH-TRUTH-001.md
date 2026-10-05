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
| `somabrain/admin/brain/neuromodulators.py`, `somabrain/runtime/neuromodulators.py`, `somabrain/admin/cognitive/amygdala.py` | Neuromodulator hubs, adaptive feedback, amygdala salience |
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
| `λ`, `lambda`, `lambda_reg` | Wiener ridge regularizer | `2.05e-5` (binder default); `1e-4` (quantum unbind fallback) | `rust_core/src/bhdc.rs:217`; `somabrain/math/bhdc_encoder.py:226`; `somabrain/admin/core/quantum.py:311-313` |
| `Δ` | quantization step on `[-1,1]` | `2/255` hard-coded | `rust_core/src/mathcore.rs:327` |
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
| `m = (m₁…m₄)` | dopamine, serotonin, noradrenaline, acetylcholine | see §4 | `rust_core/src/neuro.rs:44-48` |
| `k_d`, `k_r`, `bias`, `u_scale` | neuromod dynamics coefficients | `[0.8,0.3,0.1,0.2]`, `[0.1,0.2,0.3,0.4]`, `0`, `0.1` | `rust_core/src/neuro.rs:32-52` |
| `ε`, `_EPS`, `tiny` | numerical floor | `1e-12` (Python math), `1e-10` (Rust), `1e-6`/`1e-12` (numerics dtype) | see §4 |
| `K` | Chebyshev degree | `24` default; `30` in `PredictorConfig` | `somabrain/math/graph_heat.py:31`; `somabrain/predictors/base.py:52` |
| `m_L`, `lanczos_m` | Lanczos steps | `16`/`20`/`32` by call site | `somabrain/math/lanczos_chebyshev.py:18`; `somabrain/math/graph_heat.py:33,38` |
| `t`, `diffusion_t` | heat diffusion time | `0.5` | `somabrain/predictors/base.py:50` |
| `α_ppr` | APPR teleport | `0.85` | `somabrain/math/appr.py:18` |
| `eps_ot` | Sinkhorn entropy regularization | `1e-2` | `somabrain/math/sinkhorn.py:16` |
| `φ` | golden-section ratio | `(√5−1)/2` | `somabrain/calibration/temperature_scaling.py:68` |
| `T_cal` | calibration temperature | fitted; clamp `[0.05, 10]` | `somabrain/calibration/temperature_scaling.py:89` |
| `b` | quantization bits | param present; **ignored** in `compute_wiener_lambda` | `rust_core/src/mathcore.rs:324-332` |
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
v ← v / √n          # only if n is a power of 2; else early return unchanged
```
- **file:line** `rust_core/src/mathcore.rs:283-307` (public wrapper `fwht` at `276-280`)
- **Status:** LIVE (used by `PermutationBinder` when `mix == "hadamard"`, `rust_core/src/bhdc.rs:256-257,281-282`)
- **Note:** Non-power-of-two `n` returns the input unchanged (`mathcore.rs:285-287`) — silent no-op, not an error.

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
v̂_i = (c_i · b′_i) / (b′_i² + λ)        # λ = lambda_reg, default 2.05e-5
v̂  = v̂ / ‖v̂‖                             # if ‖v̂‖ > 1e-10
```
- **file:line** `rust_core/src/bhdc.rs:277-309`
- **Status:** LIVE (via `QuantumLayer.unbind_exact_unitary`, `somabrain/admin/core/quantum.py:421-431`)
- **DOC-DRIFT vs Python fallback (T7b):** Python fallback unbind is plain division `c / π(b)` with a ±1e-12 sign-preserving tiny (`somabrain/math/bhdc_encoder.py:119-126`) — **not** Wiener. Different inverse.

**(T7b) PermutationBinder unbind (Python fallback, non-Wiener)**
```
b′ = π(b)
denom_i = b′_i  if |b′_i| ≥ 1e-12  else  sign(b′_i)·1e-12
v̂ = c / denom
```
- **file:line** `somabrain/math/bhdc_encoder.py:119-126`
- **Status:** LIVE-FALLBACK

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
λ  = BrainSetting("gmd_lambda_reg") or 1e-4
fa = fc · conj(fb) / (|fb|² + λ)
a  = irfft(fa, n=D);  a = normalize_array(a)
```
- **file:line** `somabrain/admin/core/quantum.py:283-322` (core at `302-322`)
- **Status:** LIVE
- **Note:** Docstring claims `unbind(bind(a,b),b) ≈ a` with "similarity > 0.95" (`quantum.py:287`) — that threshold is **not** enforced anywhere in this function.

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

**(T12) Optimal sparsity `p*`**
```
p* = (1 + √clamp(δ, 1e-4, 1−1e-4)) / 2
```
- **file:line** `rust_core/src/mathcore.rs:313-316`
- **Status:** EXPORTED (`compute_optimal_p`). Comment claims "p* ≈ 0.1 recommended" (`mathcore.rs:311`) which is **not** what this formula returns for small δ (e.g. δ=0.01 → p*≈0.55). Comment is wrong; formula is as written.

**(T13) Wiener ridge `λ*` (as coded)**
```
Δ = 2/255                         # hard-coded; argument `bits` is IGNORED
σ_ε² = Δ² / 12
σ_v² = clamp(p, 0.01, 0.99) · (1 − clamp(p, 0.01, 0.99))
λ*   = σ_ε² / σ_v²                # ≈ 5.126e-6 / (p(1−p))
```
- **file:line** `rust_core/src/mathcore.rs:324-332`
- **Status:** EXPORTED (`compute_wiener_lambda`)
- **Note:** At `p = 0.5`, `λ* = Δ²/3 = (2/255)²/3 ≈ 2.0505e-5`, which is the constant hard-coded as `lambda_reg` default in T7. The comment "λ* = (2/255)²/3" (`bhdc.rs:209`) is therefore **only true at p = 0.5**, not the general (T13) formula.

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

**(T32) Neuromodulator dynamics (Rust ODE step)**
```
ẋ_i = k_d[i] · x_i − k_r[i] · m_i + bias[i] + u_scale · u_i
m_i ← m_i + ẋ_i · dt
clamps: dopamine ∈ [0.2, 0.8]
        serotonin ∈ [0.0, 1.0]
        noradrenaline ∈ [0.0, 0.1]
        acetylcholine ∈ [0.0, 0.1]
```
- **file:line** `rust_core/src/neuro.rs:70-90` (defaults `32-52`)
- **Status:** EXPORTED; Python hubs sync state to Rust when available (`somabrain/admin/brain/neuromodulators.py:123-153`, same in `somabrain/runtime/neuromodulators.py:125-155`)

**(T33) Adaptive neuromod feedback (Python)**
```
f_dopamine = success_rate + DOPAMINE_BIAS [+ DOPAMINE_REWARD_BOOST if task=="reward_learning"]
f_serotonin = 1 − error_rate
f_norad = min( NORAD_MAX,
               (1 / max(latency_floor, latency)) · LATENCY_SCALE
               + URGENCY_FACTOR·[task=="urgent"] )
f_acetyl = accuracy · ACCURACY_SCALE + MEMORY_FACTOR·[task=="memory"]
```
- **file:line** `somabrain/admin/brain/neuromodulators.py:322-384` (duplicate body `somabrain/runtime/neuromodulators.py:324-386`)
- **Status:** LIVE (via `AdaptiveNeuromodulators.update_from_performance`)

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
s ← s + acetylcholine
s = clamp(s, 0, 1)
```
- **file:line** `somabrain/admin/cognitive/amygdala.py:125-183`
- **Status:** LIVE

**(T35) Amygdala gates**
```
th_store = threshold_store + noradrenaline − hysteresis·[last_store]
th_act   = threshold_act   + noradrenaline − hysteresis·[last_act]
hard:  do_store = (s ≥ th_store);  do_act = (s ≥ th_act)
soft:  p = σ( (s − th) / T ),  T = max(1e-4, soft_temperature)
       σ(x) = 1/(1+e^{−x}) with x clamped to [−20, 20]
       do_* = (p ≥ 0.5)
```
- **file:line** `somabrain/admin/cognitive/amygdala.py:185-278` (thresholds `263-278`, sigmoid `244-261`)
- **Status:** LIVE

**(T36) Rust Amygdala linear salience / gate**
```
salience = w₀·novelty + w₁·error + w₂·energy
gate     = (salience > threshold)
```
- **file:line** `rust_core/src/neuro.rs:156-162`
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
score = clamp( w_cosine·cos(q,c) + w_fd·cos(P q, P c) + w_recency·exp(−age/τ_rec) , 0, 1 )
```
with `cos` from (T15); `P` = FD projection (T38); if no FD backend, `w_fd` term = 0; if `recency_steps is None`, recency term = 0. Weights themselves are read from settings and clamped to `[weight_min, weight_max]` (`scoring.py:63-73,78-97`).
- **file:line** `somabrain/admin/core/learning/scoring.py:133-169` (components `104-131`)
- **Status:** LIVE
- **Note:** Constructor args `w_cosine,w_fd,w_recency` are **ignored**; values come from `SOMABRAIN_SCORER_*` settings (`scoring.py:64-72`).

**(T40) Working-memory salience**
```
novelty  = 1 − max_i cos(q, v_i)                 # 1.0 if empty / zero-norm
recency  = 1 − cos(q, v_last)                    # query salience
s_query  = clamp( α·novelty + β·reward + γ·recency, 0, 1 )
s_item   = clamp( α·novelty + γ·item.recency, 0, 1 )
s_evict  = clamp( α·novelty + γ·exp(−age/recency_scale), 0, 1 )
```
- **file:line** `somabrain/memory/wm/wm_salience.py:27-58` (query), `108-140` (item), `143-179` (evict), novelty `82-105`
- **Status:** LIVE

**(T41) Recall recency features**
```
normalised   = age_seconds / max(scale, 1e-6)
recency_steps = min( log1p(normalised)·sharpness , cap )
damp         = exp( −normalised^sharpness )
boost        = clamp(damp, floor, 1)
```
defaults: `scale=60`, `cap=1000`, `sharpness=1.2`, `floor=0.05`.
- **file:line** `somabrain/memory/scoring.py:134-161` (profile `105-131`)
- **Status:** LIVE

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
- **file:line** `somabrain/memory/scoring.py:227-266` (rank), `349-441` (rescore)
- **Status:** LIVE

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
e = 1 − |cos(pred, actual)|     if both norms > 0
e = 1                           otherwise
```
- **file:line** `rust_core/src/prediction.rs:37-42`
- **Status:** EXPORTED

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
mean ← (1−α)·mean + α·x          # covariance stored but UNUSED
distance = ‖x − mean‖₂            # Euclidean, not Mahalanobis
```
- **file:line** `rust_core/src/prediction.rs:84-93`
- **Status:** EXPORTED
- **DOC-DRIFT:** Named `MahalanobisPredictor` but computes plain L2 distance; `covariance` field is `#[allow(dead_code)]` (`prediction.rs:68-69`).

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
A′ = (2A − (b+a)I)/(b−a)
nodes_k = cos( π(k−0.5)/K ),  k=1..K
λ_k = (b−a)/2 · nodes_k + (b+a)/2
f_k = exp(−t λ_k)
c_k = (2/K) Σ f_j cos(k · arccos(nodes_j));  c_0 ← c_0/2
y = Σ_{k=0}^{K} c_k T_k(A′) x        # Clenshaw recurrence
```
- **file:line** `somabrain/math/lanczos_chebyshev.py:57-113` (coeffs `93-103`, Clenshaw `105-113`)
- **Status:** LIVE

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
| T1 | binding | LIVE | `mathcore.rs:283-307` |
| T2 | binding | LIVE | `bhdc.rs:69,76` |
| T3 | binding | LIVE | `bhdc.rs:166-195` |
| T3b | binding | LIVE-FALLBACK | `bhdc_encoder.py:59-71` |
| T4 | binding | LIVE | `bhdc.rs:14-40` |
| T4b | binding | LIVE-FALLBACK | `bhdc_encoder.py:49-57` |
| T5 | binding | EXPORTED | `bhdc.rs:111-141` |
| T6 | binding | LIVE | `bhdc.rs:252-268` |
| T7 | binding | LIVE | `bhdc.rs:277-309` |
| T7b | binding | LIVE-FALLBACK | `bhdc_encoder.py:119-126` |
| T8 | binding | LIVE | `quantum.py:254-259` |
| T9 | binding | LIVE | `quantum.py:302-322` |
| T10 | binding | TEST-ONLY | `quantum_pure.py:121-161` |
| T11 | binding | EXPORTED | `mathcore.rs:338-344` |
| T12 | binding | EXPORTED | `mathcore.rs:313-316` |
| T13 | binding | EXPORTED | `mathcore.rs:324-332` |
| T14 | binding | EXPORTED | `bhdc.rs:418-419` |
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
| T32 | neuromod | EXPORTED | `neuro.rs:70-90` |
| T33 | neuromod | LIVE | `admin/brain/neuromodulators.py:322-384` |
| T34 | neuromod | LIVE | `amygdala.py:125-183` |
| T35 | neuromod | LIVE | `amygdala.py:185-278` |
| T36 | neuromod | EXPORTED | `neuro.rs:156-162` |
| T37 | memory | LIVE | `learning/salience.py:35-39` |
| T38 | memory | LIVE | `learning/salience.py:71-192` |
| T39 | memory | LIVE | `learning/scoring.py:133-169` |
| T40 | memory | LIVE | `wm_salience.py:27-179` |
| T41 | memory | LIVE | `memory/scoring.py:134-161` |
| T42 | memory | LIVE | `memory/scoring.py:164-202` |
| T43 | memory | LIVE | `memory/scoring.py:227-441` |
| T44 | memory | LIVE | `builder.py:315-464` |
| T45 | memory | LIVE | `context_hrr.py:92-239` |
| T46 | memory | LIVE | `context_hrr.py:107-128` |
| T47 | annealing | EXPORTED | `adaptation.rs:193-195` |
| T48 | annealing | EXPORTED | `mathcore.rs:205-241` |
| T49 | prediction | EXPORTED | `prediction.rs:37-42` |
| T50 | prediction | LIVE | `learning/prediction.py:100-423` |
| T51 | prediction | LIVE | `learning/prediction.py:275-347` |
| T52 | prediction | EXPORTED | `prediction.rs:84-93` |
| T53 | prediction | EXPORTED | `prediction.rs:131-216` |
| T54 | prediction | EXPORTED | `prediction.rs:23-28` |
| T55 | prediction | DEAD-STUB | `prediction.rs:109-111` |
| T56 | prediction | DEAD-STUB | `prediction.rs:57-62` |
| T57 | calibration | LIVE | `temperature_scaling.py:33-91` |
| T58 | calibration | LIVE | `temperature_scaling.py:93-100` |
| T59 | calibration | LIVE | `temperature_scaling.py:103-200` |
| T60 | cognition | LIVE | `lanczos_chebyshev.py:17-54` |
| T61 | cognition | LIVE | `lanczos_chebyshev.py:57-113` |
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

Values are the coded defaults. "Appears in" lists every site found in the scope files (and settings sources they read).

| Constant | Value | Symbol | Appears in | Duplicate? |
|---|---|---|---|---|
| Wiener λ binder default | `2.05e-5` | `lambda_reg` | `rust_core/src/bhdc.rs:217`; `somabrain/math/bhdc_encoder.py:92,226`; `somabrain/brain_settings/models.py:219` (`gmd_lambda_reg`) | **YES** — see λ fallback |
| Wiener λ unbind fallback | `1e-4` | `lambda_reg` | `somabrain/admin/core/quantum.py:311-313` | **CONFLICT with 2.05e-5** |
| λ\* closed form | `(2/255)²/(12 p(1−p))` | `λ*` | `rust_core/src/mathcore.rs:324-332` | Comment claims `(2/255)²/3` which equals λ\* only at p=0.5 |
| Quantization Δ | `2/255 ≈ 0.007843` | `Δ` | `rust_core/src/mathcore.rs:327` | — |
| Quantization bits | `8` | `bits` | `brain_settings/models.py:220`; param of `compute_wiener_lambda` **ignored** | parameter dead |
| BayesianMemory η | `0.08` (DB), clamp `[0.01,0.5]` | `η` | `brain_settings/models.py:225-231`; `mathcore.rs:377` | — |
| BayesianMemory α (capacity) | `640.0` | `α` | `mathcore.rs:379`; `brain_settings/models.py:218` | unused in formulas |
| GMD δ (max pairwise sim) | `0.01` | `δ` | `brain_settings/models.py:216` | not read by mathcore |
| GMD ε (collision) | `0.05` | `ε` | `brain_settings/models.py:217` | not read by mathcore |
| BHDC sparsity | `0.1` | `p` | `settings/cognitive.py:264`; `settings/django_core.py:45,65` | consistent |
| HRR dim | `8192` (brain_settings); env-dependent | `D` | `brain_settings/models.py:221` | — |
| Global seed | `42` | `seed` | `brain_settings/models.py:223` | Dropout seed also 42 (`mathcore.rs:138`) |
| Retrieval α/β/γ/τ | `1.0 / 0.2 / 0.1 / 0.7` | — | `settings/cognitive.py:178-181`; `adaptation.rs:24`; `engine.py:244` | consistent |
| Utility λ/μ/ν | `1.0 / 0.1 / 0.05` | — | `learning/config.py:29-37`; `adaptation.rs:62` | consistent |
| Adaptation gains (Python) | `1.0, −0.5, 1.0, −0.25, −0.25` | `gain_*` | `learning/config.py:76-90`; `settings/cognitive.py:350-360` | **CONFLICT with Rust** |
| Adaptation gains (Rust) | `0.1, 0.05, 0.1, 0.05, 0.02` | `gain_*` | `rust_core/src/adaptation.rs:118-122` | **CONFLICT with Python** |
| Adaptation bounds (Python) | α∈[0.1,5], γ∈[0,1], λ∈[0.1,5], μ∈[0.01,5], ν∈[0.01,5] | — | `learning/config.py:139-168`; `settings/cognitive.py:362-383` | **CONFLICT with Rust** |
| Adaptation bounds (Rust) | α∈[0.1,2], γ∈[0,1], λ∈[0.1,2], μ∈[0,0.5], ν∈[0,0.2] | — | `rust_core/src/adaptation.rs:113-117` | **CONFLICT with Python** |
| adapt_lr | `0.05` (min 0, max 0.25) | `lr` | `brain_settings/models.py:232-238`; `adaptation.rs:105` | — |
| Scorer weights | `0.6 / 0.25 / 0.15` | `w_*` | `settings/cognitive.py:170-172` | constructor args ignored |
| Salience dense weights | `0.6 / 0.4 / 0.0` | `w_novelty, w_error, w_fd` | `learning/salience.py:30-32` | — |
| Amygdala soft T | settings default `0.1`, floor `1e-4` | `T` | `amygdala.py:79-82,244` | — |
| Amygdala FD energy floor | `0.9` | `fd_energy_floor` | `amygdala.py:83-86` | — |
| Dopamine base | **`0.5`** (Rust) / **`0.4`** (settings) | `m₁` | `neuro.rs:45` vs `settings/neuro.py:10` | **CONFLICT** |
| Serotonin base | `0.5` both | `m₂` | `neuro.rs:46`; `settings/neuro.py:11-13` | consistent |
| Noradrenaline base | **`0.05`** (Rust) / **`0.0`** (settings) | `m₃` | `neuro.rs:47` vs `settings/neuro.py:14` | **CONFLICT** |
| Acetylcholine base | **`0.05`** (Rust) / **`0.0`** (settings) | `m₄` | `neuro.rs:48` vs `settings/neuro.py:15` | **CONFLICT** |
| Neuromod clamps | DA [0.2,0.8], 5HT [0,1], NE [0,0.1], ACh [0,0.1] | — | `neuro.rs:84-87`; `settings/neuro.py:18-31` | consistent |
| Neuromod `k_d` | `[0.8, 0.3, 0.1, 0.2]` | `k_d` | `neuro.rs:34` | brain_settings names exist, not auto-loaded into Rust |
| Neuromod `k_r` | `[0.1, 0.2, 0.3, 0.4]` | `k_r` | `neuro.rs:38` | — |
| Neuromod `u_scale` | `0.1` | `u_scale` | `neuro.rs:29,52` | — |
| Entropy sharpen rate | `0.8` | `sharpen_rate` | `annealing.py:339`; `brain_settings/models.py:399` | builder variant uses adaptive scale (T28b) |
| Entropy final sharpen | `0.05` | `final_sharpen` | `annealing.py:340`; `brain_settings/models.py:400`; `builder.py:424` | consistent |
| tau_min | **`0.05`** / **`0.01`** | `τ_min` | `annealing.py:254,102,108` vs `adaptation.rs:202` vs `engine.py:571-573` | **CONFLICT (3 values)** |
| Recency half-life | `60.0` | `scale` | `memory/scoring.py:96-98`; `settings/cognitive.py:182` | consistent |
| Recency sharpness | `1.2` | `sharpness` | `memory/scoring.py:115-121`; `builder.py:145-146` | consistent |
| Recency floor | `0.05` | `floor` | `memory/scoring.py:122-130`; `builder.py:147-149` | consistent |
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
11. **Scorer weights clamped to [weight_min, weight_max]** — `learning/scoring.py:78-97`.
12. **Scorer total clamped to [0, 1]** — `learning/scoring.py:164`.
13. **Salience clamped to [0, 1]** — `learning/salience.py:39`; `amygdala.py:183`; `wm_salience.py:58,140,179`.
14. **Recency boost clamped to [floor, 1]** — `memory/scoring.py:160`; `builder.py:537`.
15. **Density factor clamped to [floor, 1]** — `memory/scoring.py:202`; `builder.py:564`.
16. **Rescored hit score clamped to [0, 1]** — `memory/scoring.py:434`.
17. **FD residual/capture ratios clamped to [0, 1]** — `learning/salience.py:84,169-172`.
18. **FD decay ∈ (0, 1]** — constructor check `learning/salience.py:60-61`.
19. **Entropic sharpening never crashes** — `annealing.py:292-390` always returns; `engine.py:416` comment "INTEGRAL".
20. **Temperature fit clamped to [0.05, 10]** — `temperature_scaling.py:89`; NLL input `T ≥ 1e-6` (`:59`).
21. **Confidence/error blends clamped to [0, 1]** — `learning/prediction.py:344,416`.
22. **Amygdala soft-temperature floor `1e-4`** — `amygdala.py:244`; sigmoid input clamp ±20 (`:256`).
23. **`compute_optimal_p` input clamp** — `δ ∈ [1e-4, 0.9999]` (`mathcore.rs:314`).
24. **`compute_wiener_lambda` p clamp** — `p ∈ [0.01, 0.99]` (`mathcore.rs:325`).
25. **`quantize_8bit` output clamp** — scaled to [0, 255] (`mathcore.rs:341`).
26. **BayesianMemory η clamp** — `[0.01, 0.5]` (`mathcore.rs:377`).
27. **BHDC active_count clamp** — `[1, D]` (`bhdc.rs:76`; `bhdc_encoder.py:23`).
28. **FWHT power-of-two guard** — non-power-of-two returns input unchanged (`mathcore.rs:285-287`) — enforced as a silent no-op, **not** as an error.
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
| λ\* = (2/255)²/3 | `bhdc.rs:209,290`; `bhdc_encoder.py:226` | General coded λ\* is `(2/255)²/(12 p(1−p))` (`mathcore.rs:324-332`). The quoted constant equals λ\* only at p = 0.5. Quantum unbind further falls back to `1e-4` (`quantum.py:311-313`). |
| Monotonic annealing `τ_{t+1} ≤ τ_t` "always" | `LEARNING_MATHEMATICAL_PROOF.md:374` | Python linear anneal multiplies by (1−rate) only when mode is configured (`annealing.py:192-212`); exponential mode is a **no-op** per feedback (`annealing.py:199-201`); tau can also *increase* under builder diversity adaptation (`builder.py:373-376`) and be restored by entropy sharpening magnitude restore (`annealing.py:368-370`). |
| Entropy `H = −Σ p log₂ p` with `p = softmax(w)` | `LEARNING_MATHEMATICAL_PROOF.md:185-190` | Code uses `p_i = w_i/Σw` (linear) and natural log (`annealing.py:315-325`; `mathcore.rs:218-223`). |
| "Mahalanobis distance" | `prediction.rs:66` name; `learning/prediction.py:247-253` docstring | Rust computes Euclidean `‖x−μ‖` (`prediction.rs:90-93`); covariance unused. Python computes a **diagonal-variance** quadratic form, not full Mahalanobis (`learning/prediction.py:299-318`). |
| `compute_wiener_lambda(p, bits)` honors `bits` | signature `mathcore.rs:324` | `bits` is never read; Δ is hard-coded `2/255` (`mathcore.rs:327`). |
| Unbind is Wiener on all paths | `bhdc.rs:270-276` docs | Python fallback `_PythonPermutationBinder.unbind` is plain signed division (`bhdc_encoder.py:119-126`). |
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
3. **Two live Wiener λ constants** (`2.05e-5` vs `1e-4`) and a closed form (T13) that only matches the constant at p=0.5.
4. **Two live binding algebras** under one class: FFT HRR (T8/T9) vs permutation BHDC (T6/T7), with a docstring that claims the latter for the former.
5. **Rust vs Python fallback disagree** on seeds (T4/T4b), vector fill (T3/T3b), and unbind (T7/T7b).
6. **Rust vs Python adaptation disagree** on gains and bounds (T23 vs T23b).
7. **Neuromodulator baselines disagree** (Rust 0.5/0.05/0.05 vs settings 0.4/0.0/0.0).
8. **Entropy of weights is not softmax entropy** (linear-normalized natural log) — any prior "proof" using softmax/log2 is void.

---

*End of document SOMA-BR-MATH-TRUTH-001 v1.0.0. Every equation above maps to a cited line range in production source. No aspirational mathematics is included in §§1–5.*
