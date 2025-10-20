SomaBrain — Detailed Sprints and Roadmap

Planning Assumptions
- Cadence: 2-week sprints; release at end of each sprint if criteria met.
- Team: 1–2 backend engineers; optional ML backend support; 1 DevOps.
- Environments: Local dev (in-proc memory), staging (HTTP memory), optional prod.
- SLOs: /act p95 ≤ 150ms (stub), ≤ 600ms (LLM); /recall p95 ≤ 80ms with WM/cache hit.

Product Goals (MVP → Advanced)
- MVP: Brain-like control loop with WM, salience, prediction error, episodic/semantic memory, reflection seed, metrics, multi-tenancy, quotas.
- Near-term: HRR cleanup, reflection clustering + reconsolidation, graph reasoning, stable configs.
- Mid-term: LLM/ML predictor providers with budgets/fallbacks; Dockerization; migration endpoints.
- Advanced: attention/gain control, reward signals, meta-learning thresholds; multi-agent messaging; HRR-first reasoning.

Timeline Overview
- Sprint 1: HRR cleanup + WM integration and metrics
- Sprint 2: Reflection v2 (clustering + semantic summaries + reconsolidation)
- Sprint 3: Graph reasoning (links, k-hop), Hebbian updates
- Sprint 4: Personality persistence + influence in /act
- Sprint 5: Predictor providers (LLM/ML) + latency budgets + degradation
- Sprint 6: Migration export/import; API hardening, auth/rate/quotas polish
- Sprint 7: Dockerization + ops; SLO validation; basic load tests
- Sprint 8: Multi-agent prep (events, configs); HRR-first recall mode

Sprint 1 — HRR Cleanup Integration (2 weeks)
- Objectives: Apply HRR superposition/cleanup to retrieval path; surface metrics.
- Stories/Tasks:
  - Wire `MultiTenantHRRContext.cleanup()` into /recall and /act ranking (feature flag `use_hrr_cleanup`).
  - Add context anchors admission policy (LRU, cap via `hrr_anchors_max`).
  - Metrics: cleanup accuracy (top-1 match rate), cosine distribution; anchor count per tenant.
  - Config: Dynaconf toggles for HRR path; defaults off.
  - Fix: dead code in `memory_client.store_from_payload` tail.
- Acceptance Criteria:
  - With HRR enabled, /act and /recall include HRR cleanup influence; metrics exposed at `/metrics`.
  - Cleanup accuracy ≥ 0.95 on single-item retrieval synthetic test.
- Artifacts:
  - Code diffs, updated docs, HRR cleanup section in README.

Sprint 2 — Reflection v2 (2 weeks)
- Objectives: Cluster episodic memories; produce semantic summaries; reconsolidate and link.
- Stories/Tasks:
  - Implement episodic clustering (e.g., mini-batch TF-IDF + cosine or simple keyword Jaccard), pluggable summarizer.
  - Extend `/reflect` to create semantic summaries per cluster and link to sources.
  - Add policies: min cluster size, max summaries, reconsolidation rules.
  - Metrics: reflection batch throughput, clusters formed, summaries created, link success rate.
- Acceptance Criteria:
  - `/reflect` returns created summaries with ≥ 80% of episodics linked (local mode).
  - Configurable clustering and thresholds; metrics visible in Prometheus.
- Artifacts:
  - Reflection doc updates; examples.

Sprint 3 — Graph Reasoning (2 weeks)
- Objectives: Create/consume links; support k-hop traversal; Hebbian edge updates on co-recall.
- Stories/Tasks:
  - MemoryClient: link APIs (HTTP + local), k-hop query abstraction (local), weight updates.
  - /recall: optional graph-augmented recall (expand 1–2 hops, re-rank).
  - Metrics: k-hop latency, link counts, Hebbian updates rate.
- Acceptance Criteria:
  - Local mode: create links and query k-hop with median latency ≤ 30ms for small graphs.
  - /recall can include graph-augmented items when flag enabled.

Sprint 4 — Personality (2 weeks)
- Objectives: Persist personality traits and use them to modulate decisions in /act.
- Stories/Tasks:
  - `/personality` GET/POST persistence via memory backend (semantic type), per tenant.
  - Influence salience thresholds and predictor selection using traits/preferences.
  - Metrics: personality hits, modulation deltas.
