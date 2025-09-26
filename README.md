# SomaBrain

SomaBrain is a governed cognitive core that intermediates between external SLM-enabled agents and
defence-in-depth infrastructure. Requests from agents are authenticated, evaluated against a
cryptographically signed constitution, enriched with persistent memory, orchestrated for
agent-side SLM execution, and audited end to end. The system is engineered to sustain millions of
transactions per day while guaranteeing safety, observability, and recoverability.

## Highlights

- **Constitutional governance** – Redis + Postgres backed constitution store with threshold
  signatures, version history, and immutable cloud snapshots.
- **Transactional audit trail** – Kafka/KRaft backbone with schema enforcement, idempotent
  producers, and replay tooling; every decision is attributable and immutable.
- **Multi-tier memory fabric** – Redis hot cache, vector store (Qdrant/PGVector), and Postgres
  relational graph with integrity workers and mathematical consistency checks.
- **LLM/SLM abstraction layer** – SomaBrain synthesises attention-like context bundles, planner
  recommendations, and governance directives that agents feed into their own SLM stacks. No SLM
  inference runs inside the brain; it strictly prepares and governs inputs for external models.
- **Agent orchestration** – Evaluate/Feedback RPCs (`/context/evaluate`, `/context/feedback`) deliver
  curated context bundles, capture feedback, audit events, and persist usage metrics so agent-side
  SLM calls stay safe, efficient, and fully audited.
- **Managed-only persistence** – no file-based state in runtime paths; all durable data flows
  through managed services (Kafka, Redis, Postgres, object storage).
- **Secure ingress** – configurable bearer/JWT auth, rate limiting, and tenant allowlists for Evaluate/Feedback APIs.
- **First-class observability** – OpenTelemetry traces, Prometheus metrics, structured logs, and
  Grafana dashboards with anomaly detection.

## Repository Layout

```
README.md                         – project overview & quick start
Dockerfile                        – multi-stage build for the SomaBrain API + workers
Docker_Canonical.yml              – canonical compose stack for local/stage environments
scripts/                          – tooling (dev_up, replay, Kafka smoke, etc.)
somabrain/                        – application modules (API, constitution, memory, metrics, learning)
brain/                            – legacy adapters and scaffolding kept for backwards-compat agent tests
benchmarks/                       – load/latency benchmarks (to be expanded in S9)
clients/                          – SDKs and CLIs for agent integrations
proto/                            – protobuf definitions for context/agent contracts
ops/                              – observability dashboards, alert rules (populated in S6)
docs/                             – canonical roadmap, architecture reference, configuration
```

See `docs/architecture/DETAILED_ARCHITECTURE.md` for a deep dive into component design and
`docs/CONFIGURATION.md` / `docs/SETTINGS.md` for environment variables and runtime tuning knobs.

## Quick Start

```bash
# 1. Prepare environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Launch canonical stack (auto-selects free ports and writes ports.json)
./scripts/dev_up.sh

# 3. Run integration tests (NO_MOCKS)
pytest -m integration -q

# 4. Tail metrics / logs
open http://localhost:$(jq -r '.SOMABRAIN_HOST_PORT' ports.json)/metrics

# (Optional) run schema migrations for Postgres-backed stores
alembic upgrade head

# 5. Export OpenAPI (optional)
./scripts/export_openapi.py
```

The canonical stack automatically detects occupied host ports and allocates alternatives; the
POC `ports.json` file records the assignments so CLI tooling and tests can hydrate the correct
endpoints.

## Contributing

1. Each sprint deliverable is tracked in `docs/architecture/CANONICAL_ROADMAP.md`.
2. Infrastructure changes must ship via Terraform/Helm manifests under code review.
3. All code paths require tests (unit + integration). Benchmarks in `benchmarks/` are executed
   before release and must meet the published SLOs.
4. Follow the coding standards documented in `docs/DEVELOPMENT_SETUP.md` (formatter, lints, hooks).

## Roadmap & Status

The fine-grained roadmap lives in `docs/architecture/CANONICAL_ROADMAP.md`. Status updates happen at
the end of every sprint (two-week cadence) along with release notes and exemplar metrics.

## CLI Example

```bash
cd clients/python
python cli.py "Hello Soma" --session sandbox-cli
```
