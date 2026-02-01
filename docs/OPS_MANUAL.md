# Retrieval Observability Runbook (Strict Real Mode)

This runbook documents the mandatory metrics, alert rules, and triage steps for the retrieval pipeline under strict production realism. No fallbacks, no silent degradation: empty results and latency surfaces must reflect actual system performance.

## Scope
Covers the unified retrieval pipeline (vector, graph, recent/WM, lexical components) and rank fusion / reranking stages. Applies to all namespaces/tenants.

## Core Metrics (Prometheus)

| Purpose | Metric | Type | Labels | Notes |
|---------|--------|------|--------|-------|
| Requests | `somabrain_retrieval_requests` | Counter | namespace,retrievers | Total retrieval pipeline invocations; retrievers label encodes active set (e.g. `vector+graph`). |
| Latency | `somabrain_retrieval_latency_seconds` | Histogram | (none) | End-to-end pipeline latency (embedding → fusion → output). |
| Candidate Count | `somabrain_retrieval_candidates_total` | Histogram | (none) | Post-dedupe + rerank final candidate size. |
| Empty Responses | `somabrain_retrieval_empty_total` | Counter | namespace,retrievers | Incremented when zero candidates returned (strict empty; no backfill). |
| Per-Retriever Hit | `somabrain_retriever_hits_total` | Counter | namespace,retriever | Non-empty candidate list per retriever adapter. |
| Fusion Applied | `somabrain_retrieval_fusion_applied_total` | Counter | method | Number of rank fusion executions (e.g. `weighted_rrf`). |
| Fusion Sources | `somabrain_retrieval_fusion_sources` | Histogram | (none) | Distribution of number of source lists fused. |

### Secondary / Stage Metrics
| Purpose | Metric | Type | Labels | Notes |
| WM Stage Latency | `somabrain_recall_wm_latency_seconds` | Histogram | cohort | Latency for working-memory stage pre-merge. |
| LTM Stage Latency | `somabrain_recall_ltm_latency_seconds` | Histogram | cohort | Latency for long-term memory stage. |
| ANN Latency | `somabrain_ann_latency_seconds` | Histogram | namespace | ANN index lookup timing. |
| Recall Requests | `somabrain_recall_requests_total` | Counter | namespace | Higher-level recall endpoint usage. |

## Alerts (`alerts.yml`)

| Alert | Condition | Window | Severity | Rationale |
|-------|-----------|--------|----------|-----------|
| RetrievalEmptyRateHigh | empty / requests > 0.30 | 5m (for 5m) | warning | Elevated empty responses; index coverage or retriever outage. |
| RetrievalLatencyP95High | p95 latency > 0.40s | 10m (for 10m) | warning | User-facing latency risk; ANN/fusion pressure or backend slowness. |
| (Indirect) PlanningLatencyP99High | planning p99 > 40ms | 10m | warning | Upstream planning pressure may cascade into retrieval demand. |

## Expected Baselines
- Empty Rate: < 10% for healthy populated memory corpus (early cold start may be higher; alert catches sustained >30%).
- p95 Latency: < 250ms typical; threshold set at 400ms leaves investigation margin.
- Fusion Sources: Usually 2–4; spikes may indicate experimental retriever activation.

## Triage Flow

1. Alert Triggered → Identify which (Empty Rate or Latency).
2. Scope: Check label namespace(s) impacted via Prometheus query.
3. Isolation Steps:
   - For Empty Rate: Query per-retriever hits
     ```promql
     sum by (retriever) (rate(somabrain_retriever_hits_total[5m]))
     ```
     If a single retriever returns zero while others have hits → retriever-specific outage (vector index rebuild, graph service connectivity, etc.).
   - For Latency: Break down ANN vs WM vs LTM stage histograms:
     ```promql
     histogram_quantile(0.95, sum(rate(somabrain_ann_latency_seconds_bucket[5m])) by (le))
     histogram_quantile(0.95, sum(rate(somabrain_recall_wm_latency_seconds_bucket[5m])) by (le))
     histogram_quantile(0.95, sum(rate(somabrain_recall_ltm_latency_seconds_bucket[5m])) by (le))
     ```
     Pinpoint dominant stage.
4. Infrastructure Readiness:
   - Run `scripts/ci_readiness.py` manually if doubtful about Kafka/Redis/Postgres/OPA.
5. ANN Issues:
   - Check rebuild counters:
     ```promql
     increase(somabrain_ann_rebuild_total[15m])
     ```
     Frequent rebuilds can stall queries.
6. Empty + Low Fusion Sources:
   - Fusion sources histogram low (1) indicates only one retriever active → verify configuration enabling vector/graph adapters.
7. Persist Session Effects:
   - Inspect `somabrain_retrieval_persist_total` counters for recent persistence status spikes (session gating).

