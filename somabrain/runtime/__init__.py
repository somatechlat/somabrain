"""Public runtime exports for lazy singleton access."""

from typing import Any

from somabrain.runtime import manager
from somabrain.runtime.manager import (
    Runtime,
    RuntimeManager,
    get_embedder,
    get_memory_pool,
    get_working_memory,
    initialize_runtime,
)
from somabrain.runtime.modes import SomaBrainMode
from somabrain.runtime.supervisor import Supervisor

__all__ = [
    "Runtime",
    "RuntimeManager",
    "SomaBrainMode",
    "Supervisor",
    "cfg",
    "embedder",
    "get_embedder",
    "get_memory_pool",
    "get_working_memory",
    "initialize_runtime",
    "mt_memory",
    "mt_wm",
]


def __getattr__(name: str) -> Any:
    """Lazy proxy for legacy module-level singletons."""
    if name in ("cfg", "embedder", "mt_memory", "mt_wm"):
        return getattr(manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
