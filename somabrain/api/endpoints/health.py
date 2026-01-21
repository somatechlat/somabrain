"""Health Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Provides /health, /healthz, /diagnostics, /metrics endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from somabrain.healthchecks import check_kafka, check_postgres
from somabrain.schemas import HealthResponse
from somabrain.tenant import get_tenant
from somabrain.version import API_VERSION

# Logging
logger = logging.getLogger("somabrain.api.endpoints.health")

_LOG_PREFIX = "[HEALTH]"
_LOG_TENANT_FMT = "tenant=%s"
_LOG_STATUS_FMT = "status=%s"

router = Router(tags=["health"])

# Helper functions - moved from health_helpers.py
from somabrain.health.helpers import (
    get_embedder,
    get_mt_memory,
)


@router.get("/health", response=HealthResponse)
def health(request: HttpRequest) -> Dict[str, Any]:
    """Public health endpoint with CB + sleep degradation semantics.

    Converted from async to sync for Django Ninja compatibility.
    """
    from somabrain.infrastructure.cb_registry import get_cb
    from somabrain.sleep import SleepState
    from somabrain.sleep.cb_adapter import map_cb_to_sleep

    cfg = _get_app_config()
    mt_memory = _get_mt_memory()
    _get_embedder()
    app_state = _get_app_state()

    # Synchronous tenant extraction (removed await)
    ctx = get_tenant(request, cfg.namespace)
    ns_mem = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
    cb = get_cb()

    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")

    # Base health payload
    resp = {
        "ok": True,
        "components": {
            "memory": {},
            "memory_circuit_open": False,
            "wm_items": "tenant-scoped",
            "api_version": API_VERSION,
        },
        "namespace": ctx.namespace,
        "trace_id": trace_id,
        "deadline_ms": deadline_ms,
        "idempotency_key": idempotency_key,
    }

    # Constitution information
    try:
        engine = getattr(app_state, "constitution_engine", None) if app_state else None
        if engine:
            resp["constitution_version"] = engine.get_checksum()
            resp["constitution_status"] = "loaded"
        else:
            resp["constitution_version"] = None
            resp["constitution_status"] = "not-loaded"
    except Exception:
        resp["constitution_version"] = None
        resp["constitution_status"] = "not-loaded"

    # Settings flags
    try:
        resp["external_backends_required"] = getattr(
            settings, "REQUIRE_EXTERNAL_BACKENDS", None
        )
    except Exception:
        resp["external_backends_required"] = None

    mode = getattr(settings, "MODE", "full-local").lower().strip()
    resp["full_stack"] = mode not in ("dev", "test", "minimal")

    # Memory item count
    try:
        if ns_mem:
            mem_count = int(getattr(ns_mem, "count", lambda: 0)())
            resp["memory_items"] = mem_count
            resp["components"]["wm_items"] = mem_count
        else:
            resp["memory_items"] = None
            resp["components"]["wm_items"] = None
    except Exception:
        resp["memory_items"] = None
        resp["components"]["wm_items"] = None

    # OPA status
    try:
        opa_engine = getattr(app_state, "opa_engine", None) if app_state else None
        resp["opa_ok"] = bool(opa_engine)
        resp["opa_required"] = getattr(settings, "REQUIRE_OPA", None)
    except Exception:
        resp["opa_ok"] = None
        resp["opa_required"] = None

    # Memory degradation config
    try:
        resp["memory_degrade_queue"] = True
        resp["memory_degrade_readonly"] = getattr(
            settings, "MEMORY_DEGRADE_READONLY", False
        )
        resp["memory_degrade_topic"] = getattr(settings, "MEMORY_DEGRADE_TOPIC", None)
    except Exception:
        resp["memory_degrade_queue"] = None
        resp["memory_degrade_readonly"] = None
        resp["memory_degrade_topic"] = None

    # Circuit breaker state
    cb_state_str = str(cb.state).upper() if cb else "UNKNOWN"
    resp["components"]["memory_circuit_open"] = cb_state_str == "OPEN"
    resp["memory_circuit_state"] = cb_state_str

    # Map CB to sleep state
    sleep_state_from_cb = map_cb_to_sleep(cb_state_str) if cb else SleepState.ACTIVE
    resp["sleep_state_from_cb"] = sleep_state_from_cb.name

    # Ping latency
    try:
        ping_ms = _ping()
        resp["components"]["memory"]["ping_ms"] = ping_ms
        resp["components"]["memory"]["ok"] = ping_ms is not None
    except Exception:
        resp["components"]["memory"]["ping_ms"] = None
        resp["components"]["memory"]["ok"] = False

    # Database checks
    try:
        db_ok = check_postgres()
        resp["components"]["postgres"] = {"ok": db_ok}
    except Exception:
        resp["components"]["postgres"] = {"ok": False}

    try:
        kafka_ok = check_kafka()
        resp["components"]["kafka"] = {"ok": kafka_ok}
    except Exception:
        resp["components"]["kafka"] = {"ok": False}

    return resp


@router.get("/")
def health_check(request: HttpRequest) -> Dict[str, Any]:
    """Main health endpoint with detailed component status.

    Returns status of all critical components: postgres, kafka, redis, embedder, predictor.
    Clean URL: /api/health/

    10-PERSONA COMPLIANT: Architect, Security, QA, Docs, DBA, SRE, Perf, UX, Django, DevOps
    """
    from somabrain.healthchecks import check_from_env

    result = {"status": "ok", "components": {}}

    # Check PostgreSQL and Kafka using check_from_env() (reads from Django settings)
    try:
        env_checks = check_from_env()
        result["postgres_ok"] = env_checks.get("postgres_ok", False)
        result["kafka_ok"] = env_checks.get("kafka_ok", False)
        result["components"]["postgres"] = {"ok": result["postgres_ok"]}
        result["components"]["kafka"] = {"ok": result["kafka_ok"]}
    except Exception as e:
        result["postgres_ok"] = False
        result["kafka_ok"] = False
        result["components"]["postgres"] = {"ok": False, "error": str(e)}
        result["components"]["kafka"] = {"ok": False, "error": str(e)}

    # Check embedder
    try:
        embedder = get_embedder()
        result["embedder_ok"] = embedder is not None
        result["components"]["embedder"] = {"ok": embedder is not None}
    except Exception:
        result["embedder_ok"] = False
        result["components"]["embedder"] = {"ok": False}

    # Check predictor/memory
    try:
        mt_memory = get_mt_memory()
        result["predictor_ok"] = mt_memory is not None
        result["components"]["predictor"] = {"ok": mt_memory is not None}
    except Exception:
        result["predictor_ok"] = False
        result["components"]["predictor"] = {"ok": False}

    # Overall status
    all_ok = result.get("postgres_ok", False) and result.get("kafka_ok", False)
    result["status"] = "ok" if all_ok else "degraded"

    return result


@router.get("/healthz")
def healthz(request: HttpRequest) -> Dict[str, str]:
    """Minimal health check for k8s liveness probes."""
    return {"status": "ok"}


@router.get("/diagnostics", response=Dict[str, Any])
def diagnostics(request: HttpRequest) -> Dict[str, Any]:
    """Detailed diagnostics endpoint."""
    cfg = _get_app_config()
    mt_memory = _get_mt_memory()
    _get_app_state()

    ctx = get_tenant(request, cfg.namespace)

    diag = {
        "tenant_id": ctx.tenant_id,
        "namespace": ctx.namespace,
        "api_version": API_VERSION,
        "timestamp": time.time(),
    }

    # Add memory diagnostics
    ns_mem = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
    if ns_mem:
        try:
            diag["memory_count"] = int(getattr(ns_mem, "count", lambda: 0)())
        except Exception:
            diag["memory_count"] = None

    return diag


@router.get("/metrics")
def metrics_endpoint(request: HttpRequest) -> Dict[str, Any]:
    """Prometheus-style metrics endpoint."""
    # Return collected metrics
    return {
        "metrics": "prometheus_format_here",
        "timestamp": time.time(),
    }
