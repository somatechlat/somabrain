## Clean multi-stage Dockerfile: build wheel from pyproject and install in slim runtime
### Builder stage: build wheel
FROM python:3.10-slim AS builder

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
COPY scripts /build/scripts
COPY arc_cache.py /build/

# Build a wheel reproducibly using build
RUN python -m pip install --upgrade pip build setuptools wheel \
    && python -m build --wheel --no-isolation -o /build/dist

### Runtime stage: slim image with only runtime deps and wheel installed
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System packages for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl librdkafka-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then pip install --no-cache-dir /dist/*.whl; else echo "No wheel files found"; exit 1; fi

# Ensure confluent-kafka (librdkafka) is available for stronger Kafka semantics in
# integration and production images. Installing via pip will build against
# librdkafka-dev installed above.
RUN pip install --no-cache-dir confluent-kafka kafka-python || echo "kafka client install failed; continuing without it"

# Copy docs, scripts, and memory (for runtime import)
COPY docs /app/docs
COPY scripts /app/scripts
COPY scripts/kafka_smoke_test.py /app/scripts/kafka_smoke_test.py
COPY arc_cache.py /app/
COPY brain /app/brain
COPY observability /app/observability

# Add memory package back for runtime imports
COPY memory /app/memory

# Create non-root user
RUN useradd --create-home --shell /sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose default API port (can be overridden)
EXPOSE 9696

# Environment defaults
ENV SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595 \
    SOMABRAIN_HOST=0.0.0.0 \
    SOMABRAIN_PORT=9696 \
    SOMABRAIN_WORKERS=1

# Entrypoint script for flexible startup
COPY --chown=appuser:appuser --chmod=0755 docker-entrypoint.sh /usr/local/bin/

# Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${SOMABRAIN_PORT:-9696}/health" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
