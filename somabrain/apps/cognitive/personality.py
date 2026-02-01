"""
Personality store for SomaBrain.

 Maintains per-tenant personality traits that can influence neuromodulation and
 salience. Uses real in-memory storage with no fallback shims and validates via
 the shared `PersonalityState` schema.
"""

from __future__ import annotations

from threading import RLock
from typing import Dict

from somabrain.schemas import PersonalityState
from somabrain.apps.aaas.logic.tenant_manager import get_tenant_manager


class PersonalityStore:
    """Personalitystore class implementation."""

    def __init__(self) -> None:
        """Initialize the instance."""

        self._lock = RLock()
        self._states: Dict[str, PersonalityState] = {}

    def get(self, tenant: str | None = None) -> PersonalityState:
        """Execute get.

        Args:
            tenant: The tenant.
        """

        t = tenant or get_tenant_manager().current_tenant()
        with self._lock:
            return self._states.setdefault(t, PersonalityState())  # validated default

    def set(
        self, state: PersonalityState, tenant: str | None = None
    ) -> PersonalityState:
        """Execute set.

        Args:
            state: The state.
            tenant: The tenant.
        """

        t = tenant or get_tenant_manager().current_tenant()
        with self._lock:
            # store a copy to avoid external mutation
            self._states[t] = PersonalityState(**state.model_dump())
            return self._states[t]

    def update_traits(
        self, traits: dict, tenant: str | None = None
    ) -> PersonalityState:
        """Merge provided traits into the tenant personality."""
        t = tenant or get_tenant_manager().current_tenant()
        with self._lock:
            current = self._states.setdefault(t, PersonalityState())
            updated = current.model_copy(update=traits)
            self._states[t] = updated
            return updated

    def all(self) -> Dict[str, PersonalityState]:
        """Execute all."""

        with self._lock:
            return {k: v.model_copy() for k, v in self._states.items()}
