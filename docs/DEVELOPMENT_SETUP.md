# SomaBrain Development Setup

This guide provides a comprehensive, step-by-step workflow for preparing a development environment,
running the canonical stack, executing tests/benchmarks, and contributing changes.

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Use `pyenv` or system Python. |
| Docker & Docker Compose | 24.x+ | Required for canonical stack; ensure Docker Desktop resources ≥ 8GB RAM. |
| Node.js (optional) | 20.x | Needed for some tooling dashboards (future). |
| Git | latest | SSH access recommended. |
| make (optional) | — | Convenience wrapper (planned). |

Install Python dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 2. Launch the Canonical Stack

```bash
# Generates .env.local and starts all services using Docker_Canonical.yml
./scripts/dev_up.sh

# Run migrations (uses SOMABRAIN_POSTGRES_DSN or falls back to local SQLite)
alembic upgrade head

# 5. Export OpenAPI (optional)
./scripts/export_openapi.py

# Optional: wait for services to settle (Redis, Kafka, Postgres, OPA, Somabrain)
./scripts/wait_for_services.sh 120
```

Outputs:
- `.env.local` – environment variables (host port mappings, service URLs).
- `ports.json` – JSON object mapping service names to host ports (e.g. `"SOMABRAIN_HOST_PORT": 9797`).

Tear down when finished:
```bash
docker compose -f Docker_Canonical.yml down --remove-orphans
```

## 3. Configure Environment Variables

```bash
source .env.local
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595  # or actual endpoint
export SOMABRAIN_OTLP_ENDPOINT=http://localhost:4317                    # if OTEL collector running
```

Sensitive secrets should **never** be committed. For local testing, store them in `.env.secrets`
(optional) and `source` the file. In CI and production, secrets are injected via Vault or the cloud
secret manager.

## 4. Running Tests

### Unit Tests
```bash
pytest tests -k "not integration" -q
```

### Integration Tests (NO_MOCKS)
```bash
pytest -m integration -q
```
The suite reads `ports.json` to determine service endpoints.

### Benchmarks (Work in Progress)
Benchmarks live under `benchmarks/` and will be expanded in S9. Example command:
```bash
python -m benchmarks.rag_live_bench --api-url "http://127.0.0.1:$(jq -r '.SOMABRAIN_HOST_PORT' ports.json)"
```

## 5. Storage & Messaging Wiring

Once the stack is running, confirm each managed dependency responds before executing
integration tests:

### Postgres
```bash
source .env.local
psql "$SOMABRAIN_POSTGRES_DSN" -c '\dt'
alembic upgrade head  # idempotent; safe to rerun
```
The `feedback_events` and `token_usage` tables should exist after migrations. Use the
`migrations/versions/` directory as the authoritative schema source.

### Redis
```bash
redis-cli -u "$SOMABRAIN_REDIS_URL" INFO server
redis-cli -u "$SOMABRAIN_REDIS_URL" KEYS 'soma:*' | head
```
Expect keys for constitution cache (`soma:constitution*`) once the app has handled requests.

### Kafka (Redpanda in dev)
```bash
broker="${SOMABRAIN_KAFKA_URL:-kafka://localhost:9092}"
rpk topic list --brokers "${broker#kafka://}"
```
Development uses Redpanda inside the compose stack. Topics such as `soma.audit` and
`soma.telemetry` are created lazily by the application; `rpk topic create` can be used to seed
them during early development. Alternatively run `docker exec -it sb_kafka rpk topic list` if the
host does not have `rpk` installed.

### Object Storage (Optional)
Local setups can stub S3/GCS with `localstack` or `minio` if constitution snapshots need to be
tested. Configure endpoints via environment variables documented in `docs/CONFIGURATION.md`.

## 6. Linting & Formatting

```bash
ruff check somabrain tests
black somabrain tests
mypy somabrain
```
Pre-commit hooks will be added to automate these steps.

## 7. Development Workflow

1. Pull latest changes and ensure `./scripts/dev_up.sh` runs cleanly.
2. Create a feature branch; update `docs/architecture/CANONICAL_ROADMAP.md` if modifying roadmap
   items.
3. Implement changes with tests.
4. Run unit + integration tests locally.
5. Submit PR; GitHub Actions will rerun tests against the canonical stack.

## 8. Troubleshooting

| Symptom | Possible Cause | Fix |
|---------|----------------|-----|
| `docker compose` fails due to port conflict | Ports already bound by other processes | `./scripts/dev_up.sh` auto-selects ports; ensure the new `.env.local` is sourced. |
| Redis refuses connections | Container not ready or credentials invalid | Check `docker logs sb_redis`; confirm env variables sourced. |
| Kafka producer errors | Broker not yet ready | Run `./scripts/wait_for_services.sh` or inspect `docker logs sb_kafka`. |
| Tests skip unexpectedly | `-m integration` requires stack to be up | Start stack or ensure env variables set. |

## 9. Key Paths to Explore

- `somabrain/app.py` – main FastAPI bootstrap.
- `somabrain/constitution/` – constitution engine and helpers.
- `somabrain/api/` – routers, middleware, dependencies.
- `somabrain/memory_client.py` – core memory gateway.
- `somabrain/context/builder.py` & `somabrain/context/planner.py` – context bundles + reasoning loop.
- `somabrain/api/context_route.py` – `/context/evaluate` + `/context/feedback` endpoints (persist
  feedback/token usage, emit audit events).
- `somabrain/storage/feedback.py` / `somabrain/storage/token_ledger.py` – Postgres tables backing
  the adaptation loop and usage accounting.
- `alembic.ini`, `migrations/` – schema migrations (run `alembic upgrade head`).
- `docs/architecture/DETAILED_ARCHITECTURE.md` – architectural decisions.

Stay current with the roadmap; each sprint may introduce new services (e.g., vector store, token
ledger) that require additional setup steps.

## 10. CLI / SDK

- Basic client available under `clients/python/`.
- Example: `python clients/python/cli.py "Hello" --session sandbox-cli --token dev-token`.
