PRODUCTION READINESS & ROADMAP for SomaBrain
============================================

Status: Draft — single-source plan for turning the local `cleanup/prepare-release` branch into a production-ready release. This file is the canonical, detailed plan that captures design decisions, priorities, tests, observability, security, release steps, migration utilities and timelines.

Goals
-----
- Ensure memory durability, observability, and correct numerics for HRR/quantum components.
- Provide reliable CI, reproducible builds, and clear release/checklist for pushing to remote registries.
- Harden operations (monitoring, alerting, metrics) so incidents are detected early and triaged quickly.
- Protect data (PII/sensitive content), provide provenance, and make migration between memory backends safe.

Acceptance criteria (what “ready for remote push” means)
--------------------------------------------------------
1. Unit and integration tests: all tests pass locally and in CI; coverage targets met for core modules (numerics, memory_client, journal, recall path).
2. Docker image builds reproducibly; smoke test verifies `/health` and `/metrics` on container startup.
3. Journaling: persistent journal append/replay validated; migration tool exists to import journal into chosen persistent backend.
4. Monitoring: Prometheus scrapes `/metrics`; Grafana dashboard imports and shows tiles & sparklines; basic alert rules trigger in test scenarios.
5. Quotas: production quota backed by durable store (Redis) or otherwise explicitly documented tradeoffs.
6. Security: admin endpoints require tokens; secrets not hard-coded; documentation includes secret management guidance.
7. Release checklist documented and followed; no remote push without manual approval by project lead.

High-level plan (phases)
------------------------
Phase A — Verify & Harden (0–3 days)
- A1 Run full test suite, fix critical failures. (P0)
- A2 Validate journaling: write memory -> confirm JSONL append -> restart server -> replay shows memory. (P0)
- A3 Add/verify CI pipeline for tests & linters. (P0)

Phase B — Observability & Alerts (1–7 days)
- B1 Build Prometheus + Grafana compose file and example `prometheus.yml`. (P1)
- B2 Create Grafana dashboard JSON (panels for the KPIs below). (P1)
- B3 Add Alertmanager rules and test alert firing. (P1)

Phase C — Durability & Scale (3–14 days)
- C1 Decide on production memory backend: persistent somafractalmemory vs external store (qdrant/faiss) + implement migration tooling. (P0/P1)
- C2 Implement Redis-backed quota manager (pluggable) or document and accept tradeoffs. (P0/P1)

Phase D — Security, Release & Ops (3–10 days)
- D1 Add token-based auth for admin endpoints; audit require_auth flow. (P0)
- D2 Add release process, automated build, and image publish (manual gate). (P1)
- D3 Add data redaction options for journaling; document retention & encryption. (P1)

Core tasks & checklist (concrete items)
---------------------------------------
Each item has: Task, Owner (TBD), Priority (P0..P2), Est Effort (hours), Acceptance.

A. Verify & Harden
- Run tests (pytest). P0, 1–3h. Acceptance: tests pass; failures triaged.
- Fix any unit test regressions introduced by numerics hardening. P0, 1–2d.
- Add integration test for remember->journal append->restart->replay->recall. P0, 4–8h. Acceptance: test passes. This guards durability.
- Add a tiny smoke script: POST /remember (sample payload) -> GET /recall -> assert memory present. P0, 2–4h.

B. Observability & Alerts
- Provide `docker-compose.monitoring.yml` including somabrain, Prometheus, Grafana, Alertmanager (optional). P1, 1–3d.
- Create `prometheus.yml` scrape config for `127.0.0.1:9696/metrics` and compose metadata. P1, 1–2h.
- Create Grafana dashboard JSON; include panels for: requests_total, avg_latency_ms, WM_utilization, WM_admits/min, journal_appends/min, quota_denies. P1, 1–2d.
- Define simple Alertmanager rules and test via synthetic load. P1, 4–8h.

C. Durability & Backend
- Choose backend (meeting production durability): either
  - Option 1: somafractalmemory with persistent storage (on-disk or object store)
  - Option 2: external vector DB (qdrant/FAISS) + metadata store (Postgres/Redis)
  Decision criteria: durability, latency, cost, operational familiarity. P0, research 1–2d.
- Implement `scripts/migrate_journal_to_backend.py` to import journal.jsonl into backend. P1, 1–3d.
- Add tests that the migration tool is idempotent and can be re-run safely. P1, 1–2d.

