"""Admin Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Service management, outbox, quota, and feature flag endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional
from xmlrpc.client import Error as XMLRPCError
from xmlrpc.client import ServerProxy

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somabrain import metrics as M
from somabrain.api.auth import admin_auth
from somabrain.db import outbox as outbox_db
from somabrain.schemas import (
    FeatureFlagsResponse,
    FeatureFlagsUpdateRequest,
    FeatureFlagsUpdateResponse,
    OutboxEventModel,
    OutboxListResponse,
    OutboxReplayRequest,
    OutboxReplayResponse,
    QuotaListResponse,
    QuotaStatus,
)
from somabrain.services.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)

router = Router(tags=["admin"])


# Supervisor helpers
def _get_supervisor_url() -> str:
    """Get the supervisor XML-RPC URL from settings."""
    url = getattr(settings, "SUPERVISOR_URL", None)
    if not url:
        user = settings.SUPERVISOR_HTTP_USER
        pwd = settings.SUPERVISOR_HTTP_PASS
        url = f"http://{user}:{pwd}@somabrain_cog:9001/RPC2"
    return url


def _supervisor() -> ServerProxy:
    """Create a supervisor XML-RPC client."""
    try:
        return ServerProxy(_get_supervisor_url(), allow_none=True)
    except Exception as e:
        raise HttpError(503, f"supervisor client init failed: {e}")


# Service management endpoints
@router.get("/services", auth=admin_auth)
def list_services(request: HttpRequest):
    """List all supervisor-managed services."""
    try:
        s = _supervisor()
        info = s.supervisor.getAllProcessInfo()
        return {"ok": True, "services": info}
    except XMLRPCError as e:
        raise HttpError(502, f"supervisor error: {e}")
    except Exception as e:
        raise HttpError(503, f"cannot reach supervisor: {e}")


@router.get("/services/{name}", auth=admin_auth)
def service_status(request: HttpRequest, name: str):
    """Get status of a specific service."""
    try:
        s = _supervisor()
        info = s.supervisor.getProcessInfo(name)
        return {"ok": True, "service": info}
    except XMLRPCError as e:
        raise HttpError(502, f"supervisor error: {e}")
    except Exception as e:
        raise HttpError(503, f"cannot reach supervisor: {e}")


@router.post("/services/{name}/start", auth=admin_auth)
def service_start(request: HttpRequest, name: str):
    """Start a service."""
    try:
        s = _supervisor()
        res = s.supervisor.startProcess(name, False)
        return {"ok": bool(res), "action": "start", "service": name}
    except XMLRPCError as e:
        raise HttpError(502, f"supervisor error: {e}")
    except Exception as e:
        raise HttpError(503, f"cannot reach supervisor: {e}")


@router.post("/services/{name}/stop", auth=admin_auth)
def service_stop(request: HttpRequest, name: str):
    """Stop a service."""
    try:
        s = _supervisor()
        res = s.supervisor.stopProcess(name, False)
        return {"ok": bool(res), "action": "stop", "service": name}
    except XMLRPCError as e:
        raise HttpError(502, f"supervisor error: {e}")
    except Exception as e:
        raise HttpError(503, f"cannot reach supervisor: {e}")


@router.post("/services/{name}/restart", auth=admin_auth)
def service_restart(request: HttpRequest, name: str):
    """Restart a service."""
    try:
        s = _supervisor()
        try:
            s.supervisor.stopProcess(name, False)
        except Exception as stop_exc:
            logger.debug(
                "Stop before restart failed (expected if not running): %s", stop_exc
            )
        res = s.supervisor.startProcess(name, False)
        return {"ok": bool(res), "action": "restart", "service": name}
    except XMLRPCError as e:
        raise HttpError(502, f"supervisor error: {e}")
    except Exception as e:
        raise HttpError(503, f"cannot reach supervisor: {e}")


# Outbox management
@router.get("/outbox", auth=admin_auth)
def admin_list_outbox(
    request: HttpRequest,
    status: str = "pending",
    tenant: Optional[str] = None,
    topic_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List outbox events with filtering."""
    try:
        events = outbox_db.list_events_by_status(
            status=status.lower().strip(),
            tenant_id=tenant,
            topic_filter=topic_filter,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc))

    if status.lower().strip() == "failed":
        for ev in events:
            tenant_label = (
                (ev.tenant_id or "default") if hasattr(ev, "tenant_id") else "default"
            )
            try:
                M.OUTBOX_FAILED_TOTAL.labels(tenant_id=tenant_label).inc()
            except Exception as metric_exc:
                logger.debug("Failed to record outbox_failed metric: %s", metric_exc)

    return OutboxListResponse(
        events=[OutboxEventModel.model_validate(ev) for ev in events],
        count=len(events),
    )


