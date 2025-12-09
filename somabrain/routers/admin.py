"""Admin Router
==============

Admin endpoints for service management, outbox operations, and quota management.
All endpoints require admin authentication.

Endpoints:
- /admin/services - Supervisor service management
- /admin/outbox - Outbox event management
- /admin/quotas - Tenant quota management
- /admin/features - Feature flag management
"""

from __future__ import annotations

import inspect
import logging
from typing import Optional
from xmlrpc.client import Error as XMLRPCError, ServerProxy

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from common.config.settings import settings
from somabrain import metrics as M, schemas as S
from somabrain.auth import require_admin_auth
from somabrain.db import outbox as outbox_db
from config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Supervisor client
# ---------------------------------------------------------------------------

def _get_supervisor_url() -> str:
    """Get the supervisor XML-RPC URL from settings."""
    url = settings.supervisor_url or None
    if not url:
        user = settings.supervisor_http_user
        pwd = settings.supervisor_http_pass
        url = f"http://{user}:{pwd}@somabrain_cog:9001/RPC2"
    return url


def _supervisor() -> ServerProxy:
    """Create a supervisor XML-RPC client."""
    try:
        return ServerProxy(_get_supervisor_url(), allow_none=True)
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"supervisor client init failed: {e}"
        )


def _admin_guard_dep(request: Request):
    """FastAPI dependency wrapper for admin auth."""
    return require_admin_auth(request, settings)


# ---------------------------------------------------------------------------
# Service management endpoints
# ---------------------------------------------------------------------------

@router.get("/services", dependencies=[Depends(_admin_guard_dep)])
async def list_services():
    """List all supervisor-managed services."""
    try:
        s = _supervisor()
        info = s.supervisor.getAllProcessInfo()
        return {"ok": True, "services": info}
    except XMLRPCError as e:
        raise HTTPException(status_code=502, detail=f"supervisor error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cannot reach supervisor: {e}")


@router.get("/services/{name}", dependencies=[Depends(_admin_guard_dep)])
async def service_status(name: str):
    """Get status of a specific service."""
    try:
        s = _supervisor()
        info = s.supervisor.getProcessInfo(name)
        return {"ok": True, "service": info}
    except XMLRPCError as e:
        raise HTTPException(status_code=502, detail=f"supervisor error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cannot reach supervisor: {e}")


@router.post("/services/{name}/start", dependencies=[Depends(_admin_guard_dep)])
async def service_start(name: str):
    """Start a service."""
    try:
        s = _supervisor()
        res = s.supervisor.startProcess(name, False)
        return {"ok": bool(res), "action": "start", "service": name}
    except XMLRPCError as e:
        raise HTTPException(status_code=502, detail=f"supervisor error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cannot reach supervisor: {e}")


@router.post("/services/{name}/stop", dependencies=[Depends(_admin_guard_dep)])
async def service_stop(name: str):
    """Stop a service."""
    try:
        s = _supervisor()
        res = s.supervisor.stopProcess(name, False)
        return {"ok": bool(res), "action": "stop", "service": name}
    except XMLRPCError as e:
        raise HTTPException(status_code=502, detail=f"supervisor error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cannot reach supervisor: {e}")