## Common Root Causes & Signals
| Symptom | Likely Cause | Corroborating Metric |
|---------|--------------|----------------------|
| Empty rate spike & zero hits for vector | ANN index unavailable/rebuilding | `increase(somabrain_ann_rebuild_total[10m]) > 0` |
| Empty rate spike & graph hits only | Embedding provider outage | Vector retriever latency high / zero hits |
| Latency spike WM stage | Redis contention | Elevated `somabrain_recall_wm_latency_seconds` p95 only |
| Latency spike ANN only | Index memory pressure / rebuild | `somabrain_ann_latency_seconds` p95 elevated |
| Latency + Empty both elevated | Kafka publish lag causing upstream ingestion stall | External kafka lag exporter (out-of-repo) |

## Manual Queries Cheat Sheet
```promql
# Empty ratio overall (fast check)
(sum(rate(somabrain_retrieval_empty_total[5m])) / clamp_min(sum(rate(somabrain_retrieval_requests[5m])),1))

# Per namespace empty ratio
(sum by (namespace) (rate(somabrain_retrieval_empty_total[5m])) / clamp_min(sum by (namespace) (rate(somabrain_retrieval_requests[5m])),1))

# p95 retrieval latency
histogram_quantile(0.95, sum(rate(somabrain_retrieval_latency_seconds_bucket[5m])) by (le))

# Per-retriever hit rate
sum by (retriever) (rate(somabrain_retriever_hits_total[5m]))
```

## Operational Actions
| Action | Description |
|--------|-------------|
| Warm Index | Trigger controlled ANN rebuild off-peak; monitor rebuild duration histograms. |
| Increase Capacity | Scale memory/embedding workers if WM or embedding latency the bottleneck. |
| Session Persistence Audit | Review persistence outcomes in `somabrain_retrieval_persist_total`; frequent failures may impact hit composition. |
| Retriever Config Check | Confirm adapter enablement (environment flags enabling vector, graph). |
| Backpressure | If planning latency also elevated, upstream planning queue saturation may require rate control. |

## No-Fallback Enforcement
If a retriever fails internally it must yield zero candidates; pipeline still records empty metrics. DO NOT introduce synthetic or cached backfill. Empty responses are an SLO signal.

## Readiness Gating
Integration tests auto-run `scripts/ci_readiness.py`; replicate manually before deploying:
```bash
python scripts/ci_readiness.py
```
Exit code != 0 blocks deployment.

## Escalation Thresholds
| Condition | Escalate To | Notes |
|-----------|-------------|-------|
| Empty Rate >50% for 10m | On-call Engineering | Potential systemic retrieval outage. |
| Latency p95 >800ms for 5m | On-call Engineering | User SLA breach imminent. |
| ANN rebuilds >10 in 30m | Index Maintainer | Misconfiguration or thrashing. |

## Future Extensions (Out-of-Repo)
- External dashboard pack (not stored here per policy).
- Alert refinement (soft warn at 20% empty, critical at 50%).
- Cross-retriever contribution ratio (vector vs graph vs recent). 

## Verification
To verify metrics export:
1. Hit `/metrics` endpoint of the API or cognition service.
2. Confirm presence of `somabrain_retrieval_empty_total` and `somabrain_retriever_hits_total`.
3. Fire a synthetic retrieval request and watch counters increment.

## References
- Internal metrics implementation: `somabrain/metrics.py`
- Alert rules: `alerts.yml`
- Readiness script: `scripts/ci_readiness.py`

Strict realism mandates authentic failure exposure; treat empty results as truth, not a UX defect to mask.
# Learner & Planner Operational Notes

## LearnerService
- Transport: Kafka consumer on `cog.next_event`, producer on `cog.config.updates` (idempotent, acks=all).
- Validation: confidence must be numeric and in [0,1]; event_id used for idempotency; DLQ records failures.
- Metrics: `somabrain_learner_events_consumed_total`, `somabrain_learner_events_failed_total{phase}`, `somabrain_learner_events_produced_total`, `somabrain_learner_event_latency_seconds`, `somabrain_learner_lag_seconds`, `somabrain_learner_dlq_total`.
- DLQ: Kafka topic `SOMABRAIN_LEARNER_DLQ_TOPIC` if configured; otherwise file `./data/learner_dlq.jsonl` (configurable via `SOMABRAIN_LEARNER_DLQ_PATH`).
- Backpressure: retry/backoff via Kafka config; manual offset store+commit to avoid double-processing on failures.
- Ops checks: monitor lag gauge and DLQ count; ensure `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` in integration runs.

## Planner
- Stateless DFS planner with action catalog (cost-ordered) and guaranteed non-empty plan (falls back to `analyze_goal`).
- Execution hook: `Planner.execute(plan, executor)` runs steps with early stop on failure; returns result list.
- Tests: `tests/services/test_planner_costs.py`, `tests/services/test_planner_execute.py` cover ordering and stop-on-failure.
- Integration: wire executor to your action runtime and feed outcomes back into learning (future work).
# SomaBrain Deployment Checklist (Strict Mode)

- Kafka
  - Bootstrap (`SOMABRAIN_KAFKA_URL`) reachable from services
  - Topics created: `cog.state.updates`, `cog.agent.updates`, `cog.action.updates`, `cog.global.frame`, `cog.config.updates`, `cog.fusion.drift.events`, `cog.fusion.rollback.events`
  - Schema registry populated with required Avro schemas
  - Network/DNS, TLS, and ACLs configured for producers/consumers

