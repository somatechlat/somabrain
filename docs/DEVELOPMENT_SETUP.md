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

To confirm the memory round-trip workflow without spinning up the full stack, reuse an existing
pytest scenario that exercises the agent memory module:
```bash
pytest tests/test_agent_memory_module.py::test_encode_and_recall_happy -q
```
The test clears the in-process store, encodes a memory, and asserts it can be recalled via
`somabrain.agent_memory.recall_memory`.

### Using an Existing Kubernetes Stack (Strict Workflow)
When you have a full stack running in Kubernetes, bridge the cluster back to localhost and reuse
the strict pytest scenario to validate the live services:

```bash
# Optional: clear any lingering forwards from previous sessions
pkill -f "kubectl -n somabrain-prod port-forward" || true

# 1. Forward the production API on 9696 using the helper script, then forward test/memory/redis (detach + log to /tmp)
./scripts/port_forward_api.sh
nohup kubectl -n somabrain-prod port-forward svc/somabrain-test 9797:9797   > /tmp/pf-somabrain-test.log 2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/somamemory 9595:9595       > /tmp/pf-somamemory.log     2>&1 &
nohup kubectl -n somabrain-prod port-forward svc/sb-redis 6379:6379         > /tmp/pf-redis.log          2>&1 &

# 2. Sanity-check health once the tunnels are up
curl -s http://127.0.0.1:9696/health | jq '.ok'
curl -s http://127.0.0.1:9797/health | jq '.ok'
curl -s http://127.0.0.1:9595/health | jq '.ok'

# 3. Run the strict memory integration against the forwarded endpoint
SOMA_API_URL=http://127.0.0.1:9797 .venv/bin/pytest \
  tests/test_agent_memory_module.py::test_encode_and_recall_happy -q

# 4. Stop the port-forwards when finished
pkill -f "kubectl -n somabrain-prod port-forward"
```

Successful runs report `true` from the health probes and a single `.` from pytest. Inspect the
log files in `/tmp/pf-*.log` if any command reports errors.

### Live Cognition Learning Suite
These end-to-end tests assert that the deployed stack really learns when driven through
`/context/evaluate`, `/context/feedback`, and `/remember`. They require **live services** — no mocks
or docker-compose shortcuts — and will be skipped automatically if the API, memory, or Redis health
checks fail.

1. Ensure port-forwards (or direct connections) exist for:
  - Somabrain API: `http://127.0.0.1:9797`
  - Somabrain memory service: `http://127.0.0.1:9595`
  - Redis: `redis://127.0.0.1:6379/0`
  - Postgres (forward `svc/postgres` → `55432`):
    ```bash
    nohup kubectl -n somabrain-prod port-forward svc/postgres 55432:5432 \
     > /tmp/pf-postgres.log 2>&1 &
    ```

2. Export the environment so pytest hits the live endpoints:
  ```bash
  export SOMA_API_URL=http://127.0.0.1:9797
  export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
  export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
  export SOMABRAIN_POSTGRES_LOCAL_PORT=55432
  ```

3. Run the cognition suite with verbose output:
  ```bash
  pytest -vv tests/test_cognition_learning.py
  ```

The file defines three `@pytest.mark.learning` cases that validate:
- memory recall increases the item count after `/remember`,
- `/context/feedback` persists rows to `feedback_events` & `token_usage`, and
- working-memory history grows monotonically across a session.

All three tests must pass to demonstrate the real stack is learning. Failed runs usually indicate
missing port-forwards, stale credentials, or Postgres not reachable on `55432`.

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
