# Production Dockerfile for SomaBrain API
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System packages for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project and install via pyproject dependencies
COPY pyproject.toml README.md /app/
COPY somabrain /app/somabrain
COPY somafractalmemory /app/somafractalmemory
COPY docs /app/docs
COPY scripts /app/scripts

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    # Only attempt editable install if somafractalmemory looks like a Python project
    && if [ -d somafractalmemory ] && { [ -f somafractalmemory/pyproject.toml ] || [ -f somafractalmemory/setup.py ]; }; then \
        pip install -e somafractalmemory; \
    fi \
    && pip install .

# Create non-root user
RUN useradd --create-home --shell /sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose default API port (can be overridden)
EXPOSE 9696

# Environment defaults
ENV SOMABRAIN_MEMORY_MODE=local \
    SOMABRAIN_HOST=0.0.0.0 \
    SOMABRAIN_PORT=9696 \
    SOMABRAIN_WORKERS=1

# Entrypoint script for flexible startup
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/

# Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${SOMABRAIN_PORT:-9696}/health" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
