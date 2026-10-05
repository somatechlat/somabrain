# SOMA-BR-CONFIG-API-TEST-001 — Configuration, API, and Test-Map (Truth)

| Field | Value |
|---|---|
| Document ID | SOMA-BR-CONFIG-API-TEST-001 |
| Revision | A (initial) |
| Status | Released for Wave W1 contracts |
| Classification | Internal — ISO-style document control |
| Repository | `somabrain` @ `/Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain` |
| Scope | Config truth, API truth, test map |
| Method | Static code reading only. Every row cites `file:line`. No invented keys, no shims. |
| Predecessors | SOMA-BR-PLAN-MASTER-001 (W1/W4), docs/SomabrainGMD.md (λ*(p)) |
| Supersedes | (none) |

**Normative sources (code is source of truth):**

| Source | Path |
|---|---|
| Settings (env) | `somabrain/settings/{cognitive,neuro,django_core,base,constants,infra}.py` |
| Settings (DB) | `somabrain/brain_settings/{models,modes}.py` |
| Learning config | `somabrain/learning/config.py` |
| Rust constants | `rust_core/src/*.rs` (no standalone `const` math tables; values come from Python/brain_settings) |
| API | `somabrain/api/endpoints/{neuromod,cognitive,memory,memory_remember,calibration,sleep}.py`, `somabrain/api/v1.py`, `somabrain/api/schemas/*.py`, `somabrain/api/memory/models.py`, `somabrain/schemas/*.py` |
| Tests | `tests/property/*.py`, `tests/unit/test_learning_math.py`, `tests/integration/test_learning_proof.py`, `tests/smoke/math_smoke_test.py`, `tests/proofs/**` |

**Reading notes**

1. `somabrain/settings/base.py:9-12` star-imports in order `cognitive → django_core → infra → neuro`. Same-named attributes are **overwritten by the later module**. Effective defaults for dual-declared keys therefore follow `django_core`, not `cognitive` (see DEF-01).
2. `brain_settings` is a DB-backed overlay (`BrainSetting.get`, `somabrain/brain_settings/models.py:72-97`) with priority: mode-tuned key (`knob:MODE`) → mode-registry override (`somabrain/brain_settings/modes.py:11-55`) → base DB/default. Env settings and brain_settings are **two parallel config planes**; many math knobs exist in both with different names or defaults.
3. "Used-by" cites the first production reader found. Absence of a used-by row means the key is declared but no production reader was found in `somabrain/` (defect candidate DEAD-KEY).

---

# Part 1 — CONFIG TRUTH TABLE

## 1.1 Working Memory / Recency / Salience (math-affecting)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SOMABRAIN_WM_ALPHA` | **0.6** | float | settings/cognitive.py:132 | memory/wm/core.py:149 | **OVERRIDE** django_core.py:46,68 re-declares same name default **0.5**; base.py import order makes 0.5 effective. DEF-01 |
| `SOMABRAIN_WM_BETA` | **0.3** | float | settings/cognitive.py:133 | memory/wm/core.py (wm weights) | django_core.py:47,69 default **0.2** wins. DEF-01 |
| `SOMABRAIN_WM_GAMMA` | **0.1** | float | settings/cognitive.py:134 | memory/wm/core.py | django_core.py:48,70 default **0.3** wins. DEF-01 |
| `SOMABRAIN_WM_RECENCY_TIME_SCALE` | **1.0** | float | settings/cognitive.py:128-129 | memory/wm/core.py:158,168; memory/wm/mt_wm.py:57; admin/cognitive/microcircuits.py:70 | django_core.py:49 default **60.0** wins. bootstrap/core_singletons.py:48,82 uses `getattr(..., 3600)` call-site default. **Three defaults: 1.0 / 60.0 / 3600**. DEF-02 |
| `SOMABRAIN_WM_RECENCY_MAX_STEPS` | **1000** (int) | int | settings/cognitive.py:131 | memory/wm | django_core.py:50 declares **float 10.0**. Type + value conflict. DEF-01 |
| `SOMABRAIN_WM_SALIENCE_THRESHOLD` | **0.4** | float | settings/cognitive.py:135-137 | salience gate | django_core.py:51 default **0.6** wins. DEF-01 |
| `SOMABRAIN_WM_SIZE` | 64 | int | settings/cognitive.py:127 | memory/wm | brain_settings `wm_size` v=64 models.py:713 |
| `SOMABRAIN_WM_PER_COL_MIN_CAPACITY` | 16 | int | settings/cognitive.py:138-140 | mt_wm | |
| `SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR` | 1e-4 | float | settings/cognitive.py:141-143 | wm vote | |
| `SOMABRAIN_WM_VOTE_ENTROPY_EPS` | 1e-9 | float | settings/cognitive.py:144 | wm vote | brain_settings `wm_vote_entropy_eps` v=1e-09 models.py:714 |
| `SOMABRAIN_WM_PER_TENANT_CAPACITY` | 128 | int | settings/cognitive.py:145-147 | mt_wm | |
| `SOMABRAIN_MTWM_MAX_TENANTS` | 1000 | int | settings/cognitive.py:148 | mt_wm | brain_settings `mtwm_max_tenants` models.py:453 |
| `SOMABRAIN_MICRO_VOTE_TEMPERATURE` | 0.25 | float | settings/cognitive.py:152-154 | microcircuits | |
| `SOMABRAIN_SALIENCE_W_NOVELTY` | 0.6 | float | settings/cognitive.py:213 | bootstrap/core_singletons.py:133 | brain_settings `salience_w_novelty` v=0.6 models.py:270-276 (learnable 0..1) |
| `SOMABRAIN_SALIENCE_W_ERROR` | 0.4 | float | settings/cognitive.py:214 | amygdala/salience | brain_settings models.py:629 |
| `SOMABRAIN_SALIENCE_THRESHOLD_STORE` | 0.5 | float | settings/cognitive.py:215-217 | bootstrap/core_singletons.py:136 (`getattr` fallback **0.6**) | Call-site default ≠ declared default. DEF-03 |
| `SOMABRAIN_SALIENCE_THRESHOLD_ACT` | 0.7 | float | settings/cognitive.py:218-220 | salience gate | |
| `SOMABRAIN_SALIENCE_HYSTERESIS` | 0.1 | float | settings/cognitive.py:221 | salience | brain_settings models.py:628 |
| `SOMABRAIN_SALIENCE_FD_WEIGHT` | 0.25 | float | settings/cognitive.py:222 | salience | brain_settings models.py:621-627 |
| `SOMABRAIN_SALIENCE_FD_DECAY` | 0.9 | float | settings/cognitive.py:212 | salience | brain_settings models.py:613-619 |
| `SOMABRAIN_SALIENCE_FD_RANK` | 128 | int | settings/cognitive.py:211 | salience | brain_settings models.py:620 |
| `SOMABRAIN_SALIENCE_SOFT_TEMPERATURE` | 0.1 | float | settings/cognitive.py:226-228 | soft salience | |
| `SOMABRAIN_SALIENCE_METHOD` | "dense" | str | settings/cognitive.py:210 | salience | |
| `SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR` | 0.9 | float | settings/cognitive.py:223-225 | salience | |
| `SOMABRAIN_USE_SOFT_SALIENCE` | False | bool | settings/cognitive.py:229 | salience | brain_settings `use_soft_salience` models.py:697 |

