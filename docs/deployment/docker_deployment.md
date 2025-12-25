# Docker Deployment Guide for Somabrain (Full‑Local Mode)

This document walks you through building, configuring, and running the **full Somabrain stack** locally using Docker.

## Prerequisites
- **Docker Engine** ≥ 24.0 (Docker Desktop on macOS/Windows is fine)
- **Docker Compose** v2 plugin (comes with Docker Desktop)
- **Python 3.11** (only needed for optional local tooling, not for the containers)

## 1. Clone the repository
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
```

## 2. Create an `.env` file (optional but recommended)
The compose file reads many values from environment variables. Create a file named **`.env`** in the repository root and set the values you need. Only a minimal set is required for a full‑local deployment:
```dotenv
# Core service ports (feel free to change the host‑side ports)
SOMABRAIN_HOST_PORT=9696
SOMABRAIN_PORT=9696

# External memory service – we use the real service that runs on the host
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595

# Mode – forces the stack to run in full‑local semantics (no stubs)
SOMABRAIN_MODE=full-local

# Optional: enable auth token for the memory service (if required)
# SOMABRAIN_MEMORY_HTTP_TOKEN=your-token-here
```
Docker Compose automatically loads this file, so you do **not** need to export the variables manually.

## 3. Build the Docker image
The repository ships a multi‑stage Dockerfile that builds a wheel from `pyproject.toml` and installs only runtime dependencies.
```bash
docker build -t somabrain:latest .
```
The build is cached, so subsequent runs are fast.

## 4. Start the full stack
```bash
docker compose up -d
```
The compose file defines the following services (all in the same Docker network `somabrain_net`):
- **Redis**, **Kafka**, **Postgres**, **OPA**, **Jaeger**, **Prometheus**
- **Memory service** is **not** started as a container – the stack expects a real memory HTTP endpoint reachable at `host.docker.internal:9595` (the health check we performed earlier returned **200**).
- **Somabrain app**, **cog**, **outbox‑publisher**, **integrator‑triplet**, etc.

You can verify that everything is healthy:
```bash
# Example health checks (all should return 200)
curl -f http://localhost:9696/health
curl -f http://localhost:16686   # Jaeger UI
curl -f http://localhost:30105   # Prometheus UI
curl -f http://localhost:30104/health?plugins   # OPA
```
Docker will show the status of each container when you run `docker compose ps`.

## 5. Run the integration test (real memory backend)
Make sure the external memory service is running (we already confirmed the health endpoint). Then execute:
```bash
python -m pytest -q tests/integration/test_memory_e2e.py
```
The test should now **pass** because the stack can reach the real memory service.

## 6. Stopping the stack
```bash
docker compose down   # stops containers
# To also delete persisted volumes (Redis, Kafka, Postgres data):
# docker compose down -v
```

## 7. Optional helper script
A small convenience script is provided for one‑click deployment.
```bash
chmod +x scripts/deploy_full_local.sh
./scripts/deploy_full_local.sh
```
The script builds the image (if needed) and starts the compose stack.

---
### TL;DR Commands
```bash
# Clone & cd
git clone https://github.com/somatechlat/somabrain.git && cd somabrain

# .env (minimal)
cat > .env <<EOF
SOMABRAIN_MODE=full-local
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595
EOF

# Build & run
docker compose up -d

# Verify
curl -f http://localhost:9696/health
```
---

**All services run in `full‑local` mode**, which means no mock services are used and the stack expects real back‑ends (Redis, Kafka, Postgres, OPA, and the external memory service). The Dockerfile and `docker‑compose.yml` are already configured for this mode, so no further changes are required.
