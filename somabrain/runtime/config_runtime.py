"""Shared configuration runtime primitives for SomaBrain services."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, List, Optional

from somabrain.config import Config
from somabrain.services.config_service import ConfigEvent, ConfigService
from somabrain.services.cutover_controller import CutoverController
from somabrain.services.parameter_supervisor import (
    MetricsSnapshot,
    ParameterSupervisor,
)

_logger = logging.getLogger(__name__)

_config_service = ConfigService(lambda: Config())
_cutover_controller = CutoverController(_config_service)
_event_queue = _config_service.subscribe()
_listeners: List[Callable[[ConfigEvent], Optional[Awaitable[None]]]] = []
_dispatcher_task: Optional[asyncio.Task[None]] = None
_dispatcher_lock = asyncio.Lock()
_supervisor = ParameterSupervisor(_config_service)
_supervisor_queue: asyncio.Queue[MetricsSnapshot] = asyncio.Queue()
_supervisor_task: Optional[asyncio.Task[None]] = None
_supervisor_lock = asyncio.Lock()


def get_config_service() -> ConfigService:
    return _config_service


def get_cutover_controller() -> CutoverController:
    return _cutover_controller


def get_parameter_supervisor() -> ParameterSupervisor:
    return _supervisor


def register_config_listener(
    callback: Callable[[ConfigEvent], Optional[Awaitable[None]]],
) -> None:
    if callback not in _listeners:
        _listeners.append(callback)


async def ensure_config_dispatcher() -> None:
    global _dispatcher_task
    if _dispatcher_task is not None and not _dispatcher_task.done():
        return
    async with _dispatcher_lock:
        if _dispatcher_task is not None and not _dispatcher_task.done():
            return
        loop = asyncio.get_running_loop()
        _dispatcher_task = loop.create_task(_dispatch_events())


async def _dispatch_events() -> None:
    while True:
        event = await _event_queue.get()
        for callback in list(_listeners):
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                _logger.exception("Config listener failed")


async def ensure_supervisor_worker() -> None:
    global _supervisor_task
    if _supervisor_task is not None and not _supervisor_task.done():
        return
    async with _supervisor_lock:
        if _supervisor_task is not None and not _supervisor_task.done():
            return
        loop = asyncio.get_running_loop()
        _supervisor_task = loop.create_task(_run_supervisor())


async def submit_metrics_snapshot(snapshot: MetricsSnapshot) -> None:
    await ensure_supervisor_worker()
    await _supervisor_queue.put(snapshot)


async def _run_supervisor() -> None:
    while True:
        snapshot = await _supervisor_queue.get()
        try:
            await _supervisor.evaluate(snapshot)
        except Exception:
            _logger.exception(
                "ParameterSupervisor evaluation failed for %s/%s",
                snapshot.tenant,
                snapshot.namespace,
            )


__all__ = [
    "get_config_service",
    "get_cutover_controller",
    "register_config_listener",
    "ensure_config_dispatcher",
    "get_parameter_supervisor",
    "submit_metrics_snapshot",
    "ensure_supervisor_worker",
]