## 1.2 Retrieval / Scorer / Recency (math-affecting)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SOMABRAIN_RETRIEVAL_ALPHA` | 1.0 | float | settings/cognitive.py:178 | context/builder.py:83 | brain_settings `retrieval_alpha` v=1.0 models.py:583-589 |
| `SOMABRAIN_RETRIEVAL_BETA` | **0.2** | float | settings/cognitive.py:179 | context/builder.py:84 | Twin `RETRIEVAL_BETA` default **0.3** cognitive.py:509. DEF-04 |
| `SOMABRAIN_RETRIEVAL_GAMMA` | 0.1 | float | settings/cognitive.py:180 | context/builder.py:85 | Twin `RETRIEVAL_GAMMA` default 0.1 cognitive.py:510 (same) |
| `SOMABRAIN_RETRIEVAL_TAU` | **0.7** | float | settings/cognitive.py:181 | context/builder.py:86 | Twin `RETRIEVAL_TAU` default **0.8** cognitive.py:511. brain_settings `retrieval_tau` v=0.7 models.py:604-610. DEF-04 |
| `RETRIEVAL_ALPHA` | 1.0 | float | settings/cognitive.py:508 | (no direct reader found) | Twin of SOMABRAIN_RETRIEVAL_ALPHA |
| `RETRIEVAL_BETA` | 0.3 | float | settings/cognitive.py:509 | (no direct reader found) | DEF-04 |
| `RETRIEVAL_GAMMA` | 0.1 | float | settings/cognitive.py:510 | (no direct reader found) | |
| `RETRIEVAL_TAU` | 0.8 | float | settings/cognitive.py:511 | (no direct reader found) | DEF-04 |
| `SOMABRAIN_RECENCY_HALF_LIFE` | 60.0 | float | settings/cognitive.py:182 | memory/scoring.py:96 (`getattr` default 60.0) | brain_settings `recency_half_life` v=60.0 models.py:277-283 |
| `SOMABRAIN_RECENCY_SHARPNESS` | 1.2 | float | settings/cognitive.py:183 | memory/scoring.py | brain_settings models.py:562 |
| `SOMABRAIN_RECENCY_FLOOR` | 0.05 | float | settings/cognitive.py:184 | memory/scoring.py | brain_settings models.py:555-561 |
| `SOMABRAIN_DENSITY_TARGET` | 0.2 | float | settings/cognitive.py:185 | recall density | brain_settings models.py:416 |
| `SOMABRAIN_DENSITY_FLOOR` | 0.6 | float | settings/cognitive.py:186 | recall density | brain_settings models.py:409-415 |
| `SOMABRAIN_DENSITY_WEIGHT` | 0.35 | float | settings/cognitive.py:187 | recall density | brain_settings models.py:417-423 |
| `SOMABRAIN_DUP_RATIO_THRESHOLD` | 0.5 | float | settings/cognitive.py:192 | recall dedupe | brain_settings models.py:424-430 |
| `SOMABRAIN_SCORER_W_COSINE` | 0.6 | float | settings/cognitive.py:170 | scoring | brain_settings models.py:639 |
| `SOMABRAIN_SCORER_W_FD` | 0.25 | float | settings/cognitive.py:171 | scoring | brain_settings models.py:640 |
| `SOMABRAIN_SCORER_W_RECENCY` | 0.15 | float | settings/cognitive.py:172 | scoring | brain_settings models.py:641 |
| `SOMABRAIN_SCORER_WEIGHT_MIN` | 0.0 | float | settings/cognitive.py:173 | scoring | brain_settings models.py:643 |
| `SOMABRAIN_SCORER_WEIGHT_MAX` | 1.0 | float | settings/cognitive.py:174 | scoring | brain_settings models.py:642 |
| `SOMABRAIN_SCORER_RECENCY_TAU` | 32.0 | float | settings/cognitive.py:175 | bootstrap/singletons.py:238 | brain_settings `scorer_recency_tau` v=32.0 models.py:632-638 |

## 1.3 Tau / anneal / entropy (math-affecting)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SOMABRAIN_TAU_MIN` | **0.4** | float | settings/cognitive.py:188 | learning/annealing.py:82 | Twin `TAU_MIN_FLOOR` default **0.1** cognitive.py:514. brain_settings `tau_min` v=0.4 models.py:678. **Floor conflict 0.4 vs 0.1**. DEF-05 |
| `SOMABRAIN_TAU_MAX` | 1.2 | float | settings/cognitive.py:189 | learning | brain_settings `tau_max` models.py:677 |
| `SOMABRAIN_TAU_INC_UP` | 0.1 | float | settings/cognitive.py:190 | tau controller | brain_settings `tau_inc_up` models.py:676 |
| `SOMABRAIN_TAU_INC_DOWN` | 0.05 | float | settings/cognitive.py:191 | tau controller | brain_settings `tau_inc_down` models.py:669-675 |
| `TAU_MIN_FLOOR` | **0.1** | float | settings/cognitive.py:514 | tasks/temperature_anneal.py:42 | DEF-05 |
| `TAU_DECAY_FACTOR` | 0.95 | float | settings/cognitive.py:513 | tasks/temperature_anneal.py | Concept twin of `SOMABRAIN_TAU_DECAY_RATE` (0.0). DEF-06 |
| `TAU_ANNEAL_INTERVAL` | 60.0 | float | settings/cognitive.py:512 | tasks/temperature_anneal.py | Twin of `SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL` (int, default 0) |
| `SOMABRAIN_TAU_DECAY_ENABLED` | False | bool | settings/cognitive.py:334 | learning | brain_settings `tau_decay_enabled` models.py:661 |
| `SOMABRAIN_TAU_DECAY_RATE` | 0.0 | float | settings/cognitive.py:335 | learning | brain_settings `tau_decay_rate` models.py:662-668 |
| `SOMABRAIN_TAU_ANNEAL_MODE` | None | str | settings/cognitive.py:336 | learning/annealing.py via runtime get_str | brain_settings `tau_anneal_mode` v="" models.py:653 |
| `SOMABRAIN_TAU_ANNEAL_RATE` | 0.0 | float | settings/cognitive.py:337 | learning/annealing.py | brain_settings `tau_anneal_rate` models.py:654-660 |
| `SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL` | 0 | int | settings/cognitive.py:338-340 | learning/annealing.py:97 (fallback 10) | Call-site default 10 ≠ declared 0. DEF-03 |
| `SOMABRAIN_ENTROPY_CAP_ENABLED` | False | bool | settings/cognitive.py:341 | learning | brain_settings models.py:435 |
| `SOMABRAIN_ENTROPY_CAP` | 0.0 | float | settings/cognitive.py:342 | core/utils/entropy_guard.py:30 | brain_settings models.py:434 |
| `SOMABRAIN_INTEGRATOR_ENTROPY_CAP` | 0.0 | float | settings/cognitive.py:456 | integrator | Twin of SOMABRAIN_ENTROPY_CAP. DEF-04 |
| `entropy_sharpen_rate` (DB) | 0.8 | float | brain_settings/models.py:399 | learning/annealing.py | DB-only key |
| `entropy_final_sharpen` (DB) | 0.05 | float | brain_settings/models.py:400 | learning/annealing.py | DB-only key |

