"""Public runtime exports for lazy singleton access."""

from .manager import (
    Runtime,
    cfg,
    embedder,
    get_embedder,
    get_memory_pool,
    get_working_memory,
    initialize_runtime,
    mt_memory,
    mt_wm,
)
from .modes import SomaBrainMode
from .supervisor import Supervisor

__all__ = [
    "Runtime",
    "Supervisor",
    "SomaBrainMode",
    "cfg",
    "embedder",
    "mt_memory",
    "mt_wm",
    "get_embedder",
    "get_memory_pool",
    "get_working_memory",
    "initialize_runtime",
]
