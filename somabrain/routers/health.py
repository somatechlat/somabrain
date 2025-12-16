"""Health Router - Health check, metrics, and diagnostics endpoints.

Extracted from somabrain/app.py per monolithic-decomposition spec.
Provides /health, /healthz, /diagnostics, /metrics, /health/memory,
/health/oak, and /health/metrics endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Request

from common.config.settings import settings
from somabrain import metrics as M, schemas as S
from somabrain.auth import require_auth
from somabrain.healthchecks import check_kafka, check_postgres
from somabrain.tenant import get_tenant as get_tenant_async
from somabrain.version import API_VERSION

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("somabrain.routers.health")

# Log format constants for consistent output
_LOG_PREFIX = "[HEALTH]"
_LOG_TENANT_FMT = "tenant=%s"
_LOG_STATUS_FMT = "status=%s"

router = APIRouter(tags=["health"])


# Helper functions - Extracted to somabrain/routers/health_helpers.py
from somabrain.routers.health_helpers import (
    get_app_config as _get_app_config,
    get_mt_memory as _get_mt_memory,
    get_embedder as _get_embedder,
    get_app_state as _get_app_state,
    ping as _ping,
    milvus_metrics_for_tenant as _milvus_metrics_for_tenant,
)


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=S.HealthResponse)
async def health(request: Request) -> S.HealthResponse:
    """Public health endpoint with shared CB + sleep degradation semantics."""
    from somabrain.infrastructure.cb_registry import get_cb
    from somabrain.sleep import SleepState
    from somabrain.sleep.cb_adapter import map_cb_to_sleep

    cfg = _get_app_config()
    mt_memory = _get_mt_memory()
    embedder = _get_embedder()
    app_state = _get_app_state()

    ctx = await get_tenant_async(request, cfg.namespace)
    tenant_id = ctx.tenant_id
    ns_mem = mt_memory.for_namespace(ctx.namespace) if mt_memory else None
    cb = get_cb()

    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    deadline_ms = request.headers.get("X-Deadline-MS")
    idempotency_key = request.headers.get("X-Idempotency-Key")

    # Base health payload
    resp = S.HealthResponse(
        ok=True,
        components={
            "memory": {},
            "memory_circuit_open": False,
            "wm_items": "tenant-scoped",
            "api_version": API_VERSION,
        },
    ).model_dump()

    # Core identifiers
    resp["namespace"] = ctx.namespace
    resp["trace_id"] = trace_id
    resp["deadline_ms"] = deadline_ms
    resp["idempotency_key"] = idempotency_key

    # Constitution information (if engine loaded)
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

    # External backend requirement flag from settings
    try:
        resp["external_backends_required"] = getattr(
            settings, "require_external_backends", None
        )
    except Exception:
        resp["external_backends_required"] = None

    # Full-stack mode flag
    mode = getattr(settings, "mode", "full-local").lower().strip()
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

    # OPA integration status
    try:
        opa_engine = getattr(app_state, "opa_engine", None) if app_state else None
        resp["opa_ok"] = bool(opa_engine)
        resp["opa_required"] = getattr(settings, "require_opa", None)
    except Exception:
        resp["opa_ok"] = None
        resp["opa_required"] = None

    # Memory degradation configuration
    try:
        resp["memory_degrade_queue"] = True
        resp["memory_degrade_readonly"] = getattr(
            settings, "memory_degrade_readonly", False
        )
        resp["memory_degrade_topic"] = getattr(settings, "memory_degrade_topic", None)
    except Exception:
        resp["memory_degrade_queue"] = None
        resp["memory_degrade_readonly"] = None
        resp["memory_degrade_topic"] = None

    try:
        resp["external_backends_required"] = bool(
            getattr(settings, "require_external_backends", True)
        )
    except Exception:
        resp["external_backends_required"] = True

    # Predictor / embedder diagnostics
    _PREDICTOR_PROVIDER = getattr(cfg, "predictor_provider", "mahal")
    _EMBED_PROVIDER = getattr(cfg, "embed_provider", "tiny")
    resp["predictor_provider"] = _PREDICTOR_PROVIDER

    try:
        edim = None
        if embedder is not None:
            vec = embedder.embed("health_probe")
            if hasattr(vec, "shape"):
                shape = getattr(vec, "shape")
                edim = int(shape[0]) if isinstance(shape, (list, tuple)) else int(shape)
        resp["embedder"] = {"provider": _EMBED_PROVIDER, "dim": edim}
    except Exception:
        resp["embedder"] = {"provider": _EMBED_PROVIDER, "dim": None}

    # Post-processing of fields that may still be None
    if resp.get("constitution_status") is None:
        resp["constitution_status"] = "not-loaded"
    if resp.get("retrieval_ready") is None:
        resp["retrieval_ready"] = bool(resp.get("embedder_ok"))
    if resp.get("opa_required") is None:
        resp["opa_required"] = False

    # Memory health + CB mapping
    memory_ok = False
    try:
        if ns_mem:
            mhealth = ns_mem.health()
            resp["components"]["memory"] = mhealth
            if isinstance(mhealth, dict):
                memory_ok = (
                    bool(mhealth.get("http"))
                    or bool(mhealth.get("ok"))
                    or bool(mhealth.get("healthy"))
                )
    except Exception:
        memory_ok = False

    if memory_ok:
        cb.record_success(tenant_id)
    else:
        cb.record_failure(tenant_id)

    # Learning metrics exposure
    try:
        from somabrain.metrics import tau_gauge

        resp["tau"] = float(tau_gauge.labels(tenant_id=tenant_id)._value.get())
    except Exception:
        resp["tau"] = None

    # Entropy-cap configuration
    try:
        resp["entropy_cap_enabled"] = getattr(settings, "entropy_cap_enabled", None)
        resp["entropy_cap"] = getattr(settings, "entropy_cap", None)
    except Exception:
        resp["entropy_cap_enabled"] = None
        resp["entropy_cap"] = None

    try:
        from somabrain.metrics import LEARNING_RETRIEVAL_ENTROPY

        resp["retrieval_entropy"] = float(
            LEARNING_RETRIEVAL_ENTROPY.labels(tenant_id=tenant_id)._value.get()
        )
    except Exception:
        resp["retrieval_entropy"] = None

    # Recompute circuit state after recording success/failure
    circuit_open = cb.is_open(tenant_id)
    should_reset = cb.should_attempt_reset(tenant_id)
    resp["memory_circuit_open"] = circuit_open
    resp["components"]["memory_circuit_open"] = circuit_open
    resp["memory_should_reset"] = should_reset
    resp["memory_ok"] = memory_ok
    resp["memory_degraded"] = circuit_open or should_reset

    # Degradation manager status (per E1.1-E1.5)
    try:
        from somabrain.infrastructure.degradation import get_degradation_manager

        dm = get_degradation_manager()
        degraded_duration = dm.get_degraded_duration(tenant_id)
        resp["degradation_duration_seconds"] = degraded_duration
        resp["degradation_alert_triggered"] = (
            dm.check_alert(tenant_id) if degraded_duration else False
        )
    except Exception:
        resp["degradation_duration_seconds"] = None
        resp["degradation_alert_triggered"] = None

    # Outbox buffering diagnostics
    try:
        from somabrain.db.models.outbox import OutboxEvent
        from somabrain.storage.db import get_session_factory

        Session = get_session_factory()
        pending = 0
        last_created = None
        with Session() as s:
            pending = (
                s.query(OutboxEvent)
                .filter(
                    OutboxEvent.status == "pending", OutboxEvent.tenant_id == tenant_id
                )
                .count()
            )
            last = (
                s.query(OutboxEvent)
                .filter(
                    OutboxEvent.status == "pending", OutboxEvent.tenant_id == tenant_id
                )
                .order_by(OutboxEvent.created_at.desc())
                .first()
            )
            if last and getattr(last, "created_at", None):
                last_created = last.created_at.isoformat()
        resp["components"]["outbox"] = {
            "pending": pending,
            "last_pending_created_at": last_created,
        }
    except Exception:
        resp["components"]["outbox"] = {
            "pending": None,
            "last_pending_created_at": None,
        }

    # Sleep state derived from CB status
    resp["sleep_state"] = map_cb_to_sleep(cb, tenant_id, SleepState.ACTIVE).value

    # WM items
    try:
        if ns_mem:
            resp["components"]["wm_items"] = int(getattr(ns_mem, "count", lambda: 0)())
        else:
            resp["components"]["wm_items"] = 0
    except Exception:
        resp["components"]["wm_items"] = 0

    # Downstream health (integrator + segmentation)
    integrator_url = settings.integrator_health_url
    segmentation_url = settings.segmentation_health_url
    resp["integrator_health"] = _ping(integrator_url)
    resp["segmentation_health"] = _ping(segmentation_url)

    # Backend readiness checks
    predictor_ok = (_PREDICTOR_PROVIDER not in ("stub", "baseline")) or (
        not resp.get("external_backends_required", False)
    )
    embedder_ok = resp["embedder"]["dim"] is not None or embedder is not None

    kafka_ok = check_kafka(settings.kafka_bootstrap_servers)
    postgres_ok = check_postgres(settings.postgres_dsn)

    resp["kafka_ok"] = bool(kafka_ok)
    resp["postgres_ok"] = bool(postgres_ok)
    resp["predictor_ok"] = bool(predictor_ok)
    resp["embedder_ok"] = bool(embedder_ok)

    resp["ready"] = bool(
        memory_ok
        and not circuit_open
        and predictor_ok
        and embedder_ok
        and kafka_ok
        and postgres_ok
    )

    # Minimal API flag for diagnostics
    resp["minimal_public_api"] = bool(settings.minimal_public_api)

    # Observability readiness
    resp["metrics_required"] = ["kafka", "postgres"]
    resp["metrics_ready"] = bool(kafka_ok and postgres_ok)

    milvus_stats = _milvus_metrics_for_tenant(tenant_id)
    resp["milvus_metrics"] = milvus_stats
    resp["components"]["milvus"] = milvus_stats

    return resp


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return await M.metrics_endpoint()


@router.get("/healthz", include_in_schema=False)
async def healthz(request: Request) -> dict:
    """Alias for /health."""
    return await health(request)


@router.get("/diagnostics", include_in_schema=False)
async def diagnostics() -> dict:
    """Lightweight diagnostics (sanitized; no secrets)."""
    cfg = _get_app_config()
    in_docker = settings.running_in_docker
    ep = str(getattr(getattr(cfg, "http", object()), "endpoint", "") or "").strip()

    mode = settings.mode.strip()
    ext_req = settings.require_external_backends
    require_memory = settings.require_memory

    return {
        "in_container": in_docker,
        "mode": mode or "",
        "external_backends_required": ext_req,
        "require_memory": require_memory,
        "memory_endpoint": ep or "",
        "env_memory_endpoint": settings.memory_http_endpoint,
        "memory_token_present": bool(
            getattr(getattr(cfg, "http", object()), "token", None)
        ),
        "api_version": int(API_VERSION),
    }


@router.get("/health/memory", response_model=Dict[str, Any])
async def health_memory(request: Request) -> Dict[str, Any]:
    """Get per-tenant memory service health and circuit breaker state."""
    from somabrain.services.memory_service import MemoryService

    cfg = _get_app_config()
    mt_memory = _get_mt_memory()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    # Create memory service instance for this tenant
    memsvc = MemoryService(mt_memory, ctx.namespace)
    circuit_state = memsvc.get_circuit_state()

    # Get outbox pending count for this tenant
    from somabrain.db.outbox import get_pending_events

    try:
        pending_count = len(get_pending_events(limit=1000))
    except Exception:
        pending_count = 0

    return {
        "tenant": ctx.tenant_id,
        "circuit_breaker": circuit_state,
        "outbox_pending": pending_count,
        "memory_service": (
            "healthy" if not circuit_state["circuit_open"] else "unavailable"
        ),
        "timestamp": time.time(),
    }


@router.get("/health/oak", response_model=Dict[str, Any])
async def health_oak(request: Request) -> Dict[str, Any]:
    """Health check for Oak subsystem.

    Returns the health of the Milvus vector store used for option persistence
    and the OPA policy engine if it is configured.
    """
    from somabrain.milvus_client import MilvusClient

    cfg = _get_app_config()
    app_state = _get_app_state()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    # Milvus health
    milvus_ok: bool = False
    try:
        _ = MilvusClient()
        milvus_ok = True
    except Exception:
        milvus_ok = False

    # OPA health
    opa_ok: bool = False
    opa_required: bool = getattr(settings, "require_opa", False)
    try:
        opa_engine = getattr(app_state, "opa_engine", None) if app_state else None
        if opa_engine:
            opa_ok = await opa_engine.health()
    except Exception:
        opa_ok = False

    return {
        "tenant": ctx.tenant_id,
        "milvus_ok": milvus_ok,
        "opa_ok": opa_ok,
        "opa_required": opa_required,
    }


@router.get("/health/metrics", response_model=Dict[str, Any])
async def health_metrics(request: Request) -> Dict[str, Any]:
    """Expose Milvus SLO telemetry in a JSON health payload.

    Returns the p95 ingest/search latency gauges and the segment load gauge for
    the tenant associated with the request.
    """
    cfg = _get_app_config()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)

    tenant = ctx.tenant_id
    stats = _milvus_metrics_for_tenant(tenant)
    return {"tenant": tenant, **stats}


# Health Watchdog - Extracted to somabrain/routers/health_watchdog.py
