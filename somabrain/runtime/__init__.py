"""Public runtime exports for lazy singleton access."""

from .manager import (
    Runtime,
    get_embedder,
    get_memory_pool,
    get_working_memory,
    initialize_runtime,
)
from .modes import SomaBrainMode
from .supervisor import Supervisor

__all__ = [
    "Runtime",
    "Supervisor",
    "SomaBrainMode",
    "get_embedder",
    "get_memory_pool",
    "get_working_memory",
    "initialize_runtime",
]
