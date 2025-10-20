SomaBrain — Project Snapshot

Context
- Purpose: Cognitive intelligence layer over SomaFractalMemory. Mimics brain anatomy and neurochemistry to drive recall, prediction, salience, reflection, and planning via FastAPI.
- Repo state: Core MVP implemented with multi‑tenancy, rate limits, quotas, metrics, and optional HRR path. Example script validates the memory layer.

Current Status
- API endpoints live: /act, /recall, /remember, /reflect, /personality, /health, /metrics.
- Working Memory: 256‑D deterministic embeddings; similarity recall; novelty scoring.
- Salience & Policy: AmygdalaSalience with neuromodulators; BasalGangliaPolicy for gates.
- Predictor: CerebellumPredictor (alias of StubPredictor); cosine error baseline.
- Memory: MemoryClient with local in‑proc (default) or HTTP mode; per‑tenant namespaces.
- Multi‑tenant: WM and memory pool keyed by `X-Tenant-ID`; short‑TTL recall cache; per‑tenant rate limit + daily write quota.
- Metrics: Prometheus counters/histograms; `/metrics` endpoint.
- HRR Path: QuantumLayer (HRR ops) and tenant HRR context feature‑flagged via config; optional HRR cleanup signal available in `/recall` when enabled.

Current Stage
- Phase: B (Next 2–4 weeks) — in progress
- Sprint status: Sprint 1 (HRR cleanup signal + metrics) completed; Sprint 2 (Reflection v2 clustering/summaries) completed; preparing Sprint 3 (Graph reasoning: links, k‑hop, Hebbian updates).

Architecture (Anatomy Map)
- ThalamusRouter → input normalization, routing, rate‑limit/auth integration.
- PrefrontalWM (WorkingMemory) → WM buffer, cosine recall, novelty.
- AmygdalaSalience → salience score from novelty + prediction error, modulated by neuromods.
- BasalGangliaPolicy → go/no‑go decisions for store/act gates.
- CerebellumPredictor → predictor + error (stub); pluggable provider later.
- HippocampusEpisodic / CortexSemantic → MemoryClient for episodic/semantic memory; graph links.
- Neuromodulators → dopamine/serotonin/noradrenaline/ACh state and callbacks.
- QuantumLayer + HRRContext → superposition/binding/unbinding/cleanup; tenant HRR context.

Biology/Chemistry Mapping (Design Intent)
- Hippocampus ↔ episodic encoding/recall; Cortex ↔ long‑term semantic.
- Prefrontal ↔ WM/exec; Thalamus ↔ gating; ACC ↔ conflict/error; Cerebellum ↔ prediction.
- Dopamine ↔ error weight; Noradrenaline ↔ gain/thresholds; ACh ↔ focus; Serotonin ↔ stability.
- Hebbian strengthening ↔ graph edge weight updates on co‑recall (planned).

Decisions
- Default memory backend: local in‑proc; HTTP for prod — configurable.
- Deterministic embeddings for MVP; HRR path behind feature flag.
- Per‑process, tenant‑scoped WM/HRR context; stickiness acceptable for now.
- Quotas/rate limits per tenant; optional bearer token auth.

Roadmap
- Near term: HRR cleanup/anchors, reflection clustering + semantic reconsolidation, graph reasoning (k‑hop), personality persistence/influence.
- Mid term: LLM/ML predictor provider; MCP tools integration; Dockerization.
- Advanced: attention via thalamus/neuromod gain control, reward‑based gating, meta‑learning thresholds, predictive memory with corrections.

Next Steps
- Implement HRR cleanup in WM path and measure cleanup accuracy.
- Reflection: cluster episodics, produce semantic summaries, link to sources.
- Graph reasoning: expose link APIs and k‑hop queries; Hebbian edge updates.
- Personality: persist traits and feed into /act decisions.
- Add smoke tests: /act happy path and WM recall correctness.

Operational Notes
- Start API: `uvicorn somabrain.app:app --reload`
- Example memory layer: `python examples/soma_quickstart.py`
- Config via `config.yaml` and `SOMABRAIN_*` env; defaults favor local dev.

References
- Overview: README.md:1, docs/SomaBrain.md:1
- Architecture: docs/Architecture.md:1
- Use cases: docs/UseCases.md:1
- Progress log: PROGRESS.md:1
- Anatomy aliases: somabrain/anatomy.py:1

Observations
- Memory HTTP/link code path: a leftover block at the bottom of `somabrain/memory_client.py` appears unreachable; consider cleanup in a dedicated PR.