## 1.4 Learning / adaptation / utility

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SOMABRAIN_UTILITY_LAMBDA` | 1.0 | float | settings/cognitive.py:347 | learning/config.py:29-30 | brain_settings `utility_lambda` models.py:699 |
| `SOMABRAIN_UTILITY_MU` | 0.1 | float | settings/cognitive.py:348 | learning/config.py:32-33 | brain_settings models.py:702 |
| `SOMABRAIN_UTILITY_NU` | 0.05 | float | settings/cognitive.py:349 | learning/config.py:35-36 | brain_settings models.py:705 |
| `UTILITY_LAMBDA_MIN/MAX` | 0.0 / 5.0 | float | settings/cognitive.py:519,518 | learning/config.py:42-43 | |
| `UTILITY_MU_MIN/MAX` | 0.0 / 5.0 | float | settings/cognitive.py:521,520 | learning/config.py:46-47 | |
| `UTILITY_NU_MIN/MAX` | 0.0 / 5.0 | float | settings/cognitive.py:523,522 | learning/config.py:50-51 | |
| `SOMABRAIN_ADAPTATION_GAIN_ALPHA` | 1.0 | float | settings/cognitive.py:350-352 | learning/config.py:76-78 | |
| `SOMABRAIN_ADAPTATION_GAIN_GAMMA` | -0.5 | float | settings/cognitive.py:353-355 | learning/config.py:79-81 | |
| `SOMABRAIN_ADAPTATION_GAIN_LAMBDA` | 1.0 | float | settings/cognitive.py:356-358 | learning/config.py:82-84 | |
| `SOMABRAIN_ADAPTATION_GAIN_MU` | -0.25 | float | settings/cognitive.py:359 | learning/config.py:85-87 | brain_settings `adaptation_gain_mu` models.py:384 |
| `SOMABRAIN_ADAPTATION_GAIN_NU` | -0.25 | float | settings/cognitive.py:360 | learning/config.py:88-90 | brain_settings models.py:385 |
| `SOMABRAIN_ADAPTATION_{ALPHA,GAMMA,LAMBDA,MU,NU}_{MIN,MAX}` | see cognitive.py:362-383 | float | settings/cognitive.py:362-383 | learning/config.py:139-168 | Bounds for AdaptationConstraints |
| `SOMABRAIN_LEARNING_RATE_DYNAMIC` | False | bool | settings/cognitive.py:343-345 | learning/adaptation/engine.py:165 | Twin `LEARNING_RATE_DYNAMIC` cognitive.py:497. DEF-04 |
| `LEARNING_RATE_DYNAMIC` | False | bool | settings/cognitive.py:497 | (no direct reader) | |
| `adapt_lr` (DB) | 0.05 | float | brain_settings/models.py:232-238 | learning/adaptation/engine.py:89; learning/rust_engine.py:43 | learnable [0, 0.25] |
| `gmd_eta` (DB) | 0.08 | float | brain_settings/models.py:225-231 | GMD plasticity | learnable [0.03, 0.10]; mode overrides modes.py:15,24,33,41,52 |
| `gmd_lambda_reg` (DB) | `compute_wiener_lambda(p, 8)` (formula, ≈5.696e-5 at p=0.1) | float | brain_settings/models.py (`_default_wiener_lambda`) | admin/core/quantum.py (same source) | Wiener λ*. DEF-07 **FIXED (W4)** |
| `gmd_delta` (DB) | 0.01 | float | brain_settings/models.py:216 | GMD MathCore | SYSTEM_CORE |
| `gmd_epsilon` (DB) | 0.05 | float | brain_settings/models.py:217 | GMD MathCore | SYSTEM_CORE |
| `gmd_alpha` (DB) | 640.0 | float | brain_settings/models.py:218 | GMD cleanup capacity | SYSTEM_CORE |
| `gmd_quantization_bits` (DB) | 8 | int | brain_settings/models.py:220 | GMD quantizer | SYSTEM_CORE |

## 1.5 Predictor / Chebyshev / heat (math-affecting)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `CHEBYSHEV_K` | **30** | int | settings/cognitive.py:482 | predictors/agent_predictor.py:57; action_predictor.py:52; state_predictor.py:57 | DEF-08 |
| `TRUTH_CHEBYSHEV_K` | **32** | int | settings/cognitive.py:517 | math/lanczos_chebyshev.py:75 | DEF-08 |
| `SOMABRAIN_CHEB_K` | **30** | int | settings/cognitive.py:438 | predictors/base.py:265 | Third name for same concept. DEF-08 |
| `LANCZOS_M` | 20 | int | settings/cognitive.py:496 | predictors | Twin `SOMABRAIN_LANCZOS_M` cognitive.py:458 |
| `SOMABRAIN_LANCZOS_M` | 20 | int | settings/cognitive.py:458 | predictors/base.py | |
| `SOMABRAIN_DIFFUSION_T` | 0.5 | float | settings/cognitive.py:445 | predictors/base.py:247 | Twin `DIFFUSION_T` cognitive.py:484 |
| `DIFFUSION_T` | 0.5 | float | settings/cognitive.py:484 | (no direct reader) | |
| `SOMABRAIN_CONF_ALPHA` | 2.0 | float | settings/cognitive.py:439 | predictors/base.py:247 | |
| `SOMABRAIN_PREDICTOR_PROVIDER` | "mahal" | str | settings/cognitive.py:386 | predictors | |
| `SOMABRAIN_PREDICTOR_DIM` | 16 | int | settings/cognitive.py:388 | predictors | brain_settings `predictor_dim` models.py:534 |
| `SOMABRAIN_PREDICTOR_ALPHA` | 2.0 | float | settings/cognitive.py:389 | services/integrator_hub_triplet.py:107,229 | Twin `PREDICTOR_ALPHA` cognitive.py:505. brain_settings `predictor_alpha` models.py:527-533 |
| `SOMABRAIN_PREDICTOR_GAMMA` | -0.5 | float | settings/cognitive.py:390 | predictors | brain_settings `predictor_gamma` models.py:535-541 (bounds 0..1 — **default -0.5 is outside brain_settings bounds**) DEF-09 |
| `PREDICTOR_ALPHA` | 2.0 | float | settings/cognitive.py:505 | (no direct reader) | |
| `HEAT_METHOD` | "chebyshev" | str | settings/cognitive.py:487 | math/lanczos_chebyshev | |
| `TRUTH_APPR_EPS` | "1e-4" | str | settings/cognitive.py:516 | math approx (string-typed) | Type is str not float |

## 1.6 HRR / SDR / BHDC / embed dim

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `EMBED_DIM` → `SOMABRAIN_EMBED_DIM` | 768 | int | settings/cognitive.py:124 | embed_dim.resolve_embed_dim | Seam unity: MEM_EMBED_DIM == SOMABRAIN_EMBED_DIM == SOMA_VECTOR_DIM (comment cognitive.py:121-123). brain_settings `embed_dim` v=768 models.py:222 |
| `EMBED_DIM_SEAM` → `SOMABRAIN_EMBED_DIM_SEAM` | 768 | int | settings/cognitive.py:126 | embed_dim fail-closed | Certified seam contract |
| `SOMABRAIN_HRR_DIM` | 8192 | int | settings/cognitive.py:260 | HRRContext | brain_settings `hrr_dim` v=8192 models.py:221 |
| `HRR_DIM` | **512** | int | settings/cognitive.py:425 | cognitive.py:84 (`getattr(cfg,"HRR_DIM",512)`) | **Different name+default from SOMABRAIN_HRR_DIM (8192)**. DEF-10 |
| `SOMABRAIN_HRR_DTYPE` | "float32" | str | settings/cognitive.py:261 | HRR | |
| `SOMABRAIN_HRR_RENORM` | True | bool | settings/cognitive.py:262 | HRR | brain_settings `hrr_renorm` models.py:443 |
| `SOMABRAIN_HRR_VECTOR_FAMILY` | "bhdc" | str | settings/cognitive.py:263 | math/bhdc_encoder | |
| `SOMABRAIN_BHDC_SPARSITY` | 0.1 | float | settings/cognitive.py:264 | bhdc | django_core.py:45,65 re-declares same default 0.1 (consistent). brain_settings `bhdc_sparsity` models.py:391; `gmd_sparsity` models.py:260-266 |
| `SOMABRAIN_MATH_BHDC_SPARSITY` | 0.1 | float | settings/cognitive.py:462 | math | Third BHDC sparsity name. DEF-04 |
| `SOMABRAIN_MATH_BHDC_MIX` | 0.5 | float | settings/cognitive.py:461 | math/bhdc_encoder | |
| `SOMABRAIN_MATH_BHDC_BINARY_MODE` | False | bool | settings/cognitive.py:460 | math | |
| `SOMABRAIN_MATH_BINDING_SEED` | 42 | int | settings/cognitive.py:463 | math binding | Twin of GLOBAL_SEED / HRR_SEED |
| `SOMABRAIN_HRR_SEED` | 42 | int | settings/cognitive.py:455 | HRR | brain_settings `global_seed` v=42 models.py:223 |
| `SOMABRAIN_GLOBAL_SEED` | 42 | int | settings/cognitive.py:280 | determinism | |
| `SOMABRAIN_DETERMINISM` | True | bool | settings/cognitive.py:281 | determinism | brain_settings `determinism` models.py:284 |
| `SOMABRAIN_HRR_ANCHORS_MAX` | 256 | int | settings/cognitive.py:453 | HRR | |
| `SOMABRAIN_HRR_DECAY_LAMBDA` | 0.05 | float | settings/cognitive.py:454 | HRR decay | |
| `SOMABRAIN_SDR_BITS` | 2048 | int | settings/cognitive.py:267 | SDR | brain_settings models.py:645 |
| `SOMABRAIN_SDR_DENSITY` | 0.03 | float | settings/cognitive.py:268 | SDR | brain_settings models.py:646 |
| `SOMABRAIN_SDR_DIM` | 16384 | int | settings/cognitive.py:269 | SDR | brain_settings models.py:647 |
| `SOMABRAIN_SDR_SPARSITY` | 0.01 | float | settings/cognitive.py:270 | SDR | brain_settings models.py:648 |
| `SOMABRAIN_QUANTUM_DIM` | 2048 | int | settings/cognitive.py:289 | quantum | brain_settings models.py:543 |
| `SOMABRAIN_QUANTUM_SPARSITY` | 0.1 | float | settings/cognitive.py:290 | quantum | brain_settings models.py:544 |
| `ALLOW_TINY_EMBEDDER` | False | bool | settings/cognitive.py:481 | embedder guard | |

## 1.7 Neuromodulator (math-affecting via DA→LR)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SOMABRAIN_NEURO_DOPAMINE_BASE` | 0.4 | float | settings/neuro.py:10 | runtime/neuromodulators.py:83-86 | |
| `SOMABRAIN_NEURO_SEROTONIN_BASE` | 0.5 | float | settings/neuro.py:11-13 | runtime/neuromodulators.py:88-91 | |
| `SOMABRAIN_NEURO_NORAD_BASE` | 0.0 | float | settings/neuro.py:14 | runtime/neuromodulators.py:93-96 | |
| `SOMABRAIN_NEURO_ACETYL_BASE` | 0.0 | float | settings/neuro.py:15 | runtime/neuromodulators.py:98-100 | Mode TRAINING overrides to 0.5 (modes.py:17) |
| `SOMABRAIN_NEURO_DOPAMINE_MIN/MAX` | 0.2 / 0.8 | float | settings/neuro.py:18-19 | neuromod bounds | Documented range NeuromodState docstring runtime/neuromodulators.py:72 |
| `SOMABRAIN_NEURO_SEROTONIN_MIN/MAX` | 0.0 / 1.0 | float | settings/neuro.py:22-23 | neuromod bounds | |
| `SOMABRAIN_NEURO_NORAD_MIN/MAX` | 0.0 / 0.1 | float | settings/neuro.py:26-27 | neuromod bounds | |
| `SOMABRAIN_NEURO_ACETYL_MIN/MAX` | 0.0 / 0.1 | float | settings/neuro.py:30-31 | neuromod bounds | |
| `SOMABRAIN_NEURO_DOPAMINE_LR` | 0.01 | float | settings/neuro.py:20 | runtime/neuromodulators.py:259; admin/brain/neuromodulators.py:257 | brain_settings `neuro_acetyl_lr` etc. models.py:239-259 |
| `SOMABRAIN_NEURO_SEROTONIN_LR` | 0.01 | float | settings/neuro.py:24 | runtime/neuromodulators.py:266 | |
| `SOMABRAIN_NEURO_NORAD_LR` | 0.01 | float | settings/neuro.py:28 | runtime/neuromodulators.py:273 | |
| `SOMABRAIN_NEURO_ACETYL_LR` | 0.01 | float | settings/neuro.py:32 | runtime/neuromodulators.py:280 | |
| `SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST` | 0.1 | float | settings/neuro.py:35-37 | neuromod feedback | |
| `SOMABRAIN_NEURO_DOPAMINE_BIAS` | 0.05 | float | settings/neuro.py:38 | neuromod | |
| `SOMABRAIN_NEURO_URGENCY_FACTOR` | 0.02 | float | settings/neuro.py:39-41 | neuromod | |
| `SOMABRAIN_NEURO_LATENCY_FLOOR` | 0.1 | float | settings/neuro.py:42 | neuromod | |
| `SOMABRAIN_NEURO_LATENCY_SCALE` | 0.01 | float | settings/neuro.py:43 | neuromod | |
| `SOMABRAIN_NEURO_MEMORY_FACTOR` | 0.02 | float | settings/neuro.py:44 | neuromod | |
| `SOMABRAIN_NEURO_ACCURACY_SCALE` | 0.05 | float | settings/neuro.py:45-47 | neuromod | |
| `neuro_k_d_*`, `neuro_k_r_*`, `neuro_u_scale` (DB) | see models.py:456-520 | float | brain_settings/models.py:456-520 | rust_core/src/neuro.rs:71,112 | Dynamics `dm/dt = k_d·x − k_r·m + bias + u_scale·u` |

