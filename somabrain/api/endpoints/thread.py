"""Cognitive Thread API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Manage per-tenant threads of option IDs.

Tenant authority: the tenant partition is resolved exclusively from the
authenticated request context (``get_tenant_sync``). A body or query
``tenant_id`` is never trusted — it is accepted only as an assertion that
must match the authenticated tenant, and any mismatch is rejected.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain import metrics as M
from somabrain.admin.core.models import CognitiveThread
from somabrain.api.auth import api_key_auth, require_auth
from somabrain.tenant import get_tenant_sync

logger = logging.getLogger("somabrain.api.endpoints.thread")

router = Router(tags=["thread"])

# Metrics
THREAD_CREATED = M.get_counter(
    "somabrain_thread_created_total",
    "Number of cognitive threads created",
    labelnames=["tenant_id"],
)
THREAD_NEXT = M.get_counter(
    "somabrain_thread_next_total",
    "Number of next-option requests",
    labelnames=["tenant_id"],
)
THREAD_RESET = M.get_counter(
    "somabrain_thread_reset_total",
    "Number of thread reset operations",
    labelnames=["tenant_id"],
)
THREAD_ACTIVE = M.get_gauge(
    "somabrain_thread_active",
    "Current number of options stored in a thread",
    labelnames=["tenant_id"],
)


class ThreadCreateRequest(Schema):
    """Data model for ThreadCreateRequest."""

    options: list[str]
    # Optional tenant assertion — must match the authenticated tenant when
    # present. Never used as the authority for which partition is written.
    tenant_id: str | None = None


def _resolve_tenant(request: HttpRequest, asserted: str | None = None) -> str:
    """Resolve the tenant partition from the authenticated context.

    A body/query tenant is treated as an assertion: if provided and it does
    not match the authenticated tenant, the request is rejected. The
    authenticated context is always the sole authority.
    """
    require_auth(request, settings)
    ctx = get_tenant_sync(request, getattr(settings, "SOMABRAIN_NAMESPACE"))
    if asserted is not None and asserted != ctx.tenant_id:
        raise HttpError(403, "tenant mismatch: asserted tenant does not match authenticated tenant")
    return ctx.tenant_id


@router.post("/thread", auth=api_key_auth)
def create_thread(request: HttpRequest, body: ThreadCreateRequest):
    """Create or replace a thread for the authenticated tenant."""
    tenant_id = _resolve_tenant(request, body.tenant_id)

    # Update or create
    thread, created = CognitiveThread.objects.update_or_create(
        tenant_id=tenant_id, defaults={"cursor": 0, "options": body.options}
    )

    THREAD_CREATED.labels(tenant_id=tenant_id).inc()
    THREAD_ACTIVE.labels(tenant_id=tenant_id).set(len(body.options))

    return {"ok": True, "tenant_id": tenant_id, "option_count": len(body.options)}


@router.get("/thread/next", auth=api_key_auth)
def next_option(request: HttpRequest, tenant_id: str | None = None):
    """Return next option and advance cursor for the authenticated tenant."""
    resolved_tenant = _resolve_tenant(request, tenant_id)

    try:
        thread = CognitiveThread.objects.get(tenant_id=resolved_tenant)
        opt = thread.next_option()
        thread.save()

        THREAD_NEXT.labels(tenant_id=resolved_tenant).inc()
        opts = (
            thread.get_options() if hasattr(thread, "get_options") else thread.options
        )
        remaining = max(0, len(opts) - thread.cursor)
        THREAD_ACTIVE.labels(tenant_id=resolved_tenant).set(remaining)

        return {"tenant_id": resolved_tenant, "option": opt}

    except CognitiveThread.DoesNotExist:
        raise HttpError(404, "Thread not found")
    except HttpError:
        raise
    except Exception as exc:
        raise HttpError(500, str(exc))


@router.put("/thread/reset", auth=api_key_auth)
def reset_thread(request: HttpRequest, tenant_id: str | None = None):
    """Reset the thread for the authenticated tenant."""
    resolved_tenant = _resolve_tenant(request, tenant_id)

    try:
        thread = CognitiveThread.objects.get(tenant_id=resolved_tenant)
        if hasattr(thread, "reset"):
            thread.reset()
        else:
            thread.options = []
            thread.cursor = 0

        thread.save()

        THREAD_RESET.labels(tenant_id=resolved_tenant).inc()
        THREAD_ACTIVE.labels(tenant_id=resolved_tenant).set(0)

        return {"ok": True, "tenant_id": resolved_tenant}

    except CognitiveThread.DoesNotExist:
        raise HttpError(404, "Thread not found")
    except HttpError:
        raise