@router.post("/services/{name}/restart", dependencies=[Depends(_admin_guard_dep)])
async def service_restart(name: str):
    """Restart a service."""
    try:
        s = _supervisor()
        try:
            s.supervisor.stopProcess(name, False)
        except Exception:
            pass
        res = s.supervisor.startProcess(name, False)
        return {"ok": bool(res), "action": "restart", "service": name}
    except XMLRPCError as e:
        raise HTTPException(status_code=502, detail=f"supervisor error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"cannot reach supervisor: {e}")


# ---------------------------------------------------------------------------
# Outbox management endpoints
# ---------------------------------------------------------------------------

@router.get("/outbox", dependencies=[Depends(_admin_guard_dep)])
async def admin_list_outbox(
    status: str = Query("pending", description="pending|failed|sent"),
    tenant: Optional[str] = Query(None),
    topic_filter: Optional[str] = Query(None, description="Filter by topic pattern"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List outbox events with enhanced filtering options."""
    try:
        events = outbox_db.list_events_by_status(
            status=status.lower().strip(),
            tenant_id=tenant,
            topic_filter=topic_filter,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if status.lower().strip() == "failed":
        for ev in events:
            tenant_label = (
                (ev.tenant_id or "default") if hasattr(ev, "tenant_id") else "default"
            )
            try:
                M.OUTBOX_FAILED_TOTAL.labels(tenant_id=tenant_label).inc()
            except Exception:
                pass

    return S.OutboxListResponse(
        events=[S.OutboxEventModel.model_validate(ev) for ev in events],
        count=len(events),
    )


@router.post("/outbox/replay", dependencies=[Depends(_admin_guard_dep)])
async def admin_replay_outbox(body: S.OutboxReplayRequest):
    """Replay specific outbox events by ID."""
    try:
        count = outbox_db.mark_events_for_replay(body.event_ids)
    except HTTPException:
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
        raise HTTPException(status_code=404, detail="No matching events to replay")
    try:
        M.OUTBOX_REPLAY_TRIGGERED.labels(result="success").inc(count)
    except Exception:
        pass
    return S.OutboxReplayResponse(replayed=count)


@router.post("/outbox/replay/tenant", dependencies=[Depends(_admin_guard_dep)])
async def admin_replay_tenant_outbox(body: S.OutboxTenantReplayRequest):
    """Replay outbox events for a specific tenant with filtering options."""
    try:
        count = outbox_db.mark_tenant_events_for_replay(
            tenant_id=body.tenant_id,
            status=body.status,
            topic_filter=body.topic_filter,
            before_timestamp=body.before_timestamp,
            limit=body.limit,
        )
    except HTTPException:
        raise
    except Exception as exc:
        try:
            M.OUTBOX_REPLAY_TRIGGERED.labels(result="tenant_error").inc()
        except Exception:
            pass
        raise exc
    if count == 0:
        try:
            M.OUTBOX_REPLAY_TRIGGERED.labels(result="tenant_not_found").inc()
        except Exception:
            pass
        raise HTTPException(
            status_code=404,
            detail=f"No matching events to replay for tenant '{body.tenant_id}'",
        )
    try:
        M.OUTBOX_REPLAY_TRIGGERED.labels(result="tenant_success").inc(count)
        tenant_label = body.tenant_id or "default"
        try:
            M.report_outbox_replayed(tenant_label, count)
        except Exception:
            pass
    except Exception:
        pass
    return S.OutboxTenantReplayResponse(
        tenant_id=body.tenant_id, replayed=count, status=body.status
    )


@router.get("/outbox/tenant/{tenant_id}", dependencies=[Depends(_admin_guard_dep)])
async def admin_get_tenant_outbox(
    tenant_id: str,
    status: str = Query("pending", description="pending|failed|sent"),
    topic_filter: Optional[str] = Query(None, description="Filter by topic pattern"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get outbox events for a specific tenant with filtering options."""
    try:
        events = outbox_db.list_tenant_events(
            tenant_id=tenant_id,
            status=status.lower().strip(),
            topic_filter=topic_filter,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if status.lower().strip() == "failed":
        tenant_label = tenant_id or "default"
        try:
            M.OUTBOX_FAILED_TOTAL.labels(tenant_id=tenant_label).inc(len(events))
        except Exception:
            pass

    return S.OutboxTenantListResponse(
        tenant_id=tenant_id,
        events=[S.OutboxEventModel.model_validate(ev) for ev in events],
        count=len(events),
        status=status,
    )


@router.get("/outbox/summary", dependencies=[Depends(_admin_guard_dep)])
async def admin_get_outbox_summary():
    """Get summary statistics for outbox events across all tenants."""
    try:
        from somabrain.db.outbox import get_pending_counts_by_tenant

        pending_counts = get_pending_counts_by_tenant()
        failed_counts = outbox_db.get_failed_counts_by_tenant()
        sent_counts = outbox_db.get_sent_counts_by_tenant()

        tenant_summaries = []
        all_tenants = (
            set(pending_counts.keys())
            | set(failed_counts.keys())
            | set(sent_counts.keys())
        )

        for tenant in sorted(all_tenants):
            tenant_label = tenant or "default"
            summary = S.OutboxTenantSummary(
                tenant_id=tenant_label,
                pending_count=pending_counts.get(tenant, 0),
                failed_count=failed_counts.get(tenant, 0),
                sent_count=sent_counts.get(tenant, 0),
                total_count=(
                    pending_counts.get(tenant, 0)
                    + failed_counts.get(tenant, 0)
                    + sent_counts.get(tenant, 0)
                ),
            )
            tenant_summaries.append(summary)

        return S.OutboxSummaryResponse(
            tenants=tenant_summaries,
            total_tenants=len(tenant_summaries),
            total_pending=sum(pending_counts.values()),
            total_failed=sum(failed_counts.values()),
            total_sent=sum(sent_counts.values()),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get outbox summary: {exc}"
        )


# ---------------------------------------------------------------------------
# Quota management endpoints
# ---------------------------------------------------------------------------

@router.get("/quotas", dependencies=[Depends(_admin_guard_dep)])
async def admin_list_quotas(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant_filter: Optional[str] = Query(
        None, description="Filter by tenant ID prefix"
    ),
):
    """List quota status for all tenants."""
    from somabrain.quotas import QuotaManager, QuotaConfig

    try:
        quota_manager = QuotaManager(QuotaConfig())

        all_quotas = quota_manager.get_all_quotas()
        if inspect.isawaitable(all_quotas):
            all_quotas = await all_quotas

        if tenant_filter and isinstance(tenant_filter, str):
            all_quotas = [
                q for q in all_quotas if q.tenant_id.startswith(tenant_filter)
            ]

        total_count = len(all_quotas)
        paginated_quotas = all_quotas[offset : offset + limit]

        quota_statuses = []
        for quota_info in paginated_quotas:
            quota_statuses.append(
                S.QuotaStatus(
                    tenant_id=quota_info.tenant_id,
                    daily_limit=quota_info.daily_limit,
                    remaining=quota_info.remaining,
                    used_today=quota_info.used_today,
                    reset_at=quota_info.reset_at,
                    is_exempt=quota_info.is_exempt,
                )
            )

        return S.QuotaListResponse(quotas=quota_statuses, total_tenants=total_count)

    except Exception as exc:
        logger.error(f"Failed to list quotas: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to list quotas: {exc}")


@router.post("/quotas/{tenant_id}/reset", dependencies=[Depends(_admin_guard_dep)])
async def admin_reset_quota(
    tenant_id: str,
    body: S.QuotaResetRequest,
    request: Request = None,
):
    """Reset quota for a specific tenant."""
    from somabrain.quotas import QuotaManager, QuotaConfig

    try:
        quota_manager = QuotaManager(QuotaConfig())

        tenant_exists = quota_manager.tenant_exists(tenant_id)
        if inspect.isawaitable(tenant_exists):
            tenant_exists = await tenant_exists
        if not tenant_exists:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        old_rem = quota_manager.remaining(tenant_id)
        if inspect.isawaitable(old_rem):
            await old_rem
        reset_res = quota_manager.reset_quota(tenant_id)
        if inspect.isawaitable(reset_res):
            await reset_res
        new_rem = quota_manager.remaining(tenant_id)
        new_remaining = await new_rem if inspect.isawaitable(new_rem) else new_rem

        logger.info(
            f"Admin reset quota for tenant {tenant_id}. Reason: {body.reason or 'Not specified'}"
        )

        try:
            M.QUOTA_RESETS.labels(tenant_id=tenant_id).inc()
        except Exception:
            pass

        return S.QuotaResetResponse(
            tenant_id=tenant_id,
            reset=True,
            new_remaining=new_remaining,
            message=f"Quota reset for tenant {tenant_id}. Remaining: {new_remaining}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to reset quota for tenant {tenant_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to reset quota: {exc}")


@router.post("/quotas/{tenant_id}/adjust", dependencies=[Depends(_admin_guard_dep)])
async def admin_adjust_quota(
    tenant_id: str,
    body: S.QuotaAdjustRequest,
    request: Request = None,
):
    """Adjust quota limit for a specific tenant."""
    from somabrain.quotas import QuotaManager, QuotaConfig

    try:
        quota_manager = QuotaManager(QuotaConfig())

        tenant_exists = quota_manager.tenant_exists(tenant_id)
        if inspect.isawaitable(tenant_exists):
            tenant_exists = await tenant_exists
        if not tenant_exists:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

        current_info = quota_manager.get_quota_info(tenant_id)
        if inspect.isawaitable(current_info):
            current_info = await current_info
        old_limit = current_info.daily_limit

        adj = quota_manager.adjust_quota_limit(tenant_id, body.new_limit)
        if inspect.isawaitable(adj):
            await adj

        new_info = quota_manager.get_quota_info(tenant_id)
        if inspect.isawaitable(new_info):
            new_info = await new_info

        logger.info(
            f"Admin adjusted quota for tenant {tenant_id}: {old_limit} -> {body.new_limit}. "
            f"Reason: {body.reason or 'Not specified'}"
        )

        try:
            M.QUOTA_ADJUSTMENTS.labels(tenant_id=tenant_id).inc()
        except Exception:
            pass

        return S.QuotaAdjustResponse(
            tenant_id=tenant_id,
            old_limit=old_limit,
            new_limit=body.new_limit,
            adjusted=True,
            message=f"Quota limit adjusted for tenant {tenant_id}: {old_limit} -> {body.new_limit}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to adjust quota for tenant {tenant_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to adjust quota: {exc}")


# ---------------------------------------------------------------------------
# Feature flags endpoints
# ---------------------------------------------------------------------------

@router.get("/features", dependencies=[Depends(_admin_guard_dep)])
async def admin_features_state() -> S.FeatureFlagsResponse:
    """Return the current feature-flag status and any persisted overrides."""
    return S.FeatureFlagsResponse(
        status=FeatureFlags.get_status(), overrides=FeatureFlags.get_overrides()
    )


@router.post("/features", dependencies=[Depends(_admin_guard_dep)])
async def admin_features_update(
    body: S.FeatureFlagsUpdateRequest,
) -> S.FeatureFlagsUpdateResponse:
    """Validate and apply an admin feature-flag update."""
    unknown = [f for f in body.disabled if f not in FeatureFlags.KEYS]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"unknown flags: {', '.join(unknown)}"
        )

    if not FeatureFlags.set_overrides(body.disabled):
        raise HTTPException(status_code=403, detail="update forbidden")

    return S.FeatureFlagsUpdateResponse(overrides=FeatureFlags.get_overrides())