## 1.8 Sleep schedule (math-affecting)

| Env key | Default | Type | Declared | Used-by | Notes |
|---|---|---|---|---|---|
| `SLEEP_K0` | **10** | int | settings/cognitive.py:314 | sleep scheduler | brain_settings `sleep_k0` v=**100** models.py:287. DEF-11 |
| `SLEEP_T0` | 1.0 | float | settings/cognitive.py:315 | sleep | brain_settings models.py:288-294 |
| `SLEEP_TAU0` | 0.1 | float | settings/cognitive.py:316 | sleep | brain_settings models.py:295-301 |
| `SLEEP_ETA0` | 0.01 | float | settings/cognitive.py:317 | sleep | brain_settings models.py:302-308 |
| `SLEEP_LAMBDA0` | 0.5 | float | settings/cognitive.py:318 | sleep | brain_settings models.py:309-315 |
| `SLEEP_B0` | 1.0 | float | settings/cognitive.py:319 | sleep | brain_settings models.py:316-322 |
| `SLEEP_K_MIN` | **5** | int | settings/cognitive.py:320 | sleep | brain_settings has **two** entries: `sleep_k_min` v=5 (RESOURCE, models.py:323-329) and `sleep_k_min` v=1 (sleep, models.py:565) — **duplicate DB key, later dict entry wins**. DEF-12 |
| `SLEEP_T_MIN` | **0.5** | float | settings/cognitive.py:321 | sleep | brain_settings duplicates: v=0.5 models.py:330-336 and v=0.1 models.py:566. DEF-12 |
| `SLEEP_ALPHA_K` | 0.1 | float | settings/cognitive.py:322 | sleep | brain_settings duplicates 0.1 (models.py:337-343) and **0.8** (models.py:567). DEF-12 |
| `SLEEP_ALPHA_T` | 0.05 | float | settings/cognitive.py:323 | sleep | brain_settings duplicates 0.05 (models.py:344-350) and **0.5** (models.py:568). DEF-12 |
| `SLEEP_ALPHA_TAU` | 0.05 | float | settings/cognitive.py:324 | sleep | brain_settings duplicates 0.05 (models.py:351-357) and **0.5** (models.py:569). DEF-12 |
| `SLEEP_ALPHA_ETA` | 0.01 | float | settings/cognitive.py:325 | sleep | brain_settings duplicates 0.01 (models.py:358-364) and **1.0** (models.py:570). DEF-12 |
| `SLEEP_BETA_B` | 0.1 | float | settings/cognitive.py:326 | sleep | brain_settings duplicates 0.1 (models.py:365-371) and **0.5** (models.py:571). DEF-12 |
| `SOMABRAIN_ENABLE_SLEEP` | True | bool | settings/cognitive.py:299 | sleep | brain_settings `enable_sleep` models.py:286 |
| `SOMABRAIN_CONSOLIDATION_ENABLED` | True | bool | settings/cognitive.py:300-302 | consolidation | brain_settings models.py:579 |
| `SOMABRAIN_NREM_BATCH_SIZE` | 16 | int | settings/cognitive.py:309 | api/endpoints/sleep.py:214 | brain_settings models.py:580 |
| `SOMABRAIN_MAX_SUMMARIES_PER_CYCLE` | 3 | int | settings/cognitive.py:310-312 | api/endpoints/sleep.py:216,228 | brain_settings models.py:581 |
| `SOMABRAIN_REM_RECOMB_RATE` | 0.2 | float | settings/cognitive.py:313 | api/endpoints/sleep.py:226 | brain_settings models.py:572-578 |
| `SLEEP_MAX_SECONDS` | 3600 | int | settings/cognitive.py:435 | api/endpoints/sleep.py:123,158 | TTL clamp for sleep API |

## 1.9 Duplicate-key register (defect candidates)

Each row = same concept, different name and/or default. This is the W1 unification worklist.

