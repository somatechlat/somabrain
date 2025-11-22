"""In‑memory tiered memory registry used by tests.

The full implementation would coordinate multiple memory back‑ends across
tenants. For the unit‑test suite we only need a simple dictionary‑based store
with ``register`` and ``get`` methods.
"""

from __future__ import annotations

from typing import Any, Dict


class TieredMemoryRegistry:
    """Very small registry mapping tenant identifiers to memory objects."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def register(self, tenant: str, memory_obj: Any) -> None:
        """Register *memory_obj* for *tenant*.

        Overwrites any existing entry for the tenant.
        """
        self._store[tenant] = memory_obj

    def get(self, tenant: str) -> Any:
        """Retrieve the memory object for *tenant*.

        Raises ``KeyError`` if the tenant is not registered.
        """
        return self._store[tenant]
