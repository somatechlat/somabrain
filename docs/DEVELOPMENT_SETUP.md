# SomaBrain Development Setup

This guide provides a comprehensive, step-by-step workflow for preparing a development environment,
running the canonical stack, executing tests/benchmarks, and contributing changes.

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13 (matches CI workflow) | Install via `pyenv`, `asdf`, or system package. |
| [uv](https://github.com/astral-sh/uv) | 0.8+ | Fast Python installer/runner used everywhere in this project. |
| Docker & Docker Compose | 24.x+ | Required for the canonical stack; allocate ≥ 8 GB RAM and 4 CPUs. |
| Node.js (optional) | 20.x | Needed only for forthcoming dashboards. |
| Git | latest | SSH access recommended. |

Set up the Python environment using `uv` (mirrors CI):
```bash
# Install uv once (pipx recommended)
pipx install uv  # or: pip install --user uv

# Create and activate the project virtual environment
uv venv --python 3.13
source .venv/bin/activate

# Install the package in editable mode with dev extras
uv pip install --editable .[dev]

# Tooling examples (works even without activating the venv)
uv run ruff check .
uv run pytest -q
```

> ❗ **Virtualenv warning tip:** If you see `VIRTUAL_ENV=venv does not match .venv`, the shell is pointing at a different environment. Either `source .venv/bin/activate` again or run commands with `uv run --active ...` to target the correct env automatically.

### 1.1 `uv.lock` maintenance

- Keep `uv.lock` **checked into git** so local installs, CI runs, and production deploys resolve identical dependency versions.
- When you change dependencies (edit `pyproject.toml` or bump extras), regenerate the lock with:
  ```bash
  uv pip compile pyproject.toml --extra dev --lockfile uv.lock
  ```
  or simply rerun `uv pip install -e .[dev]` and commit the updated lock that `uv` produces.
- If you intentionally discard the lock file (e.g., to test fresh resolution), delete it and rerun the install command; the new file should be committed with the change.

## 2. Launch the Canonical Stack

Follow this checklist every time you need the full development cluster:

1. **Start (or restart) everything**
  ```bash
  ./scripts/dev_up.sh
  ```
  The script removes any stale containers, rebuilds the Somabrain image, and starts Redis, Kafka, Postgres, Prometheus, Somabrain, the external memory service, and the OPA stub. It emits:
  - `.env.local` – environment variables with host port mappings.
  - `ports.json` – the same information in JSON for tooling/tests.

2. **Confirm the API is ready** (already checked by the script, but always good to spot-check):
  ```bash
  curl -fsS http://localhost:9696/health | jq
  ```

3. **Apply database migrations** (idempotent):
  ```bash
  uv run alembic upgrade head
  ```

4. **Full-stack smoke verification** – run these commands in order to ensure every dependency is reachable:
  ```bash
  # Memory service
  curl -fsS http://localhost:9595/health

  # OPA stub & Prometheus metrics
  curl -fsS http://localhost:8181/health
  curl -fsS http://localhost:9090/metrics | head -n 5

  # Redis
  MSG="smoke-$(date +%s)"
  redis-cli -u redis://localhost:6379 SET smoke_test_key "$MSG"
  redis-cli -u redis://localhost:6379 GET smoke_test_key

  # Postgres
  docker exec -i sb_postgres psql -U soma -d somabrain -c "SELECT 'feedback_events' AS tbl, COUNT(*) FROM feedback_events;"
  docker exec -i sb_postgres psql -U soma -d somabrain -c "SELECT 'token_usage' AS tbl, COUNT(*) FROM token_usage;"

  # Kafka (create topic once; subsequent runs reuse it)
  docker exec sb_kafka kafka-topics.sh --create --topic test-smoke --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 || true
  SMOKE_MSG="smoke-$(uuidgen)"
  printf '%s\n' "$SMOKE_MSG" | docker exec -i sb_kafka kafka-console-producer.sh --bootstrap-server localhost:9092 --topic test-smoke >/dev/null
  docker exec sb_kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-smoke --from-beginning --max-messages 1 --timeout-ms 10000

  # End-to-end remember/recall sanity check
  curl -fsS -X POST http://localhost:9696/remember -H 'Content-Type: application/json' \
    -d '{"coord_key":"smoke:integration","payload":{"content":"integration smoke memory","phase":"bootstrap","quality_score":0.95}}'
  curl -fsS -X POST http://localhost:9696/recall -H 'Content-Type: application/json' -d '{"query":"integration","top_k":3}' | jq '.wm'
  ```

  All commands should return successfully; the recall output must include the newly stored memory in both the `wm` and `memory` arrays.

5. **Quick combined smoke** – the helper script condenses the above checks and is ideal after every restart:
  ```bash
  bash scripts/smoke_test.sh
  ```

6. **Optional artifacts** – the stack automatically writes health snapshots to `artifacts/run/` (see `scripts/dev_up.sh`).

7. **Shutdown** when you are done:
  ```bash
  docker compose -f Docker_Canonical.yml down --remove-orphans
  ```

### 2.1 Posture knobs for local vs. production parity

- **Single worker with read-your-writes:** the compose profile sets `SOMABRAIN_WORKERS=1` so `/remember` writes are visible immediately to `/recall`.
- **Force full-stack readiness:** `SOMABRAIN_FORCE_FULL_STACK=1` (now written to `.env.local` by `scripts/dev_up.sh`) requires a real predictor, embedder, and reachable memory service. Disabling it relaxes readiness for isolated development.
- **OPA fail-closed simulation:** set `SOMA_OPA_FAIL_CLOSED=1` to make `/health` depend on the OPA stub (`opa_required=true`).
- **devprod smoke script:** `python scripts/devprod_smoke.py --url http://127.0.0.1:9696` runs the same remember/recall loop with additional assertions if you prefer a Python-based check.

### 2.2 Rebuild image & redeploy the full stack

Whenever you change application code or dependencies, rebuild the image and restart the entire developer stack before testing:

1. Stop any previous run:
  ```bash
  docker compose -f Docker_Canonical.yml down --remove-orphans
  ```
2. Rebuild and relaunch everything (image build is automatic):
  ```bash
  ./scripts/dev_up.sh --rebuild
  ```
  The `--rebuild` flag forces a clean Docker image rebuild before containers start. If omitted, the script still detects most changes, but using the flag guarantees a fresh image.
  
  By default, `scripts/dev_up.sh` writes production-like flags into `.env.local` so every run uses a strict, full-stack posture:
  - `SOMABRAIN_FORCE_FULL_STACK=1`
  - `SOMABRAIN_STRICT_REAL=1`
  - `SOMABRAIN_REQUIRE_MEMORY=1`
  - `SOMABRAIN_MODE=enterprise`

  To temporarily relax this (e.g., offline dev), comment out or override these envs before running `docker compose`.

### 2.3 Default Docker image posture

The `Dockerfile` sets production-like defaults for development parity even when running the container standalone:

```
ENV SOMABRAIN_FORCE_FULL_STACK=1 \\
    SOMABRAIN_STRICT_REAL=1 \\
    SOMABRAIN_REQUIRE_MEMORY=1 \\
    SOMABRAIN_MODE=enterprise
```

You can override at runtime with `-e VAR=value`, for example:

```bash
docker run --rm -p 9696:9696 \
  -e SOMABRAIN_PORT=9696 \
  -e SOMABRAIN_FORCE_FULL_STACK=0 \
  -e SOMABRAIN_STRICT_REAL=0 \
  somabrain:latest
```
3. Wait for the script to report a healthy `/health` check and review the generated `.env.local`/`ports.json`.
4. Run the smoke checks from step 4 above or the condensed helper:
  ```bash
  bash scripts/smoke_test.sh
  ```
5. With the stack healthy, run the desired test suite (examples in §4). This ensures code and image stay in lockstep with the running services.

## 3. Configure Environment Variables

```bash
source .env.local
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=${SOMABRAIN_MEMORY_HTTP_ENDPOINT:-http://host.docker.internal:9595}
export SOMABRAIN_OTLP_ENDPOINT=http://localhost:4317  # if OTEL collector running
```

Sensitive secrets should **never** be committed. For local testing, store them in `.env.secrets`
(optional) and `source` the file. In CI and production, secrets are injected via Vault or the cloud
secret manager.

## 4. Running Tests

### Unit Tests
```bash
uv run pytest tests -k "not integration" -q
```

> ⚠️ **Python 3.13 heads-up:** if you run tests outside of `uv` (for example via a custom venv), make sure `typing_extensions>=4.12`. Older releases bundled by some tooling crash with `ValueError: '__doc__' in __slots__ conflicts with class variable` when FastAPI imports under Python 3.13. The `uv` workflow already pins a safe version.

To focus on the composite recall scorer (math prioritization, WM reinforcement, metadata weighting), run the
dedicated regression suite:

```bash
uv run pytest tests/test_recall_scoring.py -q
```

### Integration Tests (real services only)
```bash
uv run pytest -m integration -q
```
The suite reads `ports.json` to determine service endpoints.

To confirm the memory round-trip workflow without spinning up the full stack, reuse an existing
pytest scenario that exercises the agent memory module:
```bash
uv run pytest tests/test_agent_memory_module.py::test_encode_and_recall_happy -q
```
The test clears the in-process store, encodes a memory, and asserts it can be recalled via
`somabrain.agent_memory.recall_memory`.

### 4.1 Running tests against an already running API (port 9696)

Most live tests default to a dedicated port 9797 to avoid clobbering dev services. To target the Docker API at
9696 instead, export the lock bypass and the URL explicitly:

```bash
export SOMA_API_URL_LOCK_BYPASS=1
export SOMA_API_URL=http://127.0.0.1:9696
uv run pytest -q
```

Notes:
- Keep the Docker stack running (scripts/dev_up.sh). Health must be ok=true before running tests.
- In dev Docker, Somabrain uses a single worker to ensure WM read‑your‑writes in process.
- Consolidation (/sleep) is time‑budgeted by SOMABRAIN_CONSOLIDATION_TIMEOUT_S (default 1s) to prevent
  long request hangs.

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
SOMA_API_URL=http://127.0.0.1:9797 uv run --active pytest \
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
  uv run pytest -vv tests/test_cognition_learning.py
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
docker exec -i sb_postgres psql -U soma -d somabrain -c '\dt'
uv run alembic upgrade head  # idempotent; safe to rerun
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
uv run ruff check somabrain tests
uv run black somabrain tests
uv run mypy somabrain
```
Pre-commit hooks will be added to automate these steps.

## 7. Development Workflow

1. Pull latest changes and ensure `./scripts/dev_up.sh` runs cleanly.
2. Create a feature branch; update `docs/architecture/CANONICAL_ROADMAP.md` if modifying roadmap
   items.
3. Implement changes with tests.
4. Run unit + integration tests locally (`uv run pytest ...`).
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
- Example: `uv run python clients/python/cli.py "Hello" --session sandbox-cli --token dev-token`.
