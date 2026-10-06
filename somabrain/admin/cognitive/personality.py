"""Personality store for SomaBrain.

Maintains per-tenant personality traits. **Behavioural** traits are the
keys that name a neuromodulator (``dopamine``, ``serotonin``,
``noradrenaline``, ``acetylcholine`` and their short aliases). Those bias
the corresponding modulator through a homeostatic blend (see
SOMA-BR-MATH-TRUTH-001 T83):

    m'_i = Π_i( (1 − w) · m_i + w · Π_i(trait_i) )

with fixed blend weight ``PERSONALITY_BLEND``. Unmapped trait keys are
**identity metadata only** — they are stored and returned, and have no
effect on neuromodulators, salience, or gates. No behavioural claim is
made for them.

Uses real in-memory storage with no fallback shims and validates via the
shared `PersonalityState` schema.
"""

from __future__ import annotations

import math
from threading import RLock

from somabrain.math.contracts import NEURO_BOUNDS
from somabrain.schemas import PersonalityState

#: Fixed blend weight w in the trait→neuromodulator law (T83).
PERSONALITY_BLEND: float = 0.3

#: Trait keys that name a neuromodulator. Values are projected into that
#: modulator's bounds before blending. Unmapped keys are identity metadata.
TRAIT_TO_NEUROMOD: dict[str, str] = {
    "dopamine": "dopamine",
    "da": "dopamine",
    "serotonin": "serotonin",
    "5ht": "serotonin",
    "5-ht": "serotonin",
    "noradrenaline": "noradrenaline",
    "norepinephrine": "noradrenaline",
    "ne": "noradrenaline",
    "acetylcholine": "acetylcholine",
    "ach": "acetylcholine",
}


def _project_neuromod(name: str, value: float) -> float:
    """Project ``value`` into ``NEURO_BOUNDS[name]``; non-finite → lower bound."""
    lo, hi = NEURO_BOUNDS[name]
    v = float(value)
    if not math.isfinite(v):
        v = float(lo)
    return max(float(lo), min(float(hi), v))


class PersonalityStore:
    """Per-tenant personality traits with neuromodulator biasing."""

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
            state = self._states.setdefault(tenant, PersonalityState())
            # Return a deep copy — callers must not mutate the live store object.
            return state.model_copy(deep=True)

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
            return self._states[tenant].model_copy(deep=True)

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
            merged = dict(current.traits)
            merged.update({str(k): float(v) for k, v in traits.items()})
            updated = current.model_copy(update={"traits": merged})
            self._states[tenant] = updated
            return updated.model_copy(deep=True)

    def modulate_neuromods(self, base, traits: PersonalityState | None):
        """Blend personality traits into a neuromodulator state (T83).

        For each mapped trait key present on ``traits``:

            m'_i = Π_i( (1 − w) · m_i + w · Π_i(trait_i) )

        where ``w = PERSONALITY_BLEND`` and Π is the ``NEURO_BOUNDS``
        projection. Unmapped keys are ignored (identity metadata). Returns a
        new state; ``base`` is not mutated.
        """
        from somabrain.runtime.neuromodulators import NeuromodState

        if traits is None:
            return base
        raw = traits.traits if isinstance(traits, PersonalityState) else dict(traits or {})
        w = float(PERSONALITY_BLEND)
        if not math.isfinite(w) or not (0.0 <= w <= 1.0):
            w = 0.3
        updates: dict[str, float] = {}
        for key, value in raw.items():
            target = TRAIT_TO_NEUROMOD.get(str(key).strip().lower())
            if target is None:
                continue
            trait_val = _project_neuromod(target, value)
            current = float(getattr(base, target))
            blended = (1.0 - w) * current + w * trait_val
            updates[target] = _project_neuromod(target, blended)
        if not updates:
            return base
        data = {
            "dopamine": base.dopamine,
            "serotonin": base.serotonin,
            "noradrenaline": base.noradrenaline,
            "acetylcholine": base.acetylcholine,
        }
        data.update(updates)
        return NeuromodState(**data)

    def all(self) -> dict[str, PersonalityState]:
        """Execute all."""

        with self._lock:
            return {k: v.model_copy(deep=True) for k, v in self._states.items()}