D. Quotas & Rate Limiting
- Implement Redis-backed `QuotaManager` with the same API. Provide config toggle. P0, 1–3d.
- Add per-tenant quota metrics and dashboards. P1, 4–8h.

E. CI / Release
- GitHub Actions or equivalent: run ruff/black, mypy (optional), pytest, build docs. P1, 1–2d.
- Add a `release` job that builds Docker image; push guarded by manual approval. P1, 1–2d.

F. Security & Governance
- Require token for sensitive endpoints; document usage & rotate keys. P0, 1–2d.
- Add optional payload redaction for journaling (configurable). P1, 1–2d.

G. Documentation & Training
- Add `docs/PRODUCTION_ROADMAP.md` (this file) to docs index; build docs in CI. P1, 2–4h.
- Add operational runbook: how to inspect metrics, how to restore journal, how to run migration. P1, 4–8h.

KPIs, metrics & alert definitions (detailed)
--------------------------------------------
This section contains the KPI formulas and example alert rules you can drop straight into Prometheus/Grafana.

Core KPIs (what to collect & why)
- requests_total (counter): baseline traffic and spike detection.
- avg_latency_ms = (somabrain_http_latency_seconds_sum / somabrain_http_latency_seconds_count) * 1000.
- errors_per_min & error_rate = delta(http_5xx_total)/min and errors/requests.
- WM_utilization = somabrain_wm_utilization (gauge 0..1).
- WM_admits_per_min = delta(somabrain_wm_admit_total) * 60000/poll_ms.
- journal_appends_per_min = delta(JOURNAL_APPEND) * 60000/poll_ms. (metric name may be `JOURNAL_APPEND` or `somabrain_journal_append_total` depending on instrumentation)
- quota_denies_per_min = delta(somabrain_quota_denied_total) * 60000/poll_ms.

Suggested thresholds (initial)
- avg_latency_ms alert: avg_latency_ms > 500ms for 3m.
- WM utilization alert: WM_utilization > 0.85 for 5m.
- Journal vs admits alert: if journal_appends_per_min == 0 AND wm_admits_per_min > 10 for 2m -> SEV1 (durability risk).
- Quota denies: quota_denies_per_min > 0 for 1m (dev) or >5/min in prod -> investigate.
- Error rate: error_rate > 0.01 AND errors_per_min > 5 -> investigate.

Example PromQL expressions
- avg latency (ms): (rate(somabrain_http_latency_seconds_sum[1m]) / rate(somabrain_http_latency_seconds_count[1m])) * 1000
- requests per min: rate(somabrain_http_requests_total[1m]) * 60
- wm admits per min: rate(somabrain_wm_admit_total[1m]) * 60
- journal appends per min: rate(somabrain_journal_append_total[1m]) * 60 OR rate(JOURNAL_APPEND[1m]) * 60

Alert example (yaml pseudo)
```
- alert: HighAvgRequestLatency
  expr: (rate(somabrain_http_latency_seconds_sum[5m]) / rate(somabrain_http_latency_seconds_count[5m])) * 1000 > 500
  for: 3m
  labels:
    severity: page
  annotations:
    summary: "High average request latency"
    description: "Average request latency > 500 ms for 3m"
```

Data migration & backup strategy
--------------------------------
- Journal (JSONL) is authoritative for single-node durability if enabled. Ensure it's written to a durable mounted volume and rotated/compacted regularly.
- For multi-node or scale-out, migrate journal to chosen backend using `scripts/migrate_journal_to_backend.py`. Migration steps:
  1. Pause writers (or coordinate a quiesce window). 2. Export journal snapshot. 3. Run migration script into backend (idempotent mode). 4. Validate count & sample records. 5. Switch reads to backend. 6. Resume writers.
- Add periodic backup job that copies journal segments to object storage with retention policy.

Security & privacy
------------------
- Require tokens for admin endpoints (X-Admin-Token) and document how to rotate.
- Journal redaction: add config `journal_redact_fields = ["content", "who"]` and optionally hash values before persist.
- Encrypt journal at rest via OS-level encrypted volumes or encryption-in-transit to object storage.

CI & release blueprint (GitHub Actions summary)
-----------------------------------------------
- jobs:
  - test: runs ruff/black (if configured), pytest, mypy; artifacts: test-report
  - docs: build docs, upload artifacts/site
  - build: build docker image and run a container smoke test (check /health /metrics), do not push automatically
  - release: manual workflow_dispatch that tags and pushes image to registry (requires manual approval)

