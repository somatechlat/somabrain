# Installation Guide

**Purpose** Bring up a functioning SomaBrain stack for evaluation or development.

**Audience** Engineers and operators who need the API running locally or in a lab environment.

**Prerequisites**
- Docker Desktop **or** a host with Docker Engine + Compose Plugin.
- Python 3.11 (optional, for running the API directly).
- An HTTP memory backend listening on port 9595.

Important when using Docker Desktop:
- Inside containers, `127.0.0.1` refers to the container itself. Point the API to the host memory service using `http://host.docker.internal:9595`.
- The provided Dockerfile and dev scripts default to this safe value; you can verify wiring at `GET /diagnostics`.

---

## 1. Clone the Repository

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
```

Check out the branch/tag you intend to run, then copy `.env.example` to `.env` if you want to override defaults.

---

## 2. Start Required Dependencies

The Docker Compose bundle in the repo launches the FastAPI runtime plus Redis, Kafka, OPA, Postgres, Prometheus, and exporters. It **does not** ship the external memory HTTP service – start your memory backend separately before booting SomaBrain.

```bash
# bring up SomaBrain services
docker compose up -d

# follow logs if you need to confirm startup
docker compose logs -f somabrain_app
```

Alternatively, use the helper script that writes a complete `.env`, builds the image if needed, and waits for health:

```bash
./scripts/dev_up.sh
```

On Linux hosts where `host.docker.internal` doesn’t resolve inside containers, set `SOMABRAIN_MEMORY_HTTP_ENDPOINT` in `.env` to the host IP explicitly (e.g., `http://192.168.1.10:9595`).

Verify the stack:

```bash
curl -s http://localhost:9696/health | jq
curl -s http://localhost:9696/metrics | head
curl -s http://localhost:9696/diagnostics | jq   # wiring snapshot (sanitized)
```

A healthy response returns HTTP 200 with `memory_ok`, `embedder_ok`, and `predictor_ok` all `true`. If `ready` is `false`, the API is still booting or waiting for an external dependency (typically the memory service).

---

## 3. Running the API Without Docker (Optional)

Use this mode only when you already have the dependencies (Redis, memory service, Kafka, OPA, Postgres) running elsewhere.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e .[dev]

export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595   # For direct host runs (uvicorn)
export SOMABRAIN_MODE=development          # dev only (auth relaxed via mode)
export SOMABRAIN_REQUIRE_MEMORY=0          # unless you have a live backend

uvicorn somabrain.app:app --host 127.0.0.1 --port 9696 --reload
```

Do not relax auth outside development mode; use proper Bearer tokens in shared environments.

---

## 4. Shutdown & Cleanup

```bash
# stop services, keep volumes
docker compose down

# optional: remove persisted data
docker compose down --volumes

# optional: delete built images
docker image prune -f --filter label=com.docker.compose.project=somabrain
```

---

## Verification Checklist

| Step | Command | Expected |
|------|---------|----------|
| Health check | `curl -s http://localhost:9696/health` | JSON with `"memory_ok": true` (or descriptive error) |
| Remember test | `curl -X POST http://localhost:9696/remember ...` | Response containing `"ok": true` |
| Recall test | `curl -X POST http://localhost:9696/recall ...` | Results array (may be empty if memory backend ignored the write) |

If any check fails, consult [FAQ](faq.md) and `docker compose logs`.

---

**Common Issues**

- `503 memory backend unavailable` – the memory HTTP service on port 9595 was not reachable; either point `SOMABRAIN_MEMORY_HTTP_ENDPOINT` at a working endpoint or set `SOMABRAIN_REQUIRE_MEMORY=0` for non-production testing.
- Port clashes on 9696 / 20001‑20007 – adjust exported ports in `.env`.
- Kafka slow to start – wait for the broker healthcheck (`somabrain_kafka` container) before sending recall requests.
- Authentication failures – provide a Bearer token (see `.env` for `SOMABRAIN_API_TOKEN`). In dev mode, auth may be relaxed by policy.

---

**Next Steps**

- Walk through the [Quick Start Tutorial](quick-start-tutorial.md) to validate memory ingestion and recall.
- Review [features/api-integration.md](features/api-integration.md) for required headers and error handling.
- For production hardening, follow the [Technical Manual – Deployment](../technical/deployment.md).