@router.post("/outbox/replay", auth=admin_auth)
def admin_replay_outbox(request: HttpRequest, body: OutboxReplayRequest):
    """Replay specific outbox events by ID."""
    try:
        count = outbox_db.mark_events_for_replay(body.event_ids)
    except HttpError:
        raise
    except Exception as exc:
        try:
            M.OUTBOX_REPLAY_TRIGGERED.labels(result="error").inc(len(body.event_ids))
        except Exception:
            pass
        raise exc

    if count == 0:
        try:
            M.OUTBOX_REPLAY_TRIGGERED.labels(result="not_found").inc(
                len(body.event_ids)
            )
        except Exception:
            pass
        raise HttpError(404, "No matching events to replay")

    try:
        M.OUTBOX_REPLAY_TRIGGERED.labels(result="success").inc(count)
    except Exception:
        pass
    return OutboxReplayResponse(replayed=count)


# Quota management
@router.get("/quotas", auth=admin_auth)
def admin_list_quotas(
    request: HttpRequest,
    limit: int = 100,
    offset: int = 0,
    tenant_filter: Optional[str] = None,
):
    """List quota status for all tenants."""
    from somabrain.quotas import QuotaConfig, QuotaManager

    try:
        quota_manager = QuotaManager(QuotaConfig())
        all_quotas = quota_manager.get_all_quotas()

        if tenant_filter and isinstance(tenant_filter, str):
            all_quotas = [
                q for q in all_quotas if q.tenant_id.startswith(tenant_filter)
            ]

        total_count = len(all_quotas)
        paginated_quotas = all_quotas[offset : offset + limit]

        quota_statuses = [
            QuotaStatus(
                tenant_id=quota_info.tenant_id,
                daily_limit=quota_info.daily_limit,
                remaining=quota_info.remaining,
                used_today=quota_info.used_today,
                reset_at=quota_info.reset_at,
                is_exempt=quota_info.is_exempt,
            )
            for quota_info in paginated_quotas
        ]

        return QuotaListResponse(quotas=quota_statuses, total_tenants=total_count)

    except Exception as exc:
        logger.error(f"Failed to list quotas: {exc}")
        raise HttpError(500, f"Failed to list quotas: {exc}")


# Feature flags
@router.get("/features", auth=admin_auth)
def admin_features_state(request: HttpRequest) -> FeatureFlagsResponse:
    """Return current feature-flag status."""
    return FeatureFlagsResponse(
        status=FeatureFlags.get_status(), overrides=FeatureFlags.get_overrides()
    )


@router.post("/features", auth=admin_auth)
def admin_features_update(
    request: HttpRequest,
    body: FeatureFlagsUpdateRequest,
) -> FeatureFlagsUpdateResponse:
    """Validate and apply admin feature-flag update."""
    unknown = [f for f in body.disabled if f not in FeatureFlags.KEYS]
    if unknown:
        raise HttpError(400, f"unknown flags: {', '.join(unknown)}")

    if not FeatureFlags.set_overrides(body.disabled):
        raise HttpError(403, "update forbidden")

    return FeatureFlagsUpdateResponse(overrides=FeatureFlags.get_overrides())