Developer ergonomics
--------------------
- Add `.pre-commit-config.yaml` with ruff/black/isort hooks.
- Provide `scripts/dev_start.sh` that launches somabrain in dev mode with example env (non-root, reduced quotas) and `scripts/dev_stop.sh`.
- Provide `scripts/smoke_mem_test.py` to exercise remember->recall->restart->replay flows.

Rollout & rollback plan
-----------------------
- Canary rollout: publish image to internal registry, run small canary instance behind a proxy, run integration tests with canary, monitor KPIs for 15–60 minutes, then promote.
- Rollback: retain previous image tag and roll back if KPIs exceed thresholds; run `scripts/migrate_backend_rollback` if migration was performed.

Owner & communication
---------------------
- Assign owners per area (proposed):
  - Core numerics & tests: Engineering lead (math)
  - Memory backend & migration: Storage/infra lead
  - Observability & dashboards: SRE/Observability
  - Release & CI: DevOps
  - Security & governance: Security lead

How this file should be used
---------------------------
- This file is the single on-disk canonical plan for production readiness. Keep it in `docs/` and update as tasks progress. Each major task must link to a PR and reference this file's section.
- Before pushing to remote: all P0 items must be completed and checked off in a PR with green CI.

Next immediate steps (recommended)
----------------------------------
1. Approve this roadmap file and commit to local branch. (done)
2. Run full test suite and produce a test report (I can run it now, confirm?).
3. Validate journaling end-to-end (I can run an automated script that remembers a sample item, checks JSONL, restarts server and rechecks). Confirm before I proceed.

Notes & rationale (concise)
---------------------------
- Keep the monitoring math simple (averages & rates) for fast triage, then add percentiles and drift metrics as second-order improvements.
- Durability is the single most important property for this project: we are building a memory system that agents rely on. Journal + persistent backend + migration tools is the minimal safe path.
- Observability and alerting prevents data loss and operational surprises during agent experiments.

Appendices (templates & snippets)
---------------------------------
- Example small smoke script to test journaling:
```python
# scripts/smoke_mem_test.py
import requests, time
r = requests.post('http://127.0.0.1:9696/remember', json={'coord': None, 'payload':{'task':'smoke test','importance':1}})
print('remember status', r.status_code, r.text)
# check journal file and restart server externally, then recall
```

- Example Prometheus `prometheus.yml` snippet:
```yaml
scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['host.docker.internal:9696']
```

- Example Graph panel list (for Grafana):
  - Requests per minute
  - Avg latency (ms)
  - Requests by endpoint (stacked)
  - WM utilization %
  - WM admits/min
  - Journal appends/min
  - Quota denies

Document history
----------------
- 2025-09-12: Draft created from repository inspection during development session. Update the file with PR links and progress as tasks are completed.

Verified status (audit) — code-backed summary
--------------------------------------------
Note: the following status was produced by an automated local audit of the repository and running the numerics-focused unit tests. This is a concise, code-backed summary intended to be appended to the roadmap for traceability.

- Audit date: 2025-09-13
- Test evidence: targeted numerics and HRR unit tests executed locally; summary result: 14 passed, 0 failed. (numerics-focused subset)
- Key items verified in source code:
  - Unitary FFT wrappers: `rfft/irfft` are used with norm='ortho' to preserve energy and satisfy HRR unitary contract (see `somabrain/numerics.py`).
  - Deterministic seeding and role generation: seed derivation and deterministic role-spectrum generation implemented (see `somabrain/quantum.py` and `somabrain/numerics.py`).
  - Tiny-floor semantics: sqrt(D)-based amplitude tiny floor and conversion to spectral power floor implemented in `somabrain/numerics.py` (functions `compute_tiny_floor` / `spectral_floor_from_tiny`).
  - Deterministic fallback & Wiener/Tikhonov helpers: `tikhonov_lambda_from_snr` and `wiener_deconvolve` implemented and used as robust unbind fallback (see `somabrain/wiener.py`).
  - Spectral arithmetic robustness: spectral division and clamping logic present with NaN/Inf guards and deterministic renormalize paths (see `somabrain/numerics.py` / `somabrain/quantum.py`).
  - Observability: Prometheus metrics for unbind telemetry and related KPIs are defined and used (see `somabrain/metrics.py`). App routes expose `/metrics` (see `somabrain/app.py`).

