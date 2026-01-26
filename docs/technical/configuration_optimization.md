# SomaBrain Configuration Optimization Analysis & Recommendations

**Version:** 1.0.0
**Status:** DRAFT
**Author:** Antigravity (SomaBrain Lead Architect)

## 1. Executive Summary

SomaBrain's configuration surface area (~300 parameters) presents a significant "Brittle Brain" risk. While flexible, maintaining optimal values across diverse workloads (e.g., creative writing vs. factual recall) via static `.env` files is unsustainable.

A review of the architecture reveals a **strong existing foundation for self-tuning**:
*   **Rust Core**: Implements mathematical theorems (GMD MathCore) that derive optimal values (e.g., `compute_optimal_p`, `compute_wiener_lambda`) from fundamental constraints rather than heuristics.
*   **Adaptive Service Layer**: `Neuromodulators` and `AdaptationEngine` already implement learning loops.

**Recommendation**: Shift from "Human-Tuning" to "Meta-Control". Do not expose 300 knobs to the user. Expose 3 high-level "Presets" and let the `AdaptationEngine` tune the rest dynamically.

---

## 2. Taxonomy of Knobs

We categorize the settings into three tiers based on their lifecycle and risk.

### Tier 1: System Invariants (DO NOT TOUCH)
*These depend on mathematical theorems or infrastructure hard-constraints. Changing them requires code changes or database migrations.*
*   **Examples**: `SOMABRAIN_EMBED_DIM` (8192), `SOMABRAIN_WM_SIZE`, `SOMABRAIN_NEURO_*_BASE` (initial priors).
*   **Management**: Static `.env` or hardcoded constants.

### Tier 2: Structural Configuration (Deploy-Time)
*These define the shape of the deployment and resource limits.*
*   **Examples**: `SOMABRAIN_POSTGRES_DSN`, `SOMABRAIN_WORKERS`, `SOMABRAIN_MEMORY_MAX`.
*   **Management**: Infrastructure-as-Code (Kubernetes/Helm/Docker Compose).

### Tier 3: Cognitive Dynamics (The "Knobs") - **The Optimization Target**
*These control the "personality" and efficacy of the brain. They are sensitive to workload.*
*   **Examples**:
    *   `INTEGRATOR_TAU`: Softmax temperature (Creativity/Determinism).
    *   `SOMABRAIN_ADAPT_LR`: Learning rate (Plasticity).
    *   `OAK_NOVELTY_THRESHOLD`: Curiosity.
    *   `SOMABRAIN_SALIENCE_THRESHOLD`: Attention filter.

---

## 3. Optimization Strategy: The Meta-Controller

Instead of manually tuning Tier 3 parameters, we propose a **Meta-Controller Architecture**.

### 3.1. High-Level Presets
Map intuitive user intents to parameter ranges.

| Preset | Intent | Key Parameter Shifts |
| :--- | :--- | :--- |
| **STABLE** (Default) | Reliable, factual recall. | `tau` ≈ 0.8 (Low), `learning_rate` ≈ 0.01 (Slow), `serotonin` (Stability) Boosted. |
| **PLASTIC** | Rapid learning, fast adaptation. | `learning_rate` ≈ 0.1 (Fast), `dopamine` (Reward sensitivity) Boosted, `saliency` Threshold Lowered. |
| **LATERAL** | Creative association, brainstorming. | `tau` ≈ 2.0 (High), `graph_hops` Increased, `rem_recomb_rate` Boosted. |

### 3.2. Dynamic Self-Tuning (The Loop)
Leverage the existing `AdaptationEngine` (`somabrain/learning/adaptation.py`) to tune these values in real-time.

1.  **Monitor**: `ParameterSupervisor` watches `success_rate` and `latency`.
2.  **Modulate**:
    *   If `success_rate` drops → Increase `dopamine` (Motivation) → Increases `learning_rate`.
    *   If `entropy` is too high (confusion) → Decrease `tau` (Focus).
3.  **Persist**: Save learnt optimal weights per-tenant in Redis/Postgres (already supported by `AdaptivePerTenantNeuromodulators`).

---

## 4. Immediate Action Plan

1.  **Code Changes**:
    *   Refactor `ParameterSupervisor` to actively write to `Settings` (or a dynamic config store) based on the feedback loop.
    *   Formalize the Presets in `somabrain/presets.py` to allow one-click reconfiguration.

2.  **Documentation**:
    *   Publish this report as `docs/technical/configuration_optimization.md`.
    *   Add a "Tuning Guide" section to `AGENT.md` for developers.

3.  **Observability**:
    *   Create a Grafana dashboard targeting *only* Tier 3 parameters to visualize the "Brain State" (Anxiety vs. Boredom, effectively).

## 5. Risk Assessment

*   **Oscillation**: If `learning_rate` and `tau` adaptation loops resonate, the brain could become unstable.
    *   *Mitigation*: Enforce hard bounds (as implemented in `AdaptiveParameter` fields `min_value`/`max_value`).
*   **Cold Start**: A new tenant has no history.
    *   *Mitigation*: Use accurate, conservative defaults (The "STABLE" preset).

---
**Verdict**: The system is capable of managing its own complexity. We just need to wire the existing `Neuromodulators` (Architecture) to the `Settings` (Configuration) more tightly.
