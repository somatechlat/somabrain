> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Service & Capability Ownership

| Area | Asset | Description | Primary Owner | Observability | Notes |
| --- | --- | --- | --- | --- | --- |
| Public API | `/remember` (POST) | Persist episodic/semantic memories | Memory Platform | Metrics: `somabrain_memory_write_latency_seconds`; Logs tagged `endpoint=remember` | Requires Memory + Redis online |
| Public API | `/recall` (POST) | Retrieve relevant memories | Memory Platform | Metrics: `somabrain_memory_recall_latency_seconds`; Traces `operation=recall_ltm` | Regression gap: recall mismatches tracked in Sprint 1 |
| Public API | `/plan/suggest` (POST) | Generate short execution plan | Cognitive Core | Metrics: `somabrain_planner_latency_seconds` | Depends on semantic graph cache |
| Public API | `/act` (POST) | Execute cognitive action loop | Cognitive Core | Logs include `act_session_id` | Strict mode gating enforced |
| Public API | `/neuromodulators` (GET/POST) | Inspect/update neuromodulator state | Neuro Team | Metrics: `somabrain_neuromod_state_changes_total` | Guarded by admin auth |
| Public API | `/personality` (POST) | Adjust tenant personality traits | Neuro Team | Audit: `append_event` entries | Requires Constitution service if enabled |
| Public API | `/graph/links` (POST) | Link semantic graph nodes | Knowledge Graph | Metrics: `somabrain_graph_link_duration_seconds` | Updates cached HRR context |
| Public API | `/delete` (POST) | Remove stored memories | Memory Platform | Metrics: `somabrain_memory_delete_total` | Requires STRICT_REAL audit logging |
| Public API | `/recall/delete` (POST) | Remove recall cache entries | Memory Platform | Logs tagged `operation=recall_delete` | Used for GDPR erasure paths |
| Ops API | `/health` (GET) | Primary health signal | SRE | Dashboard: Grafana `SomaBrain/ServiceHealth` | Returns strict-real compliance status |
| Ops API | `/healthz` (GET) | Lightweight health probe | SRE | Alert: `healthz_probe_failed` | Not in OpenAPI schema |
| Ops API | `/micro/diag` (GET) | Microcircuit diagnostics | Cognitive Core | Logs include `micro_diag_latency_ms` | Auth required |
| Ops API | `/sleep/run` (POST) | Trigger consolidation sleep cycle | Memory Platform | Metrics: `sleep_cycle_duration_seconds` | Invokes background tasks |
| Ops API | `/sleep/status` (GET) | Sleep cycle status | Memory Platform | Gauge: `sleep_cycle_active` | Tenant scoped |
| Ops API | `/sleep/status/all` (GET) | All tenant sleep status | Memory Platform | Dashboard: SRE sleep overview | Admin only |
| Ops API | `/constitution/version` (GET) | Constitution engine status | Governance | Logs `constitution_version` | Optional module |

## Background Jobs & Scheduled Tasks

| Job | Trigger | Owner | Description | Dependencies | Runbook |
| --- | --- | --- | --- | --- | --- |
| OutboxProcessor | Startup task + interval | Cognitive Core | Flushes event outbox to Kafka/Postgres | Kafka, Postgres | ops/runbooks/Runbooks.md#outbox |
| SleepCycle | Manual `/sleep/run` or cron | Memory Platform | Runs consolidation via `Hippocampus` | Memory API, Redis | docs/TESTING_MEMORY.md |
| DriftMonitor | Interval task | Controls | Evaluates drift using `DriftMonitor` | Redis metrics samples | ops/runbooks/Compliance_and_Proofs.md |
| RealityMonitor | Interval task | Controls | Calls `assess_reality` checks | Memory + External truth sources | ops/runbooks/Compliance_and_Proofs.md |
| QuotaReset | Cron | Platform | Resets tenant quotas nightly | Redis, Config | ops/runbooks/Release_and_Health_Gating.md |

## Tenant & Data Ownership

| Domain | Data Store | Owner | Notes |
| --- | --- | --- | --- |
| Memory Payloads | Postgres (`somabrain_memory` schema) | Memory Platform | Backed by WAL archiving; snapshots in `data/postgres/` |
| Semantic Graph | Redis (`tenant:{id}:graph`) | Knowledge Graph | TTL caching w/ HRR embeddings |
| Journals | S3/MinIO (`artifacts/journal/`) | Governance | Append-only audit trail |
| Metrics | Prometheus (`data/prometheus/`) | SRE | Scraped by Grafana dashboards |
| Traces | OTLP Collector | SRE | Planned Sprint 5 deliverable |

## SLA Matrix

| Endpoint | Availability | Latency (p95) | Error Budget | Page Target |
| --- | --- | --- | --- | --- |
| `/remember` | 99.5% | 750 ms | 3.6 h/month | Memory Platform On-call |
| `/recall` | 99.5% | 500 ms | 3.6 h/month | Memory Platform On-call |
| `/plan/suggest` | 99.0% | 1.5 s | 7.2 h/month | Cognitive Core On-call |
| `/health` | 99.9% | 150 ms | 0.7 h/month | SRE Primary |

## Contact Roster

| Owner | Slack Channel | Escalation | Notes |
| --- | --- | --- | --- |
| Memory Platform | `#somabrain` | PagerDuty: `memory-primary` | Owns recall regression investigation |
| Cognitive Core | `#somabrain-core` | PagerDuty: `cortex-primary` | Maintains planner, action loop |
| Controls | `#somabrain-controls` | PagerDuty: `controls-primary` | Oversees drift/reality monitors |
| SRE | `#somabrain-sre` | PagerDuty: `sre-primary` | Manages deployments & health signals |
| Governance | `#somabrain-governance` | PagerDuty: `gov-primary` | Constitution + compliance |