- Operational steps already completed in this workspace during the audit:
  - Ran numerics-focused unit tests (passed).
  - Removed an in-repo agent scaffold (untracked files) from the working tree per project policy; no agent code remains tracked in the repository.
  - Verified bench harness scripts exist under `benchmarks/` and that docs describe how to run bench sweeps to produce JSON/PNG artifacts.

- Partial / follow-up items (recommended next work items):
  1. Persistent spectral cache: role spectra are cached in-memory; implement a persistent per-memory spectral cache and a migration utility to recompute/persist spectra for existing memories (C1). (P1)
  2. Centralized unbind policy & auto-calibration: consolidate local heuristics into a pluggable decision policy that can auto-tune Wiener/Tikhonov lambda based on observed SNR histograms (B1/C1). (P1)
  3. Migration tooling idempotency: ensure `scripts/migrate_journal_to_backend.py` (to be created) is idempotent and covered by tests. (P0/P1)
  4. Grafana dashboard JSON: produce an example dashboard that surfaces UNBIND_PATH, RECONSTRUCTION_COSINE, UNBIND_K_EST, and other HRR KPIs. (B2)

- Quick quality-gates run performed during audit:
  - Build: not applicable for pure-Python check here; local imports and syntax checked while reading modules.
  - Tests: targeted numerics tests executed -> PASS (14/0).
  - Lint/type: not re-run in this audit pass (recommended in CI).

Appendix: short reproduction steps I used locally
1. Run the numerics-focused pytest subset that covers HRR/unitary/tiny-floor/wiener code.
2. Inspect `somabrain/numerics.py`, `somabrain/wiener.py`, `somabrain/quantum.py`, and `somabrain/metrics.py` to confirm the implementations described.
3. Confirm `/metrics` endpoint exposure in `somabrain/app.py`.

Summary
-------
The numerics hardening work (unitary FFTs, deterministic seeding, sqrt(D) tiny-floor semantics, deterministic fallback/Wiener) is implemented in the codebase and validated by localized unit tests. Operational work remaining focuses on persistence of spectral caches, centralized unbind policy, and dashboarding/migration tooling. I can implement the persistent spectral cache prototype and the migration script next if you want me to proceed; otherwise I will continue to milestone 6 as you directed.

Personas (paused)
-----------------
Per current direction, detailed persona implementation (definition, sharing, training, and runtime mood/skill overlays) is placed on hold. The persona design, tooling, and migration notes produced during the audit are saved as part of the roadmap and may be resumed later. When ready to resume persona work, follow this short checklist:

- Reconfirm persona governance (who may author/publish personalities and review learned deltas).
- Choose default HRR encoding parameters (dim, dtype, seed policy) for canonical reproducibility.
- Run `scripts/precompute_role_spectra.py` (or schedule via Sleep) to persist role spectra for tokens in planned personas.
- Implement `somabrain/personality.py` utilities and add roundtrip/unbind tests before pilot rollout.

For now, continue with the roadmap phases above (A..G). Persona work will be restarted upon explicit approval and scheduling.

Neuromodulator roadmap (final task)
-----------------------------------
This roadmap item captures the concrete short-, medium-, and long-term work to harden, secure,
and evolve the neuromodulator subsystem used by the brain components (amygdala, thalamus,
prefrontal, supervisor, unified_core). Additions below should be treated as the canonical
last task in the production readiness plan.

Priority: P0 (safety & stability) -> P1 (quality & observability) -> P2 (learned controllers)

Short-term (P0) — safety & stability (1–3 days)
- Protect the HTTP surface: require tenant context and `require_auth` for `POST /neuromodulators` and
  consider requiring auth for `GET /neuromodulators` as well. Add audit logging for manual changes.
- Hide endpoints from public OpenAPI if temporary protection is needed (`include_in_schema=False`).
- Add clamping, per-step magnitude limits and a cooldown for automatic Supervisor updates to avoid
  oscillation. Implement simple EWMA smoothing on supervisor-driven deltas.
- Add Prometheus gauges for neuromod values and metrics for update frequency and modulation magnitude.

