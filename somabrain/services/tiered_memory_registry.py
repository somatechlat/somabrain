"""In‑memory tiered memory registry used by tests.

The full implementation would coordinate multiple memory back‑ends across
tenants. For the unit‑test suite we only need a simple dictionary‑based store
with ``register`` and ``get`` methods.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np


class TieredMemoryRegistry:
    """Very small registry mapping tenant identifiers to memory objects."""

    def __init__(self) -> None:
        # For test/local use we keep two maps:
        # - tenant -> injected backend object (register/get)
        # - tenant -> in‑process records captured via remember() for diagnostics
        """Initialize the instance."""

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

    def remember(
        self,
        tenant: str,
        namespace: Optional[str] = None,
        *,
        anchor_id: Optional[str] = None,
        key_vector: Optional[np.ndarray] = None,
        value_vector: Optional[np.ndarray] = None,
        payload: Optional[Dict[str, Any]] = None,
        coordinate: Optional[List[Any]] = None,
    ) -> None:
        """Persist a captured record in the in‑process registry.

        This is used by the API layer after a successful external write so
        tests and debug endpoints can introspect what was sent without relying
        on an external store. It mirrors the payload without bypassing the real
        memory backend.

        Args:
            tenant: Tenant identifier
            namespace: Optional namespace within the tenant
            anchor_id: Unique identifier for the memory record
            key_vector: Embedding vector for the key
            value_vector: Embedding vector for the value
            payload: The full memory payload
            coordinate: Storage coordinate from the backend
        """
        tenant = tenant or "default"
        key = anchor_id or "unknown"
        slot = self._records.setdefault(tenant, {})
        slot[key] = {
            "namespace": namespace,
            "anchor_id": anchor_id,
            "payload": payload,
            "coordinate": coordinate,
            "has_key_vector": key_vector is not None,
            "has_value_vector": value_vector is not None,
        }

    def last(self, tenant: str) -> Dict[str, Any] | None:
        """Return the latest in‑process records for a tenant, if any."""
        return self._records.get(tenant)

    def rebuild(self, tenant: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Rebuild ANN indexes for a tenant/namespace.

        This is a no-op in the in-memory implementation.
        Returns metadata about the rebuild operation.
        """
        return {
            "tenant": tenant,
            "namespace": namespace,
            "rebuilt": True,
            "records_count": len(self._records.get(tenant, {})),
        }

    def apply_effective_config(self, event: Any) -> Optional[Dict[str, Any]]:
        """Apply configuration event to the registry.

        Returns metrics if applicable, None otherwise.
        """
        # No-op for in-memory implementation
        return None