- Redis / Postgres / OPA
  - Redis URL (`SOMABRAIN_REDIS_URL`) reachable; minimal latency and maxmemory policy set
  - Postgres reachable with migrations applied (`alembic upgrade head`)
  - OPA URL/policy configured when enabled; enforce fail-closed posture

- Environment
  - Strict mode flags set: `ENABLE_DRIFT_DETECTION`, `ENABLE_AUTO_ROLLBACK` (as desired), `SOMABRAIN_FF_COG_INTEGRATOR`
  - Disable legacy flags and fallbacks; Avro-only IO confirmed
  - Learning tenants file mounted (`config/learning.tenants.yaml`) with per-tenant `entropy_cap`
  - Drift state dir writeable (`SOMABRAIN_DRIFT_STORE`, default `./data/drift/state.json`)

- Observability
  - OpenTelemetry collector endpoint configured; API/SDK versions aligned
  - Prometheus scrape of `/metrics` endpoints enabled for services
  - Alerts: drift rate, rollback events, integrator errors, OPA veto ratio

- Health/Readiness
  - Health server enabled where supported (`HEALTH_PORT`)
  - Liveness and readiness probes configured in orchestrator (K8s)
  - Backoff/restart policy for critical services

- Security
  - Secrets injected via env or secret manager; no secrets in images
  - Network policies restrict east-west traffic; Kafka/Redis/DB only from services
  - TLS where applicable; verify certs in CI before deploy

- Testing in Env
  - Run smoke tests: produce minimal `belief_update` events and verify `global_frame` publication
  - Validate drift/rollback telemetry topics receive events under forced conditions
  - Confirm calibration service metrics and acceptance logic under sample data

- Run Commands (examples)

```sh
# Apply DB migrations
alembic upgrade head

# Start core services (compose)
docker compose -f docker-compose.yml up -d integrator calibration drift

# Verify metrics endpoints (replace host/ports accordingly)
curl -sf http://localhost:9090/metrics | head -n 20 || true

# Force a drift snapshot (if admin endpoint available)
# curl -X POST http://integrator:8080/drift/snapshot
```
## Kafka Topic Naming Policy

### Collision Warning Context
Some Kafka metrics exporters (and JMX→Prometheus transformers) sanitize topic names by replacing dots (`.`) with underscores (`_`). When a cluster contains mixed naming styles (both `cog.state.updates` and `cog_state_updates`), the sanitized metric names can collide, producing warnings like:

```
WARNING: Due to limitations in metric names, topics with a period ('.') or underscore ('_') could collide. To avoid issues it is best to use either, but not both.
```

### Policy (Enforced)
SomaBrain uses dot-delimited topic names exclusively. Underscores are not used in any Kafka topic identifiers. This ensures one unambiguous sanitized form for metrics.

Allowed pattern (examples):
- `cog.state.updates`
- `cog.global.frame`
- `cog.integrator.context.shadow`
- `soma.belief.state`

Disallowed examples (do not create):
- `cog_state_updates`
- `cog-global-frame`
- `cog_integrator_context_shadow`

### Rationale
1. Avoid exporter collisions when `.` → `_` sanitation occurs.
2. Provide hierarchical semantic grouping (prefix segments) improving operational filtering.
3. Maintain compatibility with existing documentation and automation (scripts/seed_topics.py).

### Verification
Add or maintain a test that asserts no required topic contains `_`.

### Migration Guidance (If Existing Underscore Topics Found)
1. Create new dot-form topic (e.g., `cog.state.updates`).
2. Dual-produce events to old + new for a short transition window.
3. Migrate consumers to the new topic.
4. Validate lag = 0 on old topic, then delete old topic.

### Operational Checklist
- [ ] Run `scripts/seed_topics.py` only (creates dot-form topics).
- [ ] Audit with `kafka-topics.sh --list` (no `_` present).
- [ ] Monitor exporter logs for absence of collision warnings.

### Future Enforcement
CI task can parse `scripts/seed_topics.py` and `somabrain/common/kafka.py` TOPICS mapping ensuring all names match regex: `^[a-z0-9]+(\.[a-z0-9]+)+$`.
# Backup and Restore Runbook

## Purpose
Provide step‑by‑step instructions for backing up and restoring the SomaBrain PostgreSQL database and Kafka topics in a production environment.

## Prerequisites
- Access to the Kubernetes cluster where SomaBrain is deployed.
- `kubectl` configured for the target cluster.
- `pg_dump` and `pg_restore` available locally (or use a container image with these tools).
- Access to the Kafka broker (`somabrain_kafka`) and the `kafka-topics.sh` utility.

## Backup PostgreSQL
1. Identify the PostgreSQL pod:
   ```bash
   POD=$(kubectl get pods -l app=postgres -o jsonpath="{.items[0].metadata.name}")
   ```
2. Execute a dump inside the pod and copy it locally:
   ```bash
   kubectl exec $POD -- pg_dump -U $POSTGRES_USER $POSTGRES_DB > somabrain_backup_$(date +%Y%m%d).sql
   ```