Medium-term (P1) — correctness & multi-tenant (3–14 days)
- Introduce a `NeuromodStore` (or extend `Neuromodulators`) that supports tenant-scoped state
  (`get_state(tenant_id)` / `set_state(tenant_id, state)`). Default to global fallback while migrating.
- Make subscriber callbacks non-blocking and per-tenant; run notifications off the request path.
- Persist neuromodulator history (append-only) for auditability and reproducibility; add migration tools
  and export utilities so neuromod traces can be analyzed offline.
- Add unit & integration tests that assert directional and bounded behavior (Supervisor never exceeds
  clamps; amygdala salience weight follows dopamine direction; thalamus attention responds to NE).

Longer-term (P2) — control & learning (2–8 weeks)
- Replace or augment heuristic Supervisor with a pluggable controller interface. Two evolution paths:
  1. PID/EWMA-based controller (low risk): better smoothing, anti-windup and baseline decay.
  2. Learned controller (higher ROI, needs data): small RL/TD/bandit agent that outputs safe bounded
     neuromodulation deltas, trained on logged KPIs using offline or safe-online methods.
- Use principled signals for urgency/uncertainty: NE driven by predictive uncertainty (e.g., ensemble
  variance), dopamine as TD reward-prediction error instead of simple proportional to pred_error.
- Provide a canary & A/B evaluation harness to validate learned controllers vs baseline heuristics.

Operational & observability items
- Metricize and dashboard: expose `somabrain_neuromod_dopamine`, `_serotonin`, `_noradrenaline`, `_acetylcholine`,
  and `somabrain_neuromod_update_total` (labels: tenant, reason/manual|supervisor).
- Add audit logs for external `POST` operations (tenant, user, old_state, new_state, timestamp, reason).
- Expose free-energy, modulation magnitude, and supervisor cooling-rate metrics for debugging and alerts.

Safety & deployment notes
- Multi-process: current in-process global state is not cluster-consistent; use a shared store (Redis/DB)
  if you need cluster-wide consistent neuromod state, or accept per-process divergence for experiments.
- Provide feature flags: default to heuristic Supervisor off for canary tenants until tested.

Acceptance criteria (for marking this task done)
1. `POST /neuromodulators` requires auth and records an audit entry; GET optionally requires auth or is hidden.
2. Supervisor.adjust uses bounded deltas and EWMA smoothing; unit tests assert no step exceeds clamps.
3. Per-tenant state API present (or clear migration path) with at least a fallback global default.
4. Metrics and dashboard exist for neuromod values and update rates; basic alert rules detect rapid changes.
5. An A/B harness exists that can compare baseline heuristics to an experimental controller and produce KPI
   comparisons (recall precision, store/admit rate, prediction error, free-energy) over a run.

Where we are now (status snapshot)
----------------------------------
- Code: `somabrain/neuromodulators.py` implements a `NeuromodState` dataclass and a `Neuromodulators` hub
  (global singleton `neuromods`) with `get_state()` and `set_state()` that notifies subscribers.
- Integration: amygdala, thalamus, prefrontal and supervisor modules read the neuromod state and use
  dopamine/serotonin/noradrenaline/acetylcholine to modulate salience, attention, decision scores and
  automated adjustments. `app.py` exposes `GET /neuromodulators` and `POST /neuromodulators` (currently
  without tenant-scoped auth) and `UnifiedBrainCore` updates dopamine/serotonin on processing success.
- Tests: there are unit tests referencing neuromodulators (e.g. `tests/test_neuromodulators.py`) and
  supervisor behavior is covered by existing tests. Full test suite status should be run after editing.
- Risks: the current implementation uses a global, process-local neuromod state (not cluster-consistent)
  and external POST can change global behavior for all tenants; this is the primary safety gap.

Next steps (recommended immediate work)
1. Implement HTTP protection and audit for `POST /neuromodulators` and add `include_in_schema=False`
   temporarily if you prefer to hide the endpoints while finishing work. (P0)
2. Add EWMA smoothing and per-step delta limits to `Supervisor.adjust` (P0).
3. Add Prometheus gauges and a simple Grafana panel for neuromod values (P1).
4. Plan a per-tenant `NeuromodStore` migration and add unit tests to lock expected behavior (P1).

If you want, I can implement the immediate changes (protect endpoints + EWMA smoothing + metrics) now,
run the test suite, and rebuild docs; tell me to proceed and I will create the code changes and report back
with results and diffs.