- Acceptance Criteria:
  - Traits persist and are retrieved per tenant; /act behavior measurably changes under trait toggles.

Sprint 5 — Predictor Providers (2 weeks)
- Objectives: Add pluggable predictor interfaces with budgets/fallbacks.
- Stories/Tasks:
  - Predictor interface (sync/async). Providers: Stub, Echo, LLM (placeholder stub for restricted env), external callable adapter.
  - Budgeting: timeouts, circuit breaker, degrade to novelty-only salience when over budget.
  - Metrics: predictor latency histogram, error distribution, fallback counts.
- Acceptance Criteria:
  - Timeouts enforced; fallback path exercised in tests; /act p95 within budgets for configured providers.

Sprint 6 — Migration + Hardening (2 weeks)
- Objectives: Export/import flows and API hardening.
- Stories/Tasks:
  - `/migrate/export` and `/migrate/import` finalize manifest fields; verify restore of WM/HRR anchors.
  - Input validation, error responses, stricter auth options (required tokens), rate/quotas config surfaced.
  - Add smoke tests for /act, /recall, /remember, /reflect; basic schema/version headers.
- Acceptance Criteria:
  - Export/import round-trip reconstructs core state (payloads + WM warm start) with no errors; tokens/rate/quotas configurable and enforced.

Sprint 7 — Ops & Packaging (2 weeks)
- Objectives: Dockerization and SLO validation.
- Stories/Tasks:
  - Minimal Dockerfile + compose (SomaBrain + local memory service when HTTP mode is used).
  - Load test scripts (k6/locust) to validate SLOs; dashboards for key metrics.
  - Logging: structured JSON with bounded fields; redaction list.
- Acceptance Criteria:
  - Container builds and runs locally; SLOs achieved on dev hardware; logs are structured and sized.

Sprint 8 — Multi-Agent Prep + HRR-First Mode (2 weeks)
- Objectives: Prepare for event-based multi-agent and enable HRR-first retrieval mode.
- Stories/Tasks:
  - Event hooks (callbacks) for store/recall/reflect; pluggable bus adapter interface (future Kafka/RabbitMQ).
  - HRR-first retrieval mode: query via HRR context + cleanup with optional memory hybrid.
  - Metrics: event dispatch counts, HRR-first recall hit rate.
- Acceptance Criteria:
  - Bus interface defined and no-op default; HRR-first mode functional and configurable.

Technical Roadmap by Component
- WM/Embeddings: deterministic 256-D path stable; optional HRR random projection bridge later.
- MemoryClient: unify local/HTTP capabilities (link, k-hop). Improve retries/backoff for HTTP.
- HRR/Quantum: anchors policy, cleanup metrics, temporal encoding via permutations for sequence modeling.
- Predictor: interface + providers; bounded error metric; offline tests.
- Reflection: clustering, summarization, reconsolidation policies; batch scheduler (future).
- Personality: trait schema, storage, modulation hooks in salience/predictor.
- API: input normalization, schema/version headers, richer responses.
- Observability: expand counters/histograms; bounded-cardinality labels; add error histograms.
- Security: token auth required option, quotas persisted (optional Redis), sensitive field redaction.
- Ops: Docker, compose for memory backend, load tests, dashboards.

Risks & Mitigations
- Predictor latency variance → budgets + degrade to novelty-only path; circuit breaker.
- Salience calibration across domains → config profiles; add auto-tune hooks; metrics.
- Multi-tenant memory isolation → enforce namespace composition; tests for cross-tenant leakage.
- HTTP backend reliability → retries/backoff; health checks; fallback to local when configured.

Milestones & Releases
- M1 (after Sprint 2): HRR cleanup + Reflection v2 release.
- M2 (after Sprint 4): Personality + Graph reasoning release.
- M3 (after Sprint 6): Predictor providers + Migration + Hardening release.
- M4 (after Sprint 7/8): Ops packaging + HRR-first + Multi-agent prep.

Definition of Done (per feature)
- Code + unit tests updated; docs (README, Architecture, or Snapshot) updated.
- Metrics emitted and visible in `/metrics`.
- Configurable via Dynaconf/env with safe defaults.
- Meets acceptance criteria and SLO budgets in local/staging.

