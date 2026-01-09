# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 ARCHITECTURE: COLIMA + TILT + MINIKUBE 🚨
# ═══════════════════════════════════════════════════════════════════════════════
# This project uses:
#   ✅ COLIMA   - Docker runtime (NOT Docker Desktop)
#   ✅ TILT     - Development orchestration
#   ✅ MINIKUBE - Kubernetes cluster
#
# ❌ DO NOT USE DOCKER DESKTOP
# ❌ DO NOT USE docker-compose directly
#
# Start with: tilt up --port <port>
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# RUST BUILDER STAGE: Compile somabrain_rs (high-performance cognitive core)
# Uses Python 3.12 base to ensure wheel compatibility with runtime
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS rust-builder

WORKDIR /rust

# Install Rust toolchain via rustup and build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain=1.83.0

# Add Rust to PATH and install maturin
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install maturin

# Copy Rust source
COPY rust_core /rust/rust_core

# Build the Rust extension wheel for Python 3.12
WORKDIR /rust/rust_core
RUN maturin build --release -o /rust/dist

# ═══════════════════════════════════════════════════════════════════════════════
# PYTHON BUILDER STAGE: Build Python wheel
# ═══════════════════════════════════════════════════════════════════════════════
## Clean multi-stage Dockerfile: build wheel from pyproject and install in slim runtime
### Builder stage: build wheel
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /build

# Install build-time dependencies
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends build-essential git \
#     && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /build/
COPY somabrain /build/somabrain
COPY common /build/common
# The scripts directory is only needed for development and testing. It is
# excluded from the build context via .dockerignore, so we do not copy it
# into the builder image.
# COPY scripts /build/scripts


# Build a wheel reproducibly using build
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip build setuptools wheel \
    && python -m build --wheel --no-isolation -o /build/dist

### Runtime stage: slim image with only runtime deps and wheel installed
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /app

# System packages for healthcheck and optional components
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl supervisor python3-numpy \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then pip install /dist/*.whl; else echo "No wheel files found"; exit 1; fi

# ═══════════════════════════════════════════════════════════════════════════════
# RUST CORE: Install precompiled somabrain_rs extension (27x faster cognitive ops)
# ═══════════════════════════════════════════════════════════════════════════════
COPY --from=rust-builder /rust/dist /rust_dist
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -d "/rust_dist" ] && [ -n "$(ls -A /rust_dist)" ]; then \
    pip install /rust_dist/*.whl && echo "✅ Rust core installed"; \
    else \
    echo "⚠️ No Rust wheel found - falling back to Python"; \
    fi
# Ensure JWT library is available for auth module
RUN --mount=type=cache,target=/root/.cache/pip pip install "PyJWT[crypto]"

# Install Kafka client libraries (always required)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip uninstall -y kafka || true && \
    pip install confluent-kafka kafka-python python-snappy six
# Install pydantic-settings package required by config shared package (pydantic v2 split)
RUN --mount=type=cache,target=/root/.cache/pip pip install pydantic-settings
# Install gunicorn for Django production (pure Django - NO uvicorn per VIBE rules)
RUN --mount=type=cache,target=/root/.cache/pip pip install gunicorn
# Install fastavro for Avro deserialization in strict mode
RUN --mount=type=cache,target=/root/.cache/pip pip install fastavro

# Copy only essential runtime assets. Documentation, development scripts and
# example files are excluded to keep the image lean. The .dockerignore file
# already prevents those directories from being added, but we explicitly omit
# them here for clarity.

COPY observability /app/observability
COPY services /app/services
# Django migrations are created in somabrain/migrations/ and saas/migrations/
# Alembic/SQLAlchemy removed per VIBE rules - pure Django ORM
# Avro/IDL schemas are required for the cognition services
COPY proto /app/proto
COPY manage.py /app/manage.py

# ---------------------------------------------------------------------------
# Runtime scripts needed by the entrypoint
# ---------------------------------------------------------------------------
# Pure Django startup - NO FastAPI/uvicorn per VIBE rules
# Django uses manage.py runserver (dev) or gunicorn (prod)
# Kafka smoke test is required by docker-entrypoint.sh for health checks
COPY tests/smoke/kafka_smoke_test.py /app/tests/smoke/kafka_smoke_test.py
# Runtime initialization script for setting up singletons before app start
COPY scripts/initialize_runtime.py /app/scripts/initialize_runtime.py

# Belt-and-suspenders: write the hippocampus module directly to the image to
# avoid any context filtering issues. This mirrors the in-repo file exactly.

# Development requirements are optional and not required for the runtime image.
# Uncomment the line below if you need to install dev extras inside the container.
# COPY requirements-dev.txt /app/requirements-dev.txt

# Also copy source tree to ensure latest local code is importable at runtime (overrides wheel)
COPY somabrain /app/somabrain

# Add memory package back for runtime imports
COPY memory /app/memory
# Copy shared `common` helpers so imports like `from common...` work at runtime
COPY common /app/common

# Copy optional helper libraries (e.g., kafka_cog) into the image. These are pure Python packages without a
# setuptools/pyproject configuration, so we expose them via PYTHONPATH instead of installing with pip.
COPY libs /app/libs

# Ensure runtime imports can find the copied libraries.
ENV PYTHONPATH=/app:/app/libs:${PYTHONPATH:-}

# Ensure runtime imports from /app are visible
ENV PYTHONPATH=/app:${PYTHONPATH:-}

# Prepare writable log dir for supervisor and services
RUN mkdir -p /app/logs && chmod 0755 /app/logs

# Supervisor config for multi-process cognitive services (used by somabrain_cog container)
COPY ops/supervisor /app/ops/supervisor

# Create non-root user with UID/GID 1000
RUN set -eux; \
    if ! getent group 1000 >/dev/null; then groupadd -g 1000 appuser; fi; \
    if ! id -u 1000 >/dev/null 2>&1; then useradd --create-home -u 1000 -g 1000 --shell /usr/sbin/nologin appuser; fi; \
    chown -R 1000:1000 /app
USER 1000:1000

# Expose default API port (can be overridden)
EXPOSE 9696

# Environment defaults (production-like for development parity)
# Override at runtime with -e VAR=value as needed.
# Default memory endpoint for Docker Desktop on macOS/Windows; override in compose/k8s as needed
ENV SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595 \
    SOMABRAIN_HOST=0.0.0.0 \
    SOMABRAIN_PORT=9696 \
    SOMABRAIN_WORKERS=1 \
    SOMABRAIN_FORCE_FULL_STACK=1 \
    SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1 \
    SOMABRAIN_REQUIRE_MEMORY=1 \
    SOMABRAIN_MODE=enterprise

# Entrypoint script for flexible startup
COPY --chown=appuser:appuser --chmod=0755 infra/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Healthcheck against unified /health endpoint (matches compose and docs)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${SOMABRAIN_PORT:-9696}/health" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