| ID | Concept | Variant A | Variant B | Variant C | Evidence | Risk | Status |
|---|---|---|---|---|---|---|---|
| DEF-01 | WM weights + recency + salience threshold | cognitive.py:132-137 defaults α=0.6 β=0.3 γ=0.1 recency_scale=1.0 max_steps=1000 sal_thr=0.4 | django_core.py:46-51 same *names*, defaults α=0.5 β=0.2 γ=0.3 recency_scale=60.0 max_steps=**float 10.0** sal_thr=0.6 | brain_settings matches **cognitive** (models.py:709-713) | base.py:9-11 import order → django_core **overwrites** cognitive | Runtime WM math uses django_core values; DB brain_settings disagree. Silent math divergence. | **FIXED (W1b)** — django_core WM re-declarations deleted; cognitive.py is the single site |
| DEF-02 | WM recency time scale | cognitive.py:128 default **1.0** | django_core.py:49 default **60.0** | bootstrap/core_singletons.py:48,82 call-site `getattr(..., 3600)` | three defaults 1.0 / 60.0 / 3600 | Recency decay time constant off by 60×–3600× | **FIXED (W1b)** — single default `contracts.RECENCY_SCALE` (60.0) |
| DEF-03 | Call-site defaults ≠ declared defaults | SOMABRAIN_SALIENCE_THRESHOLD_STORE declared 0.5 (cognitive.py:215) | core_singletons.py:136 `getattr` fallback **0.6** | SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL declared 0 (cognitive.py:338) vs annealing.py:97 fallback **10** | R-VAL-01 violated at call site | Value depends on whether settings object is complete | **FIXED (W1b)** — call-site defaults reference `contracts.*` |
| DEF-04 | Retrieval weights / plan / entropy / learning-rate / BHDC / diffusion / predictor α | `SOMABRAIN_RETRIEVAL_BETA` 0.2 (cognitive.py:179) | `RETRIEVAL_BETA` 0.3 (cognitive.py:509) | `SOMABRAIN_RETRIEVAL_TAU` 0.7 vs `RETRIEVAL_TAU` 0.8 (cognitive.py:181 vs 511) | also PLAN_MAX_STEPS / SOMABRAIN_PLAN_MAX_STEPS; USE_PLANNER / SOMABRAIN_USE_PLANNER; USE_MICROCIRCUITS / SOMABRAIN_USE_MICROCIRCUITS; LEARNING_RATE_DYNAMIC; DIFFUSION_T; PREDICTOR_ALPHA; LANCZOS_M; MEMORY_FAST_ACK; MEMORY_HEALTH_POLL_INTERVAL | Two spellings, different defaults; one is dead | **FIXED (W1b)** — dead twins deleted; readers re-pointed to `SOMABRAIN_*` |
| DEF-05 | Tau floor | `SOMABRAIN_TAU_MIN` 0.4 (cognitive.py:188) | `TAU_MIN_FLOOR` 0.1 (cognitive.py:514) | brain_settings `tau_min` 0.4 (models.py:678) | annealing.py:82 reads SOMABRAIN_TAU_MIN; temperature_anneal.py:42 reads TAU_MIN_FLOOR | Two anneal paths, different floors | **FIXED (W1b)** — `contracts.TAU_FLOOR=0.1` is the single floor |
| DEF-06 | Tau decay rate | `SOMABRAIN_TAU_DECAY_RATE` 0.0 (cognitive.py:335) | `TAU_DECAY_FACTOR` 0.95 (cognitive.py:513) | — | multiplicative factor vs additive rate | Unify to one schedule | **FIXED (W1b)** — `contracts.TAU_DECAY_FACTOR=0.95`; twins deleted |
| DEF-07 | Wiener λ* | **FIXED (W4):** single source `compute_wiener_lambda(p, 8)` (Rust `mathcore.rs` + Python `math/bhdc_encoder.py`) | brain_settings `gmd_lambda_reg` computed from formula | quantum.py fallback uses `production_wiener_lambda()`; binder default = formula at production p | GMD doc λ*(p)=5.126e-6/(p(1−p)) | one formula, no constants | **FIXED (W4)** |
| DEF-08 | Chebyshev K | `CHEBYSHEV_K` **30** (cognitive.py:482) | `TRUTH_CHEBYSHEV_K` **32** (cognitive.py:517) | `SOMABRAIN_CHEB_K` **30** (cognitive.py:438) | predictors/* use CHEBYSHEV_K; math/lanczos_chebyshev.py:75 uses TRUTH_CHEBYSHEV_K | Heat-kernel approx order differs by path | **FIXED (W1b)** — one key `SOMABRAIN_CHEB_K`; twins deleted |
| DEF-09 | Predictor gamma bounds | env default **-0.5** (cognitive.py:390) | brain_settings `predictor_gamma` min **0.0** max 1.0 (models.py:535-541) | — | default outside learnable bounds | set() would reject the seeded default | **OPEN** (W3 gains parity) |
| DEF-10 | HRR dim | `SOMABRAIN_HRR_DIM` **8192** (cognitive.py:260) | `HRR_DIM` **512** (cognitive.py:425) | brain_settings `hrr_dim` 8192 (models.py:221) | cognitive.py:84 reads `HRR_DIM` | FocusState HRR dim 512 vs system 8192 | **FIXED (W1b)** — `HRR_DIM` unified to `BHDC_D` (8192) |
| DEF-11 | Sleep K0 | `SLEEP_K0` **10** (cognitive.py:314) | brain_settings `sleep_k0` **100** (models.py:287) | — | 10× divergence | Sleep schedule rate | **FIXED (W1b)** — `SLEEP_K0` default unified to 100 |
| DEF-12 | Sleep α/min duplicates in BRAIN_DEFAULTS | RESOURCE block models.py:323-371 (k_min=5, t_min=0.5, α_k=0.1, α_t=0.05, α_tau=0.05, α_eta=0.01, β_b=0.1) | sleep block models.py:565-571 (**k_min=1, t_min=0.1, α_k=0.8, α_t=0.5, α_tau=0.5, α_eta=1.0, β_b=0.5**) | dict later entry silently overwrites earlier | Python dict literal — second value wins at models.py:565-571 | Seed data wrong; two "authoritative" tables in one dict | **FIXED (W1b)** — duplicate sleep block deleted |
| DEF-13 | Adaptation gain/naming | `adapt_gain_mu/nu`, `adapt_*_min/max` (models.py:373-383) | `adaptation_gain_mu/nu`, `adaptation_*_min/max` (models.py:384-389) | env `SOMABRAIN_ADAPTATION_GAIN_*` (cognitive.py:350-360) | three naming schemes for one family | W1 must pick one | **FIXED (W1b)** — `adaptation_*` namespace kept; `adapt_*` deleted |
| DEF-14 | Settings attrs referenced but **not declared** | context/builder.py:92-101 reads `settings.retrieval_recency_half_life`, `retrieval_recency_sharpness`, `retrieval_recency_floor`, `retrieval_density_*`, `SOMABRAIN_RETRIEVAL_TAU_min/_max/_increment_up/_increment_down`, `retrieval_dup_ratio_threshold` | None of these names exist in settings/*.py (declared names are `SOMABRAIN_RECENCY_HALF_LIFE`, `SOMABRAIN_TAU_MIN`, `SOMABRAIN_TAU_INC_UP`, …) | — | AttributeError / silent wrong config at runtime | Missing keys must be created by **renaming readers to real settings**, not by adding shim attributes | **FIXED (W1b)** — builder.py reads real `SOMABRAIN_*` keys |

## 1.10 Rust-core constants

| Item | Location | Value source | Notes |
|---|---|---|---|
| Neuro dynamics k_d/k_r/u_scale | rust_core/src/neuro.rs:19,71,112-126 | Loaded from brain_settings (`neuro_k_d_*`, `neuro_k_r_*`, `neuro_u_scale`) | No Rust-side `const` math tables |
| linear_tau_decay / exponential_tau_decay | rust_core/src/adaptation.rs (called from learning/annealing.py:408-427) | Args passed from Python | Python fallback formulas at annealing.py:411,428 must match Rust |
| Adaptation constraints | rust_core/src/adaptation.rs:147 `set_constraints` | Python `AdaptationConstraints` | |
| bhdc / mathcore / prediction | rust_core/src/{bhdc,mathcore,prediction}.rs | Parameters from Python | No independent defaults found |

---

# Part 2 — API TRUTH

Legend for **Clamps**: `Y` = request/schema clamps present; `N` = absent (unvalidated); `PART` = partial.

## 2.1 Neuromod (`somabrain/api/endpoints/neuromod.py`, mounted at `/neuromod/` — v1.py:76-78)

| Endpoint | Method | Request schema | Response schema | Clamps | Store touched | Unvalidated inputs |
|---|---|---|---|---|---|---|
| `/neuromod/state` | GET | (none) | inline dict `{tenant_id, dopamine, serotonin, noradrenaline, acetylcholine}` neuromod.py:58-61 | N/A | In-memory `PerTenantNeuromodulators.get_state` neuromod.py:35 via bootstrap/singletons | — |
| `/neuromod/adjust` | POST | `NeuromodAdjustRequest` neuromod.py: `dopamine/serotonin/noradrenaline/acetylcholine: float\|None` | same dict shape | **Y — REJECT out-of-box** | `checked_value` → `store.set_state(NeuromodState(**current))` | **FIXED (W2 / DEBT-003).** `checked_value` (runtime/neuromodulators.py) rejects non-finite and out-of-box values with HTTP 422 against `math.contracts.NEURO_BOUNDS` (DA [0.2,0.8], 5-HT [0,1], NA [0,0.1], ACh [0,0.1]). Store projects with Π on `set_state`. |

## 2.2 Cognitive (`somabrain/api/endpoints/cognitive.py`, mounted at `/cognitive/` — v1.py:66-68)

| Endpoint | Method | Request schema | Response schema | Clamps | Store touched | Unvalidated inputs |
|---|---|---|---|---|---|---|
| `/cognitive/plan/suggest` | POST | `PlanSuggestRequest` schemas/api.py:137-143: `task_key: str` (required), `max_steps: int\|None`, `rel_types: list[str]\|None`, `universe: str\|None` | `PlanSuggestResponse` schemas/api.py:146-149 `{plan: list[str]}` | PART: `task_key` non-empty 400 cognitive.py:117-119; `rel_types` must be list cognitive.py:127-129; `max_steps` int-cast but **no upper bound** cognitive.py:121-125 | MemoryService → memory pool; PlanEngine + graph_client cognitive.py:138-154 | `max_steps` unbounded; `universe` free string |
| `/cognitive/act` | POST | `ActRequest` schemas/api.py:14-19: `task: str`, `top_k: int=3`, `universe: str\|None` | `ActResponse` schemas/api.py:35-41 | N: `task` required by schema only; `top_k` unused by handler; `novelty` via `getattr(body,"novelty",…)` cognitive.py:203-207 — **`novelty` not even on ActRequest** | eval_step → predictor, neuromods, personality, amygdala, WM, memory cognitive.py:209-220; optional PlanEngine; focus_state persist cognitive.py:236-243 | `novelty` (schema-missing), `universe` free; no bounds on task length (truncated only for logs cognitive.py:275-278) |
| `/cognitive/personality` | POST | `PersonalityState` schemas/api.py:81-84 `{traits: dict[str,float]}` | `PersonalityState` | **N — no trait range clamp** | `PersonalityStore.set` cognitive.py:307 | All trait floats unclamped |
| `/cognitive/micro/diag` | GET | headers `X-Request-ID`, `X-Deadline-MS`, `X-Idempotency-Key` cognitive.py:316-318 | inline dict | N | `mc_wm.stats(tenant)` cognitive.py:334 | `deadline_ms` passed through as raw string |

## 2.3 Memory (`somabrain/api/endpoints/memory.py`, `memory_remember.py`, mounted at `/memory/` — v1.py:90-101)

| Endpoint | Method | Request schema | Response schema | Clamps | Store touched | Unvalidated inputs |
|---|---|---|---|---|---|---|
| `/memory/remember` | POST | `MemoryWriteRequest` api/memory/models.py:106-208 | `MemoryWriteResponse` | PART (see below) | WM admit + LTM via MemoryService; outbox when fast-ack memory_remember.py:176-215 | `value` free dict; `meta` free dict; `key` min_length=1 only |
| `/memory/recall` | POST | `RecallRequest` memory.py:150-202 | list of MemoryHit-shaped dicts memory.py:136-147 | PART | WM + LTM via MemoryService memory.py:235 | `scoring_mode` free string; `layer` free string (no enum) |
| `/memory/forget` | POST | `ForgetRequest` api/memory/models.py | `ForgetResponse` | PART | LTM + WM eviction | |

**MemoryWriteRequest clamp inventory** (api/memory/models.py):

| Field | Constraint | Line |
|---|---|---|
| `namespace` | `min_length=1`, `require_namespace` if blank | models.py:167-169, 237-243 |
| `key` | `min_length=1` | models.py:170-174 |
| `salience` | `ge=0.0, le=1.0` | models.py:150-152 |
| `importance`, `novelty` | `ge=0.0` (no upper bound) | models.py:200-205 |
| `ttl_seconds` | `ge=0` | models.py:182-184 |
| `MemoryLink.weight` | `ge=0.0` | models.py:70 |
| `signals.importance/novelty` | `ge=0.0` | models.py:77-82 |
| `tenant` | required after normalize (body or `X-Tenant-ID`); 400 if missing memory_remember.py:121-127 | |
| `value` | **free `dict[str,Any]` — no schema** | models.py:175 |
| `coord` | `str\|list[float]\|None`, 3-float list expected by helpers | models.py:141-145 |
| `embedding` | `list[float]\|None`, `ensure_embedding_dim` memory_remember.py:159 | |
| `kind`/`source` | free strings; seam defaults applied only if absent | models.py:125-159 |

**RecallRequest clamps** (memory.py:150-202): `min_score ge=0.0` :169-171; `max_age_seconds ge=0` :172-174; `chunk_size ge=1 le=50` :187-189; `chunk_index ge=0` :190; `top_k` `max(1, int(...))` handler clamp memory.py:237. **Unclamped:** `scoring_mode`, `layer`, `tags`, `session_id`, `conversation_id`.

## 2.4 Calibration (`somabrain/api/endpoints/calibration.py`, mounted at `/calibration/` — v1.py:135-138)

| Endpoint | Method | Request | Response | Clamps | Store touched | Unvalidated |
|---|---|---|---|---|---|---|
| `/calibration/status` | GET | — | `get_all_calibration_status()` or `{enabled:False}` calibration.py:20-22 | N/A | calibration_service (in-proc) | — |
| `/calibration/{domain}/{tenant}` | GET | path `domain`, `tenant` | `get_calibration_status(domain,tenant)` | **N — free path strings** calibration.py:25-40 | calibration_service | `domain`, `tenant` unvalidated; errors → 500 |
| `/calibration/reliability/{domain}/{tenant}` | GET | path `domain`, `tenant` | `export_reliability_data(domain,tenant)` | **N** calibration.py:43-58 | calibration_service | same |

No auth decorator on calibration router (contrast `api_key_auth` on neuromod/cognitive/memory/sleep).

## 2.5 Sleep (`somabrain/api/endpoints/sleep.py`, mounted at `/sleep/` — v1.py:70-73)

| Endpoint | Method | Request | Response | Clamps | Store touched | Unvalidated |
|---|---|---|---|---|---|---|
| `/sleep/state` | GET | — | `{tenant_id, state, timestamp}` sleep.py:80-84 | N/A | `TenantSleepState` ORM sleep.py:73 | — |
| `/sleep/brain/mode` | POST | raw `dict` Body sleep.py:238-247: `target_state` (default "active"), `ttl_seconds`, `trace_id` | `{ok, tenant, new_state, consolidation}` sleep.py:184-189 | PART: state enum validated sleep.py:129-132; `ttl_seconds > SLEEP_MAX_SECONDS` → 400 sleep.py:158-160; rate limit 100/min sleep.py:50-63; OPA sleep.py:111-126 | `TenantSleepState` ORM + NREM/REM consolidation sleep.py:178, 208-231 | body is **untyped dict**; `ttl_seconds` no lower bound (negative TTL accepted); `trace_id` free |
| `/sleep/util/mode` | POST | same dict sleep.py:250-259 | same | same | same | same |
| `/sleep/policy/mode` | POST | same dict sleep.py:262-271 | same | same | same | same |
| `/sleep/state` | POST | dict `state` sleep.py:275-281 | same | same (maps to mode="util") | same | `state` key vs `target_state` inconsistency |
| `/sleep/transition` | POST | dict `trigger` sleep.py:284-312 | `{tenant_id, state, timestamp}` | **N — trigger free string**, no OPA, no rate limit, no TTL | `TenantSleepState` + `SleepStateManager.transition` sleep.py:296-306 | `trigger` unvalidated; bypasses OPA path used by `/mode` |

`api/schemas/sleep.py` defines `SleepRequest` with `target_state: SleepTargetState` enum + `ttl_seconds ge=1` + `async_mode` (sleep.py schemas:31-56) — **this schema is NOT used by the endpoints**, which take raw `dict = Body(...)`. Contract drift: schemas/sleep.py:31-56 vs endpoints/sleep.py:239-247.

## 2.6 Router map (`somabrain/api/v1.py`)

| Prefix | Router import | Line |
|---|---|---|
| `/health/` | endpoints.health + endpoints.system_health | v1.py:46-53 |
| `/admin/` | endpoints.admin | v1.py:56-58 |
| `/admin/journal/` | endpoints.admin_journal | v1.py:61-63 |
| `/cognitive/` | endpoints.cognitive | v1.py:66-68 |
| `/sleep/` | endpoints.sleep | v1.py:70-73 |
| `/neuromod/` | endpoints.neuromod | v1.py:76-78 |
| `/proxy/` | endpoints.proxy | v1.py:81-83 |
| `/config/` | endpoints.config | v1.py:86-88 |
| `/memory/` | endpoints.memory + endpoints.memory_remember | v1.py:91-101 |
| `/memory/admin/` | endpoints.memory_admin | v1.py:95-97 |
| `` (root aliases) | endpoints.memory_alias (`/remember|recall|forget`) | v1.py:106-108 |
| `/context/` | endpoints.context | v1.py:111-113 |
| `/features/` | endpoints.features | v1.py:116-118 |
| `/threads/` | endpoints.thread | v1.py:121-123 |
| `/oak/` | endpoints.oak | v1.py:126-128 |
| `/opa/` | endpoints.opa | v1.py:131-133 |
| `/calibration/` | endpoints.calibration | v1.py:136-138 |
| `/persona/` | endpoints.persona | v1.py:141-143 |
| `/constitution/` | endpoints.constitution | v1.py:146-148 |
| `/brain/` | endpoints.brain_settings | v1.py:153-155 |

## 2.7 Schema modules inventory

| Module | Contents | Line refs |
|---|---|---|
| `somabrain/schemas/api.py` | ActRequest/ActStepResult/ActResponse, HealthResponse, PersonalityState, Persona, NeuromodStateModel, SleepRun*/SleepStatus*, PlanSuggestRequest/Response | api.py:14-149 |
| `somabrain/schemas/cognitive.py` | Observation, Thought, Memory, ToolCall, PlanStep (vector normalize validators) | cognitive.py:19-80 |
| `somabrain/api/schemas/sleep.py` | SleepTargetState enum, SleepRequest (unused by endpoints — see 2.5) | sleep.py:19-56 |
| `somabrain/api/schemas/context.py` | EvaluateRequest/Response, FeedbackRequest/Response, RetrievalWeightsState, UtilityWeightsState | context.py:19-80 |
| `somabrain/api/memory/models.py` | MemoryAttachment, MemoryLink, MemorySignalPayload/Feedback, MemoryWriteRequest/Response, ForGet*, batch | models.py:45-208 |

