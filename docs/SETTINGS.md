# SomaBrain Settings & Runtime Tunables

This document maps configuration knobs to their corresponding code paths and recommended values for
different environments (development, staging, production).

## 1. Core Settings (Config Dataclasses)

`somabrain/config.py` defines the primary runtime dataclass `Config`. Even though a more structured
config system will be introduced in later sprints, the following fields are already available:

| Setting | Description | Default (dev) | Recommended Production |
|---------|-------------|----------------|-------------------------|
| `namespace` | Default namespace for memory operations. | `somabrain_ns` | Unique per tenant (e.g. `tenant_a`) |
| `http.endpoint` | Memory service endpoint (HTTP). | `http://localhost:9595` | Managed memory service URL |
| `outbox_path` | Local outbox file path (legacy). | `./data/somabrain/outbox.jsonl` | **Disable** (use Redis/Kafka) |
| `redis_url` | Redis connection string. | `redis://localhost:6379/0` | Managed Redis cluster URL |
| `rate_rps` | Default rate limit per second. | `50` | Derived from tenant contract |
| `write_daily_limit` | Daily write cap. | `10000` | Derived from tenant contract |
| `predictor_provider` | Predictor implementation (`stub|mahal|slow|llm`). | `stub` | `llm` with caching |
| `embed_provider` | Embedding backend. | `"tiny"` | Model-specific identifier |

Future sprints (S3, S4) will replace local fields such as `outbox_path` with cloud alternatives and
introduce additional sections for vector index tuning and pipeline concurrency limits.

## 2. Environment-Specific Profiles

### Development
- Use `./scripts/dev_up.sh` to generate `.env.local` with sane defaults.
- `SOMABRAIN_ENABLE_TRACING=0`, `SOMABRAIN_ENABLE_REWARD_GATE=0`.
- Local Postgres and Redis containers with non-persistent volumes.

### Staging
- Connect to staging Redis/Postgres clusters.
- `SOMABRAIN_ENABLE_TRACING=1` with OTLP collector pointing to staging observability stack.
- Lower rate limits to prevent unexpected load (e.g. 10 req/sec per tenant) while still testing
  concurrency.
- Coordinate with agent teams so their staging SLM endpoints point at the staging SomaBrain API.

### Production
- All secrets managed via Vault.
- Rate limits loaded from tenant config service.
- Reward gate enabled; constitution enforcement fail-closed.
- Kafka cluster endpoints pointed to HA brokers with TLS/SASL.
- Benchmarks executed before each release to ensure SLO compliance.

## 3. Mathematical Parameters

The constitution stores parameters for utility calculation (`λ`, `μ`, `ν`) and reward policies. Keep
these under version control in the constitution JSON and document changes in the constitution
release notes. Future math modules (S8) will read additional parameters:
- `geodesic_metric`: toggles geodesic vs. Euclidean similarity.
- `embedding_decay`: controls memory aging.
- `reward_window`: number of audit-confirmed decisions considered for reward computation.

## 4. Observability Settings

- `SOMABRAIN_OTLP_ENDPOINT` – required for traces/metrics/export.
- `SOMABRAIN_LOG_LEVEL` (planned) – exposes log verbosity (default `INFO`).
- Alert thresholds defined in `ops/alerts/` (to be added). Configure Alertmanager to page on:
  - `somabrain_audit_fallback_total` spikes.
  - `somabrain_constitution_verified` dropping to 0.
  - Agent-reported SLM latency (captured via feedback) breaching SLO targets.

## 5. Testing & Benchmark Settings

- Integration tests read `.env.test` or `ports.json` for endpoints.
- Benchmarks use configuration files under `benchmarks/config/` specifying concurrency, payload
  size, and model selection.
- Chaos tests (S9) will reference YAML manifests describing failure scenarios and durations.

Keep this document synchronized with the codebase; each new configuration flag or setting must be
added with environment defaults and production guidance.
