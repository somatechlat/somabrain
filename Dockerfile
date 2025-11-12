## Clean multi-stage Dockerfile: build wheel from pyproject and install in slim runtime
### Builder stage: build wheel
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build-time dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /build/
COPY somabrain /build/somabrain
COPY common /build/common
COPY scripts /build/scripts
COPY arc_cache.py /build/

# Build a wheel reproducibly using build
RUN python -m pip install --upgrade pip build setuptools wheel \
    && python -m build --wheel --no-isolation -o /build/dist

### Runtime stage: slim image with only runtime deps and wheel installed
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System packages for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl librdkafka-dev libsnappy-dev libsnappy1v5 build-essential supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then pip install --no-cache-dir /dist/*.whl; else echo "No wheel files found"; exit 1; fi
# Ensure JWT library is available for auth module
RUN pip install --no-cache-dir "PyJWT[crypto]"

# Ensure confluent-kafka (librdkafka) is available for stronger Kafka semantics in
# integration and production images. Installing via pip will build against
# librdkafka-dev installed above.
# First, remove any conflicting legacy ``kafka`` package that may shadow ``kafka-python``.
RUN pip uninstall -y kafka || true && \
    pip install --no-cache-dir confluent-kafka kafka-python python-snappy || echo "kafka client install failed; continuing without it"
# Ensure only kafka-python is used (which provides its own vendored six). No additional
# legacy kafka package is installed to avoid module name conflict.
# Install six, which is a dependency required by kafka-python for compatibility utilities
RUN pip install --no-cache-dir six
# Install pydantic-settings package required by config shared package (pydantic v2 split)
RUN pip install --no-cache-dir pydantic-settings
# Install ASGI server used by service modules launched under supervisor
RUN pip install --no-cache-dir "uvicorn[standard]"
# Install fastavro for Avro deserialization in strict mode
RUN pip install --no-cache-dir fastavro

# Copy docs, scripts, and memory (for runtime import)
COPY docs /app/docs
COPY scripts /app/scripts
COPY scripts/kafka_smoke_test.py /app/scripts/kafka_smoke_test.py
COPY arc_cache.py /app/
COPY observability /app/observability
COPY services /app/services
COPY config /app/config
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
# Copy Avro/IDL schemas used at runtime by cognition services
COPY proto /app/proto

# Include development requirements for the test service (used when the same image
# runs the ``somabrain_test`` container). The file is copied to the same location
# as the source tree so ``pip install -r /app/requirements-dev.txt`` works.
COPY requirements-dev.txt /app/requirements-dev.txt

# Also copy source tree to ensure latest local code is importable at runtime (overrides wheel)
COPY somabrain /app/somabrain

# Add memory package back for runtime imports
COPY memory /app/memory
# Copy shared `common` helpers so imports like `from common...` work at runtime
COPY common /app/common

# Copy and install in-repo helper packages (e.g. libs.kafka_cog) so Avro
# serde and other in-repo modules are importable at runtime. This ensures
# services that import `libs.kafka_cog` find the package inside the image.
COPY libs /app/libs
RUN if [ -d "/app/libs" ]; then pip install --no-cache-dir /app/libs || echo "installing /app/libs failed"; fi

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
COPY --chown=appuser:appuser --chmod=0755 docker-entrypoint.sh /usr/local/bin/

# Healthcheck against unified /health endpoint (matches compose and docs)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${SOMABRAIN_PORT:-9696}/health" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