---

# Part 3 — TEST MAP

Legend: **VALID** = exercises a production function/equation; **TAUTOLOGY** = tests a local reimplementation of the formula (asserts a function against itself); **WEAK** = production called but assertion does not pin the claimed theorem; **XFAIL** = marked expected-fail; **GATED** = skipped unless env flag; **META** = repo lint, not math; **MISSING** = no production test found.

## 3.1 Property tests (`tests/property/*.py`)

| Test file / test | Claims to pin | Production target | Verdict | Evidence |
|---|---|---|---|---|
| `test_learning_properties.py::TestAdaptationDeltaFormula` | δ = lr×gain×signal | `AdaptationEngine.apply_feedback` (learning/adaptation/engine.py:322) | **TAUTOLOGY** | Local `compute_delta` test_learning_properties.py:43-45 tested against itself :76-78; never imports AdaptationEngine |
| `test_learning_properties.py::TestConstraintClamping` | clamp to [min,max] | `AdaptationConstraints` (learning/config.py:124) | **TAUTOLOGY** | Local `clamp_value` :48-50 |
| `test_learning_properties.py::TestTauExponentialAnnealing` | τ ← max(floor, τ(1−rate)) | `apply_tau_annealing` (learning/annealing.py:169) / rust | **TAUTOLOGY** | Local `exponential_anneal` :53-55; **also wrong formula** vs production linear mode `τ*(1-rate)` annealing.py:203 and exp mode `τ₀·exp(-γt)` annealing.py:428 |
| `test_learning_properties.py::TestAdaptationReset` | reset restores defaults | `AdaptationEngine` reset | **TAUTOLOGY** | pure local math |
| `test_math_core_properties.py::TestBindSpectralInvariant` | bind spectral magnitude | `QuantumLayer.bind` (admin/core/quantum.py) | **VALID** | imports production :20-21 |
| `test_math_core_properties.py::TestUnitaryRoleNorm` | unitary role unit norm | `QuantumLayer.make_unitary_role` | **VALID** | :20 |
| `test_math_core_properties.py::TestBindingRoundTrip` | bind/unbind invertibility | `QuantumLayer.unbind*` | **VALID** | :20 |
| `test_math_core_properties.py::TestTinyFloorFormula` | tiny floor formula | `compute_tiny_floor` (admin/core/numerics) | **VALID** | :19 |
| `test_math_core_properties.py::TestBHDCSparsityCount` | BHDC sparsity count | `BHDCEncoder` (math/bhdc_encoder.py) | **VALID** | :21 |
| `test_math_core_properties.py::TestNormalizationInvariants` | normalize invariants | numerics normalize | **VALID** | :19 |
| `test_memory_properties.py::test_stable_coord_deterministic/bounds` | coord hash stability/bounds | `MemoryClient._stable_coord` (memory/client.py) | **VALID** | :14 |
| `test_memory_properties.py::test_memory_round_trip` | remember→recall roundtrip | MemoryClient | **VALID (GATED integration)** | :50-53 |
| `test_similarity_properties.py` (all) | cosine symmetry/boundedness/batch | `somabrain.math.similarity` | **VALID** | :14-22 |
| `test_normalization_properties.py` (all) | normalize idempotence/unit-norm/safe | `somabrain.math.normalize` | **VALID** | :17-23 |
| `test_predictor_properties.py::TestChebyshevHeatApproximation` | Chebyshev heat-kernel approx | `somabrain.math.lanczos_chebyshev` | **VALID** | :121-126 |
| `test_predictor_properties.py::TestLanczosSpectralBounds` | Lanczos spectral bounds | same | **VALID** | :121 |
| `test_predictor_properties.py::TestChebyshevLanczosConsistency` | Chebyshev↔Lanczos consistency | same | **VALID** | :121 |
| `test_memory_system_properties.py` (all) | SuperposedTrace decay; WM recall/novelty | `memory.superposed_trace`, `memory.wm.core.WorkingMemory` | **VALID** | :21-22 |
| `test_multitenancy_serialization.py` (all) | tenant isolation; NeuromodState/RecallHit ser/de; timestamps | `admin.brain.neuromodulators`, `memory.client.RecallHit`, `datetime_utils` | **VALID** | :79-84 |
| `test_forbidden_terms.py` | repo comment lint | — | **META** | :5-85 |
| `test_dead_code_removal.py` | dead-code lint | — | **META** | |

