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

# Include development requirements so this image can install pytest/dev extras
# when needed (e.g., ``pip install -r /app/requirements-dev.txt`` inside a container).
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