3. Store the dump in a secure location (S3, encrypted archive, etc.).

## Restore PostgreSQL
1. Ensure the target database is empty or the existing data is no longer needed.
2. Copy the backup file to the pod (or stream it directly):
   ```bash
   cat somabrain_backup_20240101.sql | kubectl exec -i $POD -- psql -U $POSTGRES_USER $POSTGRES_DB
   ```
3. Verify the restore:
   ```bash
   kubectl exec $POD -- psql -U $POSTGRES_USER -c "SELECT count(*) FROM somabrain.memory;"
   ```

## Backup Kafka Topics
1. List topics to back up:
   ```bash
   kubectl exec -it $(kubectl get pod -l app=kafka -o jsonpath="{.items[0].metadata.name}") -- kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```
2. Use `kafka-exporter` or `kafka-mirror-maker` to copy topic data to a backup cluster, or use `kafka-console-consumer` to export messages to files:
   ```bash
   kubectl exec -it $KAFKA_POD -- kafka-console-consumer.sh \
       --bootstrap-server localhost:9092 \
       --topic my_topic \
       --from-beginning > my_topic_$(date +%Y%m%d).json
   ```
3. Store the exported files securely.

## Restore Kafka Topics
1. Re‑create the topic if needed:
   ```bash
   kubectl exec -it $KAFKA_POD -- kafka-topics.sh \
       --create --topic my_topic \
       --partitions 3 --replication-factor 2 \
       --bootstrap-server localhost:9092
   ```
2. Produce the saved messages back into the topic:
   ```bash
   cat my_topic_20240101.json | \
     kubectl exec -i $KAFKA_POD -- kafka-console-producer.sh \
       --bootstrap-server localhost:9092 \
       --topic my_topic
   ```
3. Verify the message count matches the original backup.

---
*This runbook is intended for operators with cluster admin privileges. Adjust namespace selectors and resource names as appropriate for your deployment.*
# Runbook: Service Start / Stop

This runbook describes how to start and stop the SomaBrain services in both **Docker‑Compose** and **Kubernetes** environments.

## Docker‑Compose

```bash
# Start all services (detached)
docker compose -f docker-compose.yml up -d

# Stop all services and clean up volumes
docker compose -f docker-compose.yml down --volumes --remove-orphans
```

### Individual services

```bash
# Start only the API service (useful for quick iteration)
docker compose -f docker-compose.yml up -d somabrain_app

# Stop a single service
docker compose -f docker-compose.yml stop somabrain_app
```

## Kubernetes

```bash
# Install or upgrade the Helm chart (namespace "soma-prod")
helm upgrade --install soma-prod ./charts/somabrain -n soma-prod -f values-prod.yaml
```

```bash
# Scale down (stop) all pods – set replica count to 0
helm upgrade soma-prod ./charts/somabrain -n soma-prod --set replicaCount=0
```

```bash
# Delete the release (full teardown)
helm uninstall soma-prod -n soma-prod
```

---

**Verification**: After start, ensure the health endpoint responds:

```bash
curl http://$APP_HOST:$APP_PORT/health
```

---
# Playbook: Calibration Drift (Versioned Runbook)

- Symptoms: Rising `somabrain_calibration_ece`; alert `CalibrationDrift` firing; downgrade counter increments.
- Dashboards: Calibration view (ECE pre/post, temperature, samples) per domain/tenant.
- Immediate Actions:
  - Verify sample counts (>=200) and class balance; check model version changes.
  - Confirm `ENABLE_CALIBRATION=1` and service health.
  - Inspect downgrade counter and `last_good_temperature` map.
- Remediation:
  - Open recalibration window: gather fresh observations; tune `temperature_scaler.min_samples` if convergence slow.
  - If unresolved after two windows, pin temperature to `last_good_temperature` and file incident follow-up.
- Rollback:
  - Temporarily disable enforcement via feature flag; document timestamp and reason in incident log.
- References: `somabrain/services/calibration_service.py` (acceptance logic), alerts.yml (rule), metrics dashboard.
# Playbook: OPA Latency Spike

- Symptoms: Elevated `somabrain_integrator_opa_latency_seconds` histogram; alert (to add) or degraded frame publish latency; rising veto ratio.
- Checks:
  - Network path to OPA; recent policy changes.
  - OPA server saturation metrics (external exporter).
- Actions:
  - Raise OPA timeout threshold only if minimal; otherwise fallback to permissive mode (fail-open) temporarily.
  - Cache last allow decision per tenant for short window.
- Rollback: temporarily disable OPA gate only via controlled configuration change (no env flag). Prefer fixing the OPA dependency.
- Reference: `integrator_hub.py` `_opa_decide`.
# Playbook: Consistency Degradation (κ) — Versioned Runbook

- Symptoms: Alert `ConsistencyKappaLow` (<0.2 over 10m); downstream policy inconsistency.
- Dashboards: Integrator κ gauges/histograms; posterior distributions for agent/action.
- Checks:
  - Validate predictor outputs and recent deployments.
  - Review `somabrain_integrator_candidate_weight` spread and alpha error trend.