## 3.2 Learning math unit tests (`tests/unit/test_learning_math.py`)

| Test | Claims to pin | Production target | Verdict | Evidence |
|---|---|---|---|---|
| `TestTDWeightUpdate::test_positive_reward_increases_alpha` | w += α·G·signal | `AdaptationEngine.apply_feedback` | **VALID** | :40-45 imports engine |
| `TestTDWeightUpdate::test_negative_reward_decreases_weights` | sign of update | same | **VALID** | :54-63 |
| `TestTDWeightUpdate::test_weight_bounds_are_respected` | clamp bounds | engine + AdaptationConstraints | **VALID** | :72-85 |
| `TestTDWeightUpdate::test_learning_rate_affects_update_magnitude` | lr scales Δ | same | **VALID** | :94-110 |
| `TestSoftmaxTemperature::test_high/low/medium_tau_*` | p=exp(s/τ)/Z | *(none)* | **TAUTOLOGY** | local softmax :129-132, :146-148, :159-161; no production softmax called |
| `TestEntropyCapEnforcement::test_sharpening_reduces_entropy` | H ≤ cap after sharpen | `check_entropy_cap` (learning/annealing.py) | **WEAK** | calls production :190-199 but asserts hardcoded `entropy < 1.4` :208-210, not the configured cap |
| `TestEntropyCapEnforcement::test_no_crash_on_high_entropy` | never raises | `check_entropy_cap` | **VALID** | :219-232 |
| `TestEntropyCapEnforcement::test_low_entropy_no_change` | no sharpen below cap | `check_entropy_cap` | **WEAK** | assertion is a tautological `or` :256 |
| `TestTauAnnealing::test_linear_decay_formula` | τ(t)=max(τmin, τ0−αt) | `linear_decay` (annealing.py:396-411 → rust) | **VALID** | :275-280 |
| `TestTauAnnealing::test_exponential_decay_formula` | τ(t)=τ0·exp(−γt) | `exponential_decay` (annealing.py:414-428) | **VALID** | :289-295 |
| `TestTauAnnealing::test_tau_min_floor_respected` | floor | `linear_decay` | **VALID** | :305-308 |
| `TestTauAnnealing::test_exponential_decay_monotonic` | monotonic decrease | `exponential_decay` | **VALID** | :317-323 |

## 3.3 Integration learning proof (`tests/integration/test_learning_proof.py`)

| Test | Claims to pin | Production target | Verdict | Evidence |
|---|---|---|---|---|
| `test_learning_proof_semantic_adaptation` | α rises on reward | `AdaptationEngine.apply_feedback` + RetrievalWeights | **VALID** | :34-53 |
| `test_learning_proof_temporal_adaptation` | γ rises on reward | same (with `AdaptationGains` gamma override) | **VALID (WEAK claim)** | :74-90; comment admits "reward is shared" :87-89 — does **not** prove DA/semantic/temporal separation |
| `test_learning_proof_entropy_reduction` | entropy falls as one weight dominates | engine weights | **VALID (local entropy fn)** | :101-117; entropy computed locally :101-105 (TAUTOLOGY for entropy, VALID for engine) |
| `test_learning_proof_tau_annealing` | τ decays under anneal config | `apply_tau_annealing` via engine | **XFAIL** | `@pytest.mark.xfail` :122-124 ("flaky in CI"); also patches `settings.tau_anneal_rate` :132-133 — **wrong attribute names** vs `SOMABRAIN_TAU_ANNEAL_RATE` (cognitive.py:337) |

## 3.4 Math smoke (`tests/smoke/math_smoke_test.py`)

| Test | Claims to pin | Production target | Verdict | Evidence |
|---|---|---|---|---|
| `run()` | bind/unbind cosine, role spectrum, normalize tiny, tiny floor | `QuantumLayer`, `numerics` | **MISSING as test** | Script with `print` only — **zero assertions** :26-57; `if __name__ == "__main__"` :60-61. Not collected as a test. |

## 3.5 Proofs (`tests/proofs/**`) — scoped summary

| File | Claims | Production target | Verdict | Notes |
|---|---|---|---|---|
| `category_a/test_hrr_math.py::test_wiener_filter_optimality` | "Wiener filter minimizes reconstruction error" (A1.5) | `QuantumLayer.unbind_wiener` (quantum.py:433) | **WEAK (VALID callsite)** | Asserts only \|sim_exact − sim_wiener\| < 0.05 :282-285 and sim > 0.1 :289 — does **not** assert Wiener ≤ exact error. Docstring admits BHDC Wiener is alias of exact :252-253. |
| `category_a/test_hrr_math.py` (bind/unbind/spectral/role) | HRR algebra | `QuantumLayer` | **VALID** | :24-25 |
| `category_a/test_salience_math.py` (all) | S = w_n·novelty + w_e·error; soft salience bounds | *(none)* | **TAUTOLOGY** | local `compute_salience`/`soft_salience`/`fd_energy` :26-62; no import of amygdala/salience production |
| `category_a/test_predictor_math.py` (all) | Mahalanobis, uncertainty growth, Chebyshev bounds | *(none)* | **TAUTOLOGY** | local `mahalanobis_distance` :65; numpy chebval :233; no `somabrain.predictors` import |
| `category_a/test_similarity_math.py` | cosine properties | `somabrain.math.similarity` + `normalize_array` | **VALID** | :23-26 |
| `category_a/test_wm_promotion.py` | promotion threshold/ticks | `memory.promotion.PromotionTracker`, `WMLTMPromoter` | **VALID** | :54, :102, :222 |
| `category_b/test_wm_capacity.py`, `test_wm_persistence.py`, `test_memory_roundtrip.py`, `test_ltm_search.py`, `test_fusion.py`, `test_graph_operations.py` | WM/LTM behavior | memory stack | **VALID (many GATED)** | skipif infra flags on several files |
| `category_c/test_learning.py` | C3.1–C3.5 learning | `somabrain.adaptive.core.AdaptiveParameter` | **VALID but WRONG TARGET for learning theorems** + **GATED** | Tests `adaptive.core`, **not** `learning.adaptation.AdaptationEngine`. `test_tau_annealing_decay` :143-185 does **not** test τ annealing — only Δ∝delta magnitude. Entire file skipif `SOMA_INFRA_AVAILABLE!=1` :27-30 |
| `category_c/test_neuromodulators.py` | neuromod behavior | `NeuromodState` / PerTenantNeuromodulators | **VALID (state I/O)** + **GATED** | Does **not** pin DA→LR wiring (see 3.7) |
| `category_c/test_context.py`, `test_planning.py` | context / planning | context + plan engine | **VALID (GATED)** | planning also skipif SFM down :73 |
| `category_d/*` | tenant isolation | runtime state stores | **VALID (GATED)** | |
| `category_e/*` | resilience, outbox, memory e2e, health | infra | **VALID (GATED)** | |
| `category_f/*` | degraded mode, circuit CB | cb registry | **VALID (GATED)** | |
| `category_g/*` | throughput, serialization, recall quality, latency | memory stack | **VALID (GATED)** | |
| `category_h/*` | metrics, tracing | metrics modules | **VALID** | |
| `test_brain_docker_proof.py`, `verify_brain_memory_bridge.py`, `verify_gmd_canvas_alignment.py` | e2e / bridge / GMD canvas | various | **VERIFY SCRIPTS** | `verify_*` are scripts; `test_brain_docker_proof.py` is pytest |

