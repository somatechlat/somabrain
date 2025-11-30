from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from somabrain.auth import require_auth
from somabrain.storage.db import get_session_factory
from somabrain.cognitive.thread_model import CognitiveThread
from common.config.settings import settings
from somabrain import metrics as M

"""FastAPI router for Cognitive Threads (Phase 5).

Provides CRUD‑style endpoints to manage a per‑tenant thread of option IDs.
The thread is persisted via the ``CognitiveThread`` SQLAlchemy model defined in
``thread_model.py``. All endpoints require authentication using the existing
``require_auth`` guard.

Endpoints
~~~~~~~~~
* ``POST /thread`` – create or replace a thread with a list of options.
* ``GET /thread/next`` – retrieve the next option according to the stored
  cursor and advance it.
* ``PUT /thread/reset`` – clear the thread (options and cursor).

Metrics are emitted via ``somabrain.metrics``:
    pass
* ``somabrain_thread_created_total`` – incremented on thread creation.
* ``somabrain_thread_next_total`` – incremented on each ``next`` call.
* ``somabrain_thread_reset_total`` – incremented on reset.
* ``somabrain_thread_active`` – gauge of the current number of stored options
  per tenant.
"""





router = APIRouter()

# Metrics ---------------------------------------------------------------
THREAD_CREATED = M.get_counter(
    "somabrain_thread_created_total",
    "Number of cognitive threads created",
    labelnames=["tenant_id"], )
THREAD_NEXT = M.get_counter(
    "somabrain_thread_next_total",
    "Number of next‑option requests",
    labelnames=["tenant_id"], )
THREAD_RESET = M.get_counter(
    "somabrain_thread_reset_total",
    "Number of thread reset operations",
    labelnames=["tenant_id"], )
THREAD_ACTIVE = M.get_gauge(
    "somabrain_thread_active",
    "Current number of options stored in a thread",
    labelnames=["tenant_id"], )


class ThreadCreateRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    options: List[str] = Field(default_factory=list, description="Option IDs in order")


@router.post("/thread", response_model=dict)
async def create_thread(body: ThreadCreateRequest, request: Request) -> dict:
    """Create or replace a thread for ``tenant_id``.

    The supplied ``options`` list is stored as JSON and the cursor is reset to
    ``0``. If a thread already exists it is overwritten.
    """
    require_auth(request, settings)
    Session = get_session_factory()
    with Session() as session:
        thread = session.get(CognitiveThread, body.tenant_id)
        if thread is None:
            thread = CognitiveThread(tenant_id=body.tenant_id)
            session.add(thread)
        thread.set_options(body.options)
        thread.cursor = 0
        session.commit()
        THREAD_CREATED.labels(tenant_id=body.tenant_id).inc()
        THREAD_ACTIVE.labels(tenant_id=body.tenant_id).set(len(body.options))
    return {"ok": True, "tenant_id": body.tenant_id, "option_count": len(body.options)}


@router.get("/thread/next", response_model=dict)
async def next_option(tenant_id: str, request: Request) -> dict:
    """Return the next option for ``tenant_id`` and advance the cursor.

    If the thread does not exist or is exhausted ``option`` will be ``null``.
    """
    require_auth(request, settings)
    Session = get_session_factory()
    with Session() as session:
        thread = session.get(CognitiveThread, tenant_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        opt = thread.next_option()
        session.commit()
        THREAD_NEXT.labels(tenant_id=tenant_id).inc()
        # Update active gauge to reflect remaining options
        remaining = max(0, len(thread.get_options()) - thread.cursor)
        THREAD_ACTIVE.labels(tenant_id=tenant_id).set(remaining)
    return {"tenant_id": tenant_id, "option": opt}


@router.put("/thread/reset", response_model=dict)
async def reset_thread(tenant_id: str, request: Request) -> dict:
    """Reset (clear) the thread for ``tenant_id``.

    The options list is cleared and the cursor set to ``0``.
    """
    require_auth(request, settings)
    Session = get_session_factory()
    with Session() as session:
        thread = session.get(CognitiveThread, tenant_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        thread.reset()
        session.commit()
        THREAD_RESET.labels(tenant_id=tenant_id).inc()
        THREAD_ACTIVE.labels(tenant_id=tenant_id).set(0)
    return {"ok": True, "tenant_id": tenant_id}