- Actions:
  - Increase exploration (tau) via `config_update` for affected tenants.
  - If normalization correlates with instability, disable `ENABLE_FUSION_NORMALIZATION` and note the override.
- Rollback: Revert to softmax-only fusion; clamp α within safe bounds.
- References: `somabrain/services/integrator_hub.py` (`_compute_kappa`), `alerts.yml`.
# Playbook: Segmentation Flood / Drought

## Flood
- Symptoms: Alert `SegmentationFlood`; >8 boundaries /5m; F1 may drop; false boundary rate may rise.
- Checks:
  - Evaluate HMM/CPD mode configuration (lambda, z_threshold).
  - Confirm input belief update rates not spiking.
  - Inspect `somabrain_seg_p_volatile` histogram for sustained high volatility.
- Actions:
  - Temporarily increase `SOMABRAIN_CPD_MIN_SAMPLES` or raise `SOMABRAIN_CPD_Z`.
  - For HMM: reduce `SOMABRAIN_HAZARD_LAMBDA`.
- Rollback: disable advanced segmentation (`ENABLE_HMM_SEGMENTATION=0`).

## Drought
- Symptoms: Alert `SegmentationDrought`; zero boundaries 30m.
- Checks:
  - Verify segmentation service process health and Kafka consumption.
  - Check leader domain variation (entropy gauge) to ensure upstream changes occur.
- Actions:
  - Lower dwell threshold (`SOMABRAIN_SEGMENT_MAX_DWELL_MS`).
  - Re-enable CPD/HMM mode if disabled.
- Rollback: fallback to leader-mode segmentation.

References: `segmentation_service.py`, evaluator metrics `somabrain_segmentation_*`.
# Outbox Backlog & Memory Circuit Playbook

## Detection

- `OutboxPendingHigh` (warning) – `memory_outbox_pending > 50` for 10m per tenant.
- `OutboxPendingCritical` (critical) – `memory_outbox_pending > 100` for 5m per tenant.
- `MemoryCircuitStuckOpen` / `MemoryCircuitCritical` – circuit breaker open ≥90%/99% over 5m/2m.
- Telemetry: `memory_outbox_replay_total`, `memory_outbox_failed_seen_total`.

## Immediate Actions

1. Confirm which tenant(s) are impacted from the alert labels (`tenant_id`).
2. Use the CLI helper to inspect queues:
   ```bash
   scripts/outbox_admin.py --token $SOMABRAIN_API_TOKEN list --tenant TENANT --status pending
   scripts/outbox_admin.py tail --tenant TENANT --status failed
   scripts/outbox_admin.py check --max-pending 100
   ```
3. If specific events are stuck, replay them:
   ```bash
   scripts/outbox_admin.py replay EVENT_ID1 EVENT_ID2 ...
   ```
4. Check downstream systems (Kafka/Memory HTTP) for errors. A circuit breaker alert usually means the memory service is failing – inspect `somabrain_app` logs and the `/health` endpoint of the external memory runtime.

## Remediation

- **Backlog caused by downstream failure:** keep the circuit breaker open (do not manually reset) until the memory service is healthy. Once healthy, replay failed events and monitor `memory_outbox_pending` trend.
- **Tenant-specific surge:** consider temporarily disabling the feature flag/canary causing the surge (`scripts/outbox_admin.py check` followed by `/admin/features`).
- **Persistent failed events:** use `/admin/outbox` or the CLI to inspect payloads for malformed data; fix upstream writers before replaying.

## Verification

- Confirm `memory_outbox_pending{tenant_id="..."}` trending to zero.
- Circuit gauges (`memory_circuit_state`) should return to 0 within a few minutes.
- `scripts/outbox_admin.py check` should exit 0.

## Escalation

- On `OutboxPendingCritical` or `MemoryCircuitCritical`, page the on-call for the external memory service and the owning tenant team.
- Attach CLI output and relevant logs to the incident ticket for postmortem.
# SomaBrain Degradation Mode

**Version:** 1.0  
**Date:** December 9, 2025  
**Classification:** Operational Documentation

---

## 1. Overview

SomaBrain implements a sophisticated degradation mode that ensures system resilience when the external memory service (port 9595) becomes unavailable. This document describes the degradation architecture, behavior, and recovery mechanisms.

### 1.1 Design Principles

Per VIBE Coding Rules, the degradation system:
- Uses REAL infrastructure (no mocks or stubs)
- Provides explicit error messages with context
- Maintains data integrity through journaling
- Supports automatic recovery when services restore

