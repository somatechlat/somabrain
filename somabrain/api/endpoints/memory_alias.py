"""Legacy BrainBridge path aliases for the memory contract.

CANONICAL paths (use these):

* ``POST /api/memory/remember``
* ``POST /api/memory/recall``
* ``POST /api/memory/forget``

This module only re-exposes the canonical handlers at the legacy BrainBridge
spellings ``/remember``, ``/recall``, ``/forget`` (and therefore also
``/api/remember`` etc. via the dual mount in ``somabrain.config.urls``).
Every function here delegates straight to the one implementation in
``somabrain.api.endpoints.memory`` / ``memory_remember`` — there is no second
write or read path.
"""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from somabrain.api.auth import api_key_auth
from somabrain.api.endpoints.memory import (
    RecallRequest,
    forget_memory,
    recall_memory,
)
from somabrain.api.endpoints.memory_remember import (
    remember_memory_async,
    remember_memory_batch,
)
from somabrain.api.memory.models import (
    ForgetRequest,
    ForgetResponse,
    MemoryBatchWriteRequest,
    MemoryBatchWriteResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
)

router = Router(tags=["memory"])


@router.post("/remember", response=MemoryWriteResponse, auth=api_key_auth)
async def remember_alias(request: HttpRequest, payload: MemoryWriteRequest):
    """Thin alias of ``POST /api/memory/remember``."""
    return await remember_memory_async(request, payload)


@router.post("/remember/batch", response=MemoryBatchWriteResponse, auth=api_key_auth)
async def remember_batch_alias(request: HttpRequest, payload: MemoryBatchWriteRequest):
    """Thin alias of ``POST /api/memory/remember/batch``."""
    return await remember_memory_batch(request, payload)


@router.post("/recall", auth=api_key_auth)
async def recall_alias(request: HttpRequest, payload: RecallRequest):
    """Thin alias of ``POST /api/memory/recall``."""
    return await recall_memory(request, payload)


@router.post("/forget", response=ForgetResponse, auth=api_key_auth)
async def forget_alias(request: HttpRequest, payload: ForgetRequest):
    """Thin alias of ``POST /api/memory/forget``."""
    return await forget_memory(request, payload)
