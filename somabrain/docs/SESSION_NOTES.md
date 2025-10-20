SomaBrain — Session Snapshot

Context
- Core MVP implemented: FastAPI API (/act, /recall, /remember, /reflect, /personality, /health, /metrics), multi‑tenancy, WM with deterministic embeddings, salience + policy, predictor budgets, local/HTTP memory, semantic graph v1, reflection v2, consolidation (NREM/REM), executive controller, planner v1, optional microcircuits.
- HRR path available behind flags (quantum layer + cleanup); optional HRR‑first WM rerank.
- Observability: Prometheus metrics across components; drift and reality monitors integrated in /recall.

Decisions (this session)
- Keep biology/chemistry/physics mapping explicit in module names (Thalamus, Amygdala, Cerebellum, etc.).
- Prioritize small, high‑impact deltas first: link reflection summaries to source episodics; then expand universe scoping and ACC “lesson” semantics.
- Persist session notes for future context reuse; avoid CI/compose changes in this pass.

Roadmap Alignment
- Phase 1/2: largely complete (WM, episodic/semantic, salience, predictor error loop, reflection/sleep, personality).
- Phase 3: partial (HRR context/cleanup, WM rerank). Pending deeper HRR graph/bind‑unbind and LTM rerank.
- Phase 4: pending (multi‑agent bus, distributed coordination).

Next Steps
- Reflection linking: add `summary_of` links from generated summaries to their source episodics (implemented next).
- Universe scoping: thread `universe` through store/recall paths and planner; honor executive target_universe in more flows.
- ACC lessons: on high prediction error, create corrective semantic memories and link to sources (feature‑flagged).
- HRR‑first hybrid: extend rerank to LTM path; expose weight and ablation metrics.
- Decay/pruning: configurable age/importance pruning; metrics.
- CI/compose: add docker‑compose and a minimal CI pipeline for smoke scripts.

