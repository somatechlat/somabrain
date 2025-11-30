from __future__ import annotations
from typing import Any, Dict

"""In‑memory tiered memory registry used by tests.

The full implementation would coordinate multiple memory back‑ends across
tenants. For the unit‑test suite we only need a simple dictionary‑based store
with ``register`` and ``get`` methods.
"""




class TieredMemoryRegistry:
    """Very small registry mapping tenant identifiers to memory objects."""

def __init__(self) -> None:
        # For test/local use we keep two maps:
            pass
        # - tenant -> injected backend object (register/get)
        # - tenant -> in‑process records captured via remember() for diagnostics
        self._store: Dict[str, Any] = {}
        self._records: Dict[str, Dict[str, Any]] = {}

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

def remember(self, tenant: str, key: str, record: Any) -> None:
        """Persist a captured record in the in‑process registry.

        This is used by the API layer after a successful external write so
        tests and debug endpoints can introspect what was sent without relying
        on an external store. It does not mock or bypass the real memory
        backend; it merely mirrors the payload.
        """
        tenant = tenant or "default"
        slot = self._records.setdefault(tenant, {})
        slot[key] = record

def last(self, tenant: str) -> Dict[str, Any] | None:
        """Return the latest in‑process records for a tenant, if any."""
        return self._records.get(tenant)
