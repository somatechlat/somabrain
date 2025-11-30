from __future__ import annotations
from threading import RLock
from typing import Dict
from somabrain.schemas import PersonalityState
from somabrain.tenant_manager import get_tenant_manager

"""
Personality store for SomaBrain.

Maintains per-tenant personality traits that can influence neuromodulation and
salience. Uses real in-memory storage (no stubs) and validates via the shared
`PersonalityState` schema.
"""





class PersonalityStore:
    pass
def __init__(self) -> None:
        self._lock = RLock()
        self._states: Dict[str, PersonalityState] = {}

def get(self, tenant: str | None = None) -> PersonalityState:
        t = tenant or get_tenant_manager().current_tenant()
        with self._lock:
            return self._states.setdefault(t, PersonalityState())  # validated default

def set(
        self, state: PersonalityState, tenant: str | None = None
    ) -> PersonalityState:
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
        with self._lock:
            return {k: v.model_copy() for k, v in self._states.items()}
