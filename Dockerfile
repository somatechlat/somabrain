## Clean multi-stage Dockerfile: build wheel from pyproject and install in slim runtime
### Builder stage: build wheel
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=0

WORKDIR /build

# Install build-time dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /build/
COPY somabrain /build/somabrain
COPY common /build/common
# The scripts directory is only needed for development and testing. It is
# excluded from the build context via .dockerignore, so we do not copy it
# into the builder image.
# COPY scripts /build/scripts
COPY arc_cache.py /build/

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
    && apt-get install -y --no-install-recommends curl supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage and install
COPY --from=builder /build/dist /dist
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -d "/dist" ] && [ -n "$(ls -A /dist)" ]; then pip install /dist/*.whl; else echo "No wheel files found"; exit 1; fi
# Ensure JWT library is available for auth module
RUN --mount=type=cache,target=/root/.cache/pip pip install "PyJWT[crypto]"

# Install Kafka client libraries (always required)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip uninstall -y kafka || true && \
    pip install confluent-kafka kafka-python python-snappy six
# Install pydantic-settings package required by config shared package (pydantic v2 split)
RUN --mount=type=cache,target=/root/.cache/pip pip install pydantic-settings
# Install ASGI server used by service modules launched under supervisor
RUN --mount=type=cache,target=/root/.cache/pip pip install "uvicorn[standard]"
# Install fastavro for Avro deserialization in strict mode
RUN --mount=type=cache,target=/root/.cache/pip pip install fastavro

# Copy only essential runtime assets. Documentation, development scripts and
# example files are excluded to keep the image lean. The .dockerignore file
# already prevents those directories from being added, but we explicitly omit
# them here for clarity.
COPY arc_cache.py /app/
COPY observability /app/observability
COPY services /app/services
COPY config /app/config
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
# Avro/IDL schemas are required for the cognition services
COPY proto /app/proto

# ---------------------------------------------------------------------------
# Runtime scripts needed by the entrypoint
# ---------------------------------------------------------------------------
# The entrypoint expects /app/scripts/start_server.py to launch the FastAPI
# application. The original source resides in the repository's scripts/ folder
# but is excluded from the build context via .dockerignore. We copy the single
# required file explicitly.
COPY scripts/start_server.py /app/scripts/start_server.py

# Belt-and-suspenders: write the hippocampus module directly to the image to
# avoid any context filtering issues. This mirrors the in-repo file exactly.
RUN mkdir -p /app/somabrain && \
    cat > /app/somabrain/hippocampus.py <<'PYCODE' && \
    chmod 0644 /app/somabrain/hippocampus.py
"""
Hippocampal consolidation shim that actually writes to the real memory backend.

This module provides:
- ``ConsolidationConfig``: tunable parameters for buffering and consolidation.
- ``Hippocampus``: accepts episodic payloads, persists them via the configured
  MultiTenantMemory client, and can run NREM/REM style consolidation using the
  existing consolidation routines (no stubs, no fallbacks).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from . import consolidation


@dataclass
class ConsolidationConfig:
    tenant: str = "sandbox"
    buffer_max: int = 512
    nrem_top_k: int = 16
    rem_recomb_rate: float = 0.2
    max_summaries: int = 3
    enable_nrem: bool = True
    enable_rem: bool = True


class Hippocampus:
    """Real consolidation buffer that talks to the live memory backend."""

    def __init__(
        self,
        cfg: ConsolidationConfig,
        *,
        mt_memory=None,
        mt_wm=None,
    ) -> None:
        self.cfg = cfg
        self._buffers: Dict[str, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=cfg.buffer_max)
        )
        if mt_memory is None or mt_wm is None:
            try:
                from . import runtime as _rt  # type: ignore
            except Exception:
                from importlib import import_module

                _rt = import_module("somabrain.runtime_module")
            mt_memory = getattr(_rt, "mt_memory", None) if mt_memory is None else mt_memory
            mt_wm = getattr(_rt, "mt_wm", None) if mt_wm is None else mt_wm
        self._mt_memory = mt_memory
        self._mt_wm = mt_wm

    def add_memory(self, payload: dict, tenant_id: Optional[str] = None) -> None:
        tenant = tenant_id or self.cfg.tenant
        p = dict(payload)
        p.setdefault("memory_type", "episodic")
        self._buffers[tenant].append(p)
        if self._mt_memory is not None:
            mem = self._mt_memory.for_namespace(f"{tenant}")
            key = str(p.get("task") or p.get("fact") or p.get("content") or "episodic")
            mem.remember(key, p)
        if self._mt_wm is not None and hasattr(self._mt_wm, "admit"):
            vec = p.get("vector")
            if vec is not None:
                self._mt_wm.admit(tenant, vec, p)

    def consolidate(self, tenant_id: Optional[str] = None) -> dict:
        tenant = tenant_id or self.cfg.tenant
        if self._mt_memory is None or self._mt_wm is None:
            raise RuntimeError("mt_memory/mt_wm not initialized; cannot consolidate")

        stats = {}
        if self.cfg.enable_nrem:
            stats["nrem"] = consolidation.run_nrem(
                tenant,
                self._mt_memory.cfg,  # type: ignore[attr-defined]
                self._mt_wm,
                self._mt_memory,  # type: ignore[arg-type]
                top_k=self.cfg.nrem_top_k,
                max_summaries=self.cfg.max_summaries,
            )
        if self.cfg.enable_rem:
            stats["rem"] = consolidation.run_rem(
                tenant,
                self._mt_memory.cfg,  # type: ignore[attr-defined]
                self._mt_wm,
                self._mt_memory,  # type: ignore[arg-type]
                recomb_rate=self.cfg.rem_recomb_rate,
                max_summaries=self.cfg.max_summaries,
            )
        return stats
PYCODE

# Development requirements are optional and not required for the runtime image.
# Uncomment the line below if you need to install dev extras inside the container.
# COPY requirements-dev.txt /app/requirements-dev.txt

# Also copy source tree to ensure latest local code is importable at runtime (overrides wheel)
COPY somabrain /app/somabrain

# Add memory package back for runtime imports
COPY memory /app/memory
# Copy shared `common` helpers so imports like `from common...` work at runtime
COPY common /app/common

# Copy and install in-repo helper packages (e.g. libs.kafka_cog) so Avro
# serde and other in-repo modules are importable at runtime. This ensures
# services that import `libs.kafka_cog` find the package inside the image.
# The optional ``libs`` directory contains auxiliary packages that are not required for core functionality.
# It is excluded from the minimal image to keep the footprint small. If needed, include it via a build argument.
ARG INCLUDE_LIBS=false
RUN if [ "$INCLUDE_LIBS" = "true" ]; then \
        cp -r /app/libs /tmp/libs && pip install --no-cache-dir /tmp/libs; \
    else \
        echo "Skipping optional libs installation"; \
    fi

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