---

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SomaBrain Application                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │MemoryService │───▶│CircuitBreaker│───▶│ LocalJournal │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                    │              │
│         ▼                   ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │MemoryClient  │    │  CB State    │    │ Journal Files│      │
│  │  (HTTP)      │    │  (per-tenant)│    │ (JSONL)      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
├─────────────────────────────────────────────────────────────────┤
│                    External Memory Service                       │
│                    (http://localhost:9595)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `MemoryService` | `somabrain/services/memory_service.py` | High-level memory facade with degradation logic |
| `CircuitBreaker` | `somabrain/infrastructure/circuit_breaker.py` | Per-tenant failure detection and recovery |
| `LocalJournal` | `somabrain/journal/local_journal.py` | Durable event storage for degraded writes |
| `MemoryClient` | `somabrain/memory_client.py` | HTTP transport to external memory service |

---

## 3. Circuit Breaker

### 3.1 Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Failure Threshold | `SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD` | 3 | Consecutive failures before circuit opens |
| Reset Interval | `SOMABRAIN_CIRCUIT_RESET_INTERVAL` | 60.0s | Time before attempting circuit reset |
| Cooldown Interval | `SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL` | 0.0s | Extra wait after reset attempt |

### 3.2 State Machine

```
                    ┌─────────────┐
                    │   CLOSED    │◀──────────────────┐
                    │  (healthy)  │                   │
                    └──────┬──────┘                   │
                           │                         │
              failure_count >= threshold             │
                           │                         │
                           ▼                         │
                    ┌─────────────┐          health check
                    │    OPEN     │          succeeds
                    │ (degraded)  │                   │
                    └──────┬──────┘                   │
                           │                         │
              reset_interval elapsed                 │
                           │                         │
                           ▼                         │
                    ┌─────────────┐                  │
                    │ HALF-OPEN   │──────────────────┘
                    │  (testing)  │
                    └─────────────┘
```

### 3.3 Per-Tenant Isolation

Each tenant has independent circuit breaker state:
- Failure counts are tracked per tenant
- One tenant's failures don't affect others
- Recovery is also per-tenant

---

## 4. Degradation Behavior

### 4.1 Write Operations (remember)

When the circuit is OPEN:

1. **Queue to Journal**: Write is persisted to local journal
2. **Return Error**: `RuntimeError("Memory service unavailable (circuit open); queued locally for replay")`
3. **Metric Update**: `CIRCUIT_BREAKER_STATE` gauge set to 1

```python
# From somabrain/services/memory_service.py
def remember(self, key: str, payload: dict, universe: str | None = None):
    if self._is_circuit_open():
        self._queue_degraded("remember", {"key": key, "payload": payload})
        message = "Memory service unavailable (circuit open)"
        if self._degrade_readonly:
            raise RuntimeError(message)
        raise RuntimeError(f"{message}; queued locally for replay")
```

### 4.2 Read Operations (recall)

When the circuit is OPEN:

1. **Fallback to WM**: Retrieval switches to Working Memory only
2. **Mark Degraded**: Response includes `degraded: true`
3. **No External Calls**: Memory service is not contacted

```python
# From somabrain/api/memory_api.py
if circuit_open:
    degraded = True
    ret_req.retrievers = ["wm"]
    ret_req.persist = False
    ret_req.layer = "wm"
```

### 4.3 Configuration Flags

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Degrade Queue | `SOMABRAIN_MEMORY_DEGRADE_QUEUE` | true | Queue writes when degraded |
| Degrade Readonly | `SOMABRAIN_MEMORY_DEGRADE_READONLY` | false | If true, reject writes entirely |
| Degrade Topic | `SOMABRAIN_MEMORY_DEGRADE_TOPIC` | `memory.degraded` | Kafka topic for degraded events |

---

## 5. Local Journal

### 5.1 Purpose

The local journal provides durable storage for memory writes that cannot be sent to the external service. Events are persisted to disk and can be replayed when the service recovers.

### 5.2 Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Journal Directory | `SOMABRAIN_JOURNAL_DIR` | `/tmp/somabrain_journal` | Storage location |
| Max File Size | `SOMABRAIN_JOURNAL_MAX_FILE_SIZE` | 100MB | Rotation threshold |
| Max Files | `SOMABRAIN_JOURNAL_MAX_FILES` | 10 | Maximum journal files |
| Retention Days | `SOMABRAIN_JOURNAL_RETENTION_DAYS` | 7 | Cleanup threshold |
| Sync Writes | `SOMABRAIN_JOURNAL_SYNC_WRITES` | true | fsync for durability |

### 5.3 Event Format

```json
{
  "id": "uuid-v4",
  "topic": "memory.degraded",
  "payload": {
    "action": "remember",
    "payload": {
      "key": "memory-key",
      "payload": { "text": "...", "metadata": {...} }
    }
  },
  "tenant_id": "tenant-123",
  "timestamp": "2025-12-09T12:00:00.000000",
  "status": "pending",
  "retries": 0
}
```

### 5.4 File Structure

```
/tmp/somabrain_journal/
├── journal_2025-12-09_12-00-00.json
├── journal_2025-12-09_13-00-00.json
└── journal_2025-12-09_14-00-00.json
```

---

## 6. Recovery

### 6.1 Automatic Recovery

The circuit breaker automatically attempts recovery:

1. **Wait for Reset Interval**: Default 60 seconds after last failure
2. **Health Check**: Probe the memory service `/health` endpoint
3. **Record Success**: If healthy, close the circuit
4. **Resume Normal Operation**: Subsequent requests go to memory service

```python
# From somabrain/services/memory_service.py
def _reset_circuit_if_needed(self) -> bool:
    if not self._is_circuit_open():
        return False
    if not breaker.should_attempt_reset(tenant):
        return False
    if self._health_check():
        breaker.record_success(tenant)
        return True
    return False
```

### 6.2 Manual Recovery

To manually reset a tenant's circuit:

```python
from somabrain.services.memory_service import MemoryService
MemoryService.reset_circuit_for_tenant("tenant-123")
```

### 6.3 Journal Replay

Pending journal events should be replayed after recovery:

```python
from somabrain.journal import get_journal

journal = get_journal()
pending = journal.read_events(status="pending")
for event in pending:
    # Replay to memory service
    # Mark as sent on success
    journal.mark_events_sent([event.id])
```

---

## 7. Observability

### 7.1 Health Endpoint

The `/health` endpoint exposes degradation state:

```json
{
  "ok": true,
  "memory_ok": true,
  "memory_circuit_open": false,
  "memory_degraded": false,
  "memory_should_reset": false,
  "components": {
    "memory": {
      "kv_store": true,
      "vector_store": true,
      "graph_store": true,
      "healthy": true
    },
    "memory_circuit_open": false,
    "outbox": {
      "pending": 0,
      "last_pending_created_at": null
    }
  }
}
```

### 7.2 Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `somabrain_circuit_breaker_state` | Gauge | 1 if open, 0 if closed |
| `somabrain_memory_degraded_writes_total` | Counter | Total degraded write events |
| `somabrain_journal_pending_events` | Gauge | Pending journal events |

### 7.3 Recall Response

Recall responses include degradation flag:

```json
{
  "results": [...],
  "degraded": true
}
```

---

## 8. Troubleshooting

### 8.1 Circuit Stuck Open

**Symptoms**: Memory operations fail even after service recovery

**Resolution**:
1. Check memory service health: `curl http://localhost:9595/health`
2. Verify network connectivity from container
3. Manually reset circuit if needed

### 8.2 Journal Growing

**Symptoms**: Journal files accumulating

**Resolution**:
1. Check memory service availability
2. Replay pending events
3. Verify retention policy is running

### 8.3 Data Loss Concerns

**Prevention**:
- Journal uses fsync for durability
- Events are not deleted until marked sent
- 7-day retention provides recovery window

---

## 9. Best Practices

1. **Monitor Circuit State**: Alert on `somabrain_circuit_breaker_state == 1`
2. **Set Appropriate Thresholds**: Balance between sensitivity and stability
3. **Implement Replay**: Ensure journal events are replayed after recovery
4. **Test Degradation**: Regularly test by stopping memory service
5. **Size Journal Storage**: Ensure sufficient disk for retention period

---

## 10. Related Documentation

- [Memory Management](../memory_management.md)
- [Production Deployment](../production_deployment.md)
- [Runtime Configuration](./runtime-config.md)
- [Strict Mode](./strict-mode.md)
# Runtime Configuration

The `somabrain.runtime_config` module is the single source of truth for runtime tunables. Values are loaded from built‑in defaults and may be overridden in local development via `data/runtime_overrides.json` when running in `full-local` mode. In production modes overrides are ignored.

## Access Helpers

Use the helper functions:
- `runtime_config.get(key, default)` generic fetch
- `runtime_config.get_bool(key, default)` boolean conversion (`1/true/yes/on`)
- `runtime_config.get_float(key, default)` float conversion
- `runtime_config.get_str(key, default)` string conversion
- `runtime_config.set_overrides(dict)` (dev only) persist overrides to `data/runtime_overrides.json`

## Override File (Dev Only)
Create or modify `data/runtime_overrides.json` to adjust values during local iteration:
```json
{
  "integrator_alpha": 1.5,
  "fusion_normalization_enabled": true,
  "learner_emit_period_s": 10.0
}
```
These overrides are only applied when mode name is `full-local`.

## Key Categories

### Cognition / Integrator
- `integrator_alpha`, `integrator_alpha_min`, `integrator_alpha_max`, `integrator_target_regret`, `integrator_alpha_eta`
- `fusion_normalization_enabled`, `drift_detection_enabled`, `integrator_enforce_conf`

### Predictor Scheduling / Models
- `state_update_period`, `agent_update_period`, `action_update_period`
- `state_model_ver`, `agent_model_ver`, `action_model_ver`

### Learning / Exploration
- `learner_ema_alpha`, `learner_emit_period_s`, `learner_beta_ema_alpha`
- `learner_tau_min`, `learner_tau_max`, `learner_default_lr`, `learner_keepalive_tau`
- `tau_decay_enabled`, `tau_decay_rate`
- `tau_anneal_mode`, `tau_anneal_rate`, `tau_anneal_step_interval` (anneal supersedes decay when active)
- `entropy_cap_enabled`, `entropy_cap`
- `learning_state_persistence` (persist adaptation state to Redis)
- `learning_rate_dynamic` (neuromodulator/dopamine influenced effective LR)

### Memory
- `memory_enable_weighting`, `memory_phase_priors`, `memory_quality_exp`, `memory_fast_ack`

### Feature Flags (Centralized)
- `cog_composite` (composite cognition frame)
- `soma_compat` (compatibility mode)
- `feature_next_event` (subscribe to next events)
- `feature_config_updates` (subscribe to global frame for config context)
- `learning_state_persistence`, `learning_rate_dynamic`

### Serialization / Test Flexibility
- `learner_strict_avro` (if false, learner service will accept JSON fallback for reward/next events when Avro is unavailable — config updates remain Avro only)
- `learner_allow_json_input` (reserved for future expanded JSON input validation)

## Rationale
Centralizing tunables avoids divergent environment variables and ensures consistent behavior across services (predictors, integrator, learner, memory). Defaults are production‑like; local development can iterate quickly via overrides without editing code or compose files.

## Adding New Tunables
1. Add a sensible default to `_defaults_for_mode` in `runtime_config.py`.
2. Consume via `runtime_config.get_*` in the service/module.
3. (Optional) Document the new key here.
4. For dev experimentation, adjust `data/runtime_overrides.json`.

## Anti‑Patterns Avoided
- No ad‑hoc `os.getenv` calls for tunables in service code (except for true infrastructure endpoints or secrets).
- No multiple sources (YAML + env + code constants) — single merged dict.
- No mode‑specific logic scattered across services.

## Example Usage
```python
from somabrain import runtime_config as rc
alpha = rc.get_float("integrator_alpha", 2.0)
if rc.get_bool("fusion_normalization_enabled"):
  apply_normalization(frame)
anneal_mode = rc.get_str("tau_anneal_mode")
if anneal_mode:
  schedule_tau_anneal(rc.get_float("tau_anneal_rate", 0.05))
```

## Testing Overrides
In tests you can temporarily set overrides:
```python
from somabrain import runtime_config as rc
rc.set_overrides({
  "learner_emit_period_s": 5.0,
  "learner_tau_min": 0.2,
  "tau_anneal_mode": "exp",
  "tau_anneal_rate": 0.05,
  "learning_state_persistence": True
})
```
Ensure tests clean up if they rely on specific values.

---
This file documents the central runtime configuration system to maintain a stable, production‑aligned default while enabling fast local iteration. In `full-local` you can safely turn on all advanced learning features (entropy capping, anneal schedules, dynamic learning rate, persistence) for end‑to‑end validation.
# Strict Mode Posture (Avro-only, Fail-fast)

- Avro-only: All Kafka topics must serialize with Avro; JSON fallbacks removed.
- Fail-fast producers: When a feature is enabled, Kafka producer initialization must succeed, otherwise the service raises at startup.
- Invariants: CI scans enforce no legacy kafka-python, no JSON fallback code paths, and no soft-disable environment gates.
- Persistence scope: Calibration persists temperatures + sample counts; drift persists only telemetry (events). Statefulness beyond that must be explicit.
- Observability: Metrics for entropy, regret, alpha, tau, ECE/Brier, improvement ratio; OTel tracing aligned and enabled.
- Policy: OPA fail-closed; frames may be dropped on explicit policy denial.
# Rollback Guide

This guide describes how to quickly roll back the cognitive-thread + learning layer using Helm values without changing images.

## Fast Disable (Flags Only)

- Set `featureFlags.enableCogThreads: false`
- Set `learnerEnabled: false`
- Optionally set `enableShadowTraffic: false`

Then apply:

```yaml
featureFlags:
  enableCogThreads: false
learnerEnabled: false
enableShadowTraffic: false
```

Apply with Helm:

```sh
helm upgrade somabrain charts/somabrain -n somabrain-prod -f values.yaml -f values-rollback.yaml
```

Effect:
- Predictors, segmentation, integrator, and orchestrator do not run gated paths.
- `learner_online` does not consume/publish config updates.
- Shadow duplication disabled.

## Full Rollback (Pinned Values + Image)

If you need to revert to a previous image and flags:

```yaml
image:
  repository: somabrain
  tag: <previous-tag>
  pullPolicy: IfNotPresent
featureFlags:
  enableCogThreads: false
learnerEnabled: false
```

Apply:

```sh
helm upgrade somabrain charts/somabrain -n somabrain-prod -f values.yaml -f values-rollback.yaml
```

## Verification

- Confirm HTTP health and metrics:
  - `GET /health` on API/pods returns 200
  - `GET /metrics` shows no `somabrain_integrator_*` increments
- Kafka activity
  - Topics `cog.global.frame`, `cog.config.updates` remain idle
- OPA
  - `somabrain_integrator_opa_veto_ratio` remains constant or absent

## Roll Forward

To re-enable learning gradually:

```yaml
featureFlags:
  enableCogThreads: true
learnerEnabled: true
shadowRatio: 0.02   # 2% shadow
```

Monitor KPIs:
- `somabrain_planning_latency_p99 <= 0.022` (22ms)
- `somabrain_integrator_opa_veto_ratio <= 0.05`
- `somabrain_learning_regret_ewma <= 0.05`

If thresholds exceed for a sustained window, revert flags above.