## 3.6 Theorems with NO production test (MISSING)

| Theorem / claim | Spec source | Production site | Test status | Required test |
|---|---|---|---|---|
| **Wiener λ*(p) = σ_ε²/σ_v² ≈ 5.126e-6 / (p(1−p))** | docs/SomabrainGMD.md:204-224; PLAN-MASTER W4.1 | `compute_wiener_lambda` (mathcore.rs / bhdc_encoder.py) feeding binder + quantum + `gmd_lambda_reg` | **TESTED (W4)** `tests/property/test_mathcore_wiener_fwht.py::TestWienerLambdaFormula` | (done) formula == default λ at production p |
| **DA → LR wiring** (dopamine scales learning rate) | runtime/neuromodulators.py:17 "Dopamine: Modulates learning rate" | `AdaptationEngine._update_learning_rate` engine.py:350-358 (`lr_scale = clip(0.5+DA, 0.5, 1.2)`); `RustAdaptationEngine.update_learning_rate` rust_engine.py:98-100 | **MISSING** | Set DA high/low, assert `engine.learning_rate` scales per formula; assert bounds [0.5, 1.2] |
| **Anneal uniqueness** (single closed-form schedule; linear/exp/step consistent Python↔Rust) | PLAN-MASTER W1/W4 | annealing.py:199-209 (modes) vs :396-428 (decay fns) vs tasks/temperature_anneal.py (factor×interval) | **MISSING** | For fixed (τ0, rate, t) assert linear_decay ≡ apply_tau_annealing(linear) ≡ rust; exp path currently "doesn't apply per-feedback annealing" annealing.py:200-201 — pin that too |
| **Entropy cap H ≤ cap** with configured cap (not 1.4) | cognitive.py:341-342 | check_entropy_cap / entropy_guard.py:30 | **WEAK only** (3.2) | Assert returned entropy ≤ `SOMABRAIN_ENTROPY_CAP` when enabled |
| **Salience weighted formula** S = w_n·n + w_e·e on production path | cognitive.py:213-214 | amygdala / salience modules | **MISSING (existing test is TAUTOLOGY 3.5)** | Import production salience fn; pin formula + thresholds |
| **Mahalanobis predictor** (production provider default "mahal") | cognitive.py:386 | somabrain/predictors/* | **MISSING (existing test is TAUTOLOGY 3.5)** | Pin production predictor Mahalanobis + Chebyshev K path (`CHEBYSHEV_K` vs `TRUTH_CHEBYSHEV_K` must be unified first — DEF-08) |
| **Softmax temperature τ selection in production vote/selection** | docstring test_learning_math.py:113-121 | WM vote / planner selection | **MISSING (local softmax only)** | Pin production softmax with `SOMABRAIN_MICRO_VOTE_TEMPERATURE` / τ |
| **Wiener vs exact optimality** (Wiener error ≤ exact under noise) | test claim A1.5 | quantum.py:302-318 | **WEAK** (3.5) | assert err_wiener ≤ err_exact for noisy binds |
| **τ bounds SOMABRAIN_TAU_MIN/MAX respected by engine** | cognitive.py:188-189 | engine.py:402 + annealing | **MISSING** | engine-level floor/ceiling test (only pure-fn floor test exists) |
| **Neuromod API range enforcement** | `contracts.NEURO_BOUNDS` + neuro.py MIN/MAX | neuromod.py `checked_value` | **FIXED (W2)** | `tests/unit/test_neuromod_wiring.py::TestApiBounds` rejects out-of-box / NaN / inf |
| **brain_settings mode-override math** (TRAINING/RECALL/ANALYTIC/SEARCH/SLEEP presets) | modes.py:11-55 | BrainSetting.get :81-94 | **MISSING** | Assert mode switch changes effective gmd_eta/tau/graph_hops as specified |
| **Duplicate-default identity** (DEF-01…DEF-14) | this doc §1.9 | settings/*.py | **MISSING** | Contract tests: one name, one default per concept |

## 3.7 Coverage summary

| Category | VALID | WEAK | TAUTOLOGY | XFAIL | META/SCRIPT | MISSING theorems |
|---|---|---|---|---|---|---|
| property | 8 files | — | 1 file (learning_properties) | — | 2 | — |
| unit learning_math | 8 tests | 2 | 3 (softmax) | — | — | — |
| integration learning_proof | 3 | — | 1 (local entropy) | 1 | — | — |
| smoke math | — | — | — | — | 1 (no asserts) | — |
| proofs category_a | 4 files | 1 (Wiener) | 2 (salience, predictor) | — | — | — |
| proofs category_c | 4 files (GATED) | 1 mis-targeted | — | — | — | DA→LR, τ anneal |
| theorems | — | — | — | — | — | **12 rows §3.6** |

---

# Part 4 — Defect register (feeds Wave W1)

| ID | Class | Summary | Fix direction (no shims) | Status |
|---|---|---|---|---|
| DEF-01 | config shadowing | django_core overwrites cognitive WM math defaults via base.py star-import | Single declaration site; delete one; align brain_settings seed | **FIXED (W1b)** |
| DEF-02 | triple default | WM_RECENCY_TIME_SCALE 1.0 / 60.0 / 3600 | One key, one default; remove call-site fallbacks | **FIXED (W1b)** |
| DEF-03 | call-site defaults | salience threshold 0.5 vs 0.6; anneal step interval 0 vs 10 | R-VAL-01: values declared once | **FIXED (W1b)** |
| DEF-04 | dead twins | SOMABRAIN_RETRIEVAL_* vs RETRIEVAL_* (and ~10 more pairs) | Keep SOMABRAIN_* names; delete twins after reader audit | **FIXED (W1b)** |
| DEF-05/06 | tau floor/schedule split | TAU_MIN 0.4 vs TAU_MIN_FLOOR 0.1; decay rate vs factor | Unify schedule API in learning/annealing + one settings family | **FIXED (W1b)** |
| DEF-07 | Wiener λ* | **FIXED (W4)** — `compute_wiener_lambda(p, 8)` is the only source | done (PLAN W4.1) | **FIXED (W4)** |
| DEF-08 | Chebyshev K | 30 vs 32 vs 30 | One key consumed by predictors and lanczos_chebyshev | **FIXED (W1b)** |
| DEF-09 | bounds vs default | predictor_gamma default −0.5 outside [0,1] | Align bounds or default | **OPEN** (W3) |
| DEF-10 | HRR dim | 8192 vs 512 | One dim (seam unity) | **FIXED (W1b)** |
| DEF-11/12 | sleep schedule | K0 10 vs 100; duplicate BRAIN_DEFAULTS sleep keys | Deduplicate models.py dict; one seed | **FIXED (W1b)** |
| DEF-13 | naming | adapt_* vs adaptation_* vs SOMABRAIN_ADAPTATION_* | One namespace | **FIXED (W1b)** |
| DEF-14 | missing keys | context/builder.py:92-101 references undeclared settings attrs | Rename readers to real declared keys | **FIXED (W1b)** |
| API-01 | unvalidated input | `/neuromod/adjust` floats unclamped | Reject out-of-box at boundary via `checked_value` | **FIXED (W2 / DEBT-003)** |
| API-02 | schema drift | sleep endpoints use raw dict; api/schemas/sleep.py unused | Bind endpoints to SleepRequest | OPEN (W2) |
| API-03 | auth gap | calibration router has no api_key_auth | Align with require_auth pattern | OPEN |
| TEST-01 | tautologies | learning_properties, salience_math, predictor_math, softmax tests | Rewrite against production imports | OPEN (W5) |
| TEST-02 | missing theorems | §3.6 twelve rows | Wave W4 contract tests | OPEN (W4) |

---

# Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | (issue) | DOC-A4 | Initial truth tables: config (incl. 14 defect rows), API (6 endpoint groups), test map (VALID/TAUTOLOGY/XFAIL/MISSING) |

**End of document SOMA-BR-CONFIG-API-TEST-001 Rev A**
