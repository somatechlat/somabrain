"""Cognitive Thread API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Manage per-tenant threads of option IDs.
"""

from __future__ import annotations

import logging
from typing import List

from django.conf import settings
from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain import metrics as M
from somabrain.api.auth import api_key_auth
from somabrain.core.security.legacy_auth import require_auth
from somabrain.apps.core.models import CognitiveThread

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

    tenant_id: str
    options: List[str]


@router.post("/thread", auth=api_key_auth)
def create_thread(request: HttpRequest, body: ThreadCreateRequest):
    """Create or replace a thread for tenant_id."""
    require_auth(request, settings)

    # Update or create
    thread, created = CognitiveThread.objects.update_or_create(
        tenant_id=body.tenant_id, defaults={"cursor": 0, "options": body.options}
    )

    THREAD_CREATED.labels(tenant_id=body.tenant_id).inc()
    THREAD_ACTIVE.labels(tenant_id=body.tenant_id).set(len(body.options))

    return {"ok": True, "tenant_id": body.tenant_id, "option_count": len(body.options)}


@router.get("/thread/next", auth=api_key_auth)
def next_option(request: HttpRequest, tenant_id: str):
    """Return next option and advance cursor."""
    require_auth(request, settings)

    try:
        thread = CognitiveThread.objects.get(tenant_id=tenant_id)
        opt = thread.next_option()
        thread.save()  # Verify if next_option saves or just returns?
        # Check model: likely model method updates state but need to call save() if it doesn't.
        # Assuming model method doesn't save to DB automatically to allow transaction control,
        # but pure Django method might.
        # Logic from legacy: thread.next_option() then session.commit()
        # So we must save.

        THREAD_NEXT.labels(tenant_id=tenant_id).inc()
        # Update active gauge
        opts = (
            thread.get_options() if hasattr(thread, "get_options") else thread.options
        )
        remaining = max(0, len(opts) - thread.cursor)
        THREAD_ACTIVE.labels(tenant_id=tenant_id).set(remaining)

        return {"tenant_id": tenant_id, "option": opt}

    except CognitiveThread.DoesNotExist:
        raise HttpError(404, "Thread not found")
    except Exception as exc:
        raise HttpError(500, str(exc))


@router.put("/thread/reset", auth=api_key_auth)
def reset_thread(request: HttpRequest, tenant_id: str):
    """Reset the thread."""
    require_auth(request, settings)

    try:
        thread = CognitiveThread.objects.get(tenant_id=tenant_id)
        if hasattr(thread, "reset"):
            thread.reset()  # Method on model
        else:
            thread.options = []
            thread.cursor = 0

        thread.save()

        THREAD_RESET.labels(tenant_id=tenant_id).inc()
        THREAD_ACTIVE.labels(tenant_id=tenant_id).set(0)

        return {"ok": True, "tenant_id": tenant_id}

    except CognitiveThread.DoesNotExist:
        raise HttpError(404, "Thread not found")
