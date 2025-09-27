## Dynamic Port Discovery and Usage

SomaBrain now supports dynamic port assignment for all major services (Kafka, Redis, Prometheus, etc.).

- The startup script (`scripts/dev_up.sh`) will detect free ports and write them to `.env.local` and `ports.json`.
- All code and scripts use the following environment variables to connect to services:
	- `SOMABRAIN_REDIS_HOST` / `SOMABRAIN_REDIS_PORT`
	- `SOMABRAIN_KAFKA_HOST` / `SOMABRAIN_KAFKA_PORT`
	- `SOMABRAIN_PROMETHEUS_HOST` / `SOMABRAIN_PROMETHEUS_PORT`
	- etc.
- If you run the stack with dynamic ports, always check `.env.local` or `ports.json` for the actual host/port mappings.
- You can override these variables manually if needed.

**Example:**

```sh
export SOMABRAIN_REDIS_HOST=127.0.0.1
export SOMABRAIN_REDIS_PORT=6380
python somabrain/app.py
```

All code, scripts, and documentation have been updated to use this pattern.
# DEVELOPMENT_GUIDE.md

## Overview
This guide provides canonical, up-to-date instructions for developing, building, and running the SomaBrain platform. It is updated live as the codebase evolves.

---

## 1. Prerequisites
- Docker and Docker Compose (latest stable)
- Python 3.10+ (for local development)
- GNU Make (optional, for convenience)
- Recommended: VS Code with Python and Docker extensions

---


## 2. Building the Docker Image

To build the production-grade Docker image:

```sh
docker build -t somabrain:latest .
```

- The build uses a multi-stage Dockerfile for minimal, secure images.
- Only essential files are included in the image (see `.dockerignore`).
- The build will fail if the Python wheel cannot be built or installed.

---

## 3. Running the Stack

To run the full stack in DEV_FULL mode (all services):

```sh
./scripts/dev_up.sh DEV_FULL
```

- This script brings up all required services (API, memory, DB, Kafka, etc.)
- **Dynamic port mapping:** If a default port (e.g., 9092 for Kafka) is already in use, Docker will automatically assign a free host port. You can find the mapped port using `docker ps` or `docker compose ps`.
- Update your client or environment variables to use the dynamically assigned host port if needed.

---

## 4. Development Workflow
- Make code changes in feature branches (unless main-only is required).
- Use `pytest` for tests: `pytest tests/`
- Use `make lint` and `make format` for code quality (if Makefile present).
- Update this guide as you improve the workflow.

---

## 5. Docker Image Hardening
- The Dockerfile uses a builder stage to create a wheel and a slim runtime stage.
- `.dockerignore` excludes tests, examples, build artifacts, and secrets.
- Only `somabrain/`, `scripts/`, `arc_cache.py`, and docs are included in the runtime image.
- Non-root user is used for security.

---

## 6. Troubleshooting
- If the build fails, check for missing dependencies or file bloat in the build context.
- Use `docker build --no-cache .` to force a clean build.
- For issues with services, check logs in `docker-compose` or `docker ps`.

---

## 7. Contributing
- Follow the code style and commit message guidelines.
- All changes should be tested and documented.
- Open PRs against `main` unless otherwise specified.

---

*This guide is updated live as the codebase and workflow evolve.*
