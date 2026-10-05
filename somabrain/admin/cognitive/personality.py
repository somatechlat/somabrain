"""
Personality store for SomaBrain.

 Maintains per-tenant personality traits that can influence neuromodulation and
 salience. Uses real in-memory storage with no fallback shims and validates via
 the shared `PersonalityState` schema.
"""

from __future__ import annotations

from threading import RLock

from somabrain.schemas import PersonalityState


class PersonalityStore:
    """Personalitystore class implementation."""

    def __init__(self) -> None:
        """Initialize the instance."""

        self._lock = RLock()
        self._states: dict[str, PersonalityState] = {}

    def get(self, tenant: str) -> PersonalityState:
        """Return the personality state for ``tenant``.

        Args:
            tenant: The tenant partition key. Required — this store is keyed by
                tenant and has no ambient tenant context to fall back on.
        """

        if not tenant:
            raise ValueError("tenant is required")
        with self._lock:
            return self._states.setdefault(tenant, PersonalityState())  # validated default

    def set(self, state: PersonalityState, tenant: str) -> PersonalityState:
        """Replace the personality state for ``tenant``.

        Args:
            state: The state.
            tenant: The tenant partition key. Required.
        """

        if not tenant:
            raise ValueError("tenant is required")
        with self._lock:
            # store a copy to avoid external mutation
            self._states[tenant] = PersonalityState(**state.model_dump())
            return self._states[tenant]

    def update_traits(self, traits: dict, tenant: str) -> PersonalityState:
        """Merge provided traits into the tenant personality.

        Args:
            traits: Trait values to merge.
            tenant: The tenant partition key. Required.
        """

        if not tenant:
            raise ValueError("tenant is required")
        with self._lock:
            current = self._states.setdefault(tenant, PersonalityState())
            updated = current.model_copy(update=traits)
            self._states[tenant] = updated
            return updated

    def all(self) -> dict[str, PersonalityState]:
        """Execute all."""

        with self._lock:
            return {k: v.model_copy() for k, v in self._states.items()}
