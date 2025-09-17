from __future__ import annotations

import time
from typing import Any, Dict, Optional


class PersonaStore:
    """
    Persona-backed trait store with a PersonalityStore-compatible surface.

    This is a lightweight adapter that exposes `get`, `set`, and
    `modulate_neuromods` used by existing code paths. It stores runtime
    traits in-process for fast reads but persists persona records using
    the existing `persona` memory contract via MemoryService.
    """

    def __init__(self, mt_memory=None, namespace: Optional[str] = None):
        # mt_memory: Memory pool / client factory (optional runtime injection)
        self._by_tenant: Dict[str, Dict[str, Any]] = {}
        self._mt_memory = mt_memory
        self._namespace = namespace

    def get(self, tenant_id: str) -> Dict[str, Any]:
        """Return traits dict for tenant_id or empty dict.

        Prefer in-memory cache; best-effort hydrate from persona memory if missing.
        """
        t = self._by_tenant.get(tenant_id)
        if t is not None:
            return dict(t)

        # Best-effort hydrate from persistent persona record if memory client supplied
        if self._mt_memory is not None and self._namespace is not None:
            try:
                ms = self._mt_memory.for_namespace(self._namespace)
                # Support both legacy persona key formats written by different writers:
                # - persona:personality:{tenant_id}
                # - persona:{tenant_id}
                keys = [f"persona:personality:{tenant_id}", f"persona:{tenant_id}"]
                for key in keys:
                    coord = ms.coord_for_key(key)
                    hits = ms.payloads_for_coords([coord]) or []
                    for p in reversed(hits):
                        if isinstance(p, dict) and p.get("fact") == "persona":
                            # Accept either traits or properties for compatibility
                            traits = p.get("traits") or p.get("properties") or {}
                            self._by_tenant[tenant_id] = dict(traits)
                            return dict(traits)
            except Exception:
                pass
        return {}

    def set(self, tenant_id: str, traits: Dict[str, Any]) -> None:
        """Store traits in-memory and persist as a persona record (best-effort).

        This method mirrors the semantics of the legacy `PersonalityStore.set`.
        """
        self._by_tenant[tenant_id] = dict(traits or {})
        if self._mt_memory is not None and self._namespace is not None:
            try:
                ms = self._mt_memory.for_namespace(self._namespace)
                payload = {
                    "id": tenant_id,
                    "fact": "persona",
                    "memory_type": "semantic",
                    "traits": dict(traits or {}),
                    "timestamp": time.time(),
                }
                # Persist both key variants to be visible to callers using either format.
                try:
                    ms.remember(f"persona:personality:{tenant_id}", payload)
                except Exception:
                    pass
                try:
                    ms.remember(f"persona:{tenant_id}", payload)
                except Exception:
                    pass
            except Exception:
                # best-effort persistence; do not fail on IO
                pass

    @staticmethod
    def modulate_neuromods(base, traits: Dict[str, Any]):
        # Inline the legacy modulation logic so this adapter is self-contained.
        # Expect `base` to be a NeuromodState-like object with attributes:
        # dopamine, serotonin, noradrenaline, acetylcholine, timestamp
        try:
            cur = float((traits or {}).get("curiosity", 0.0) or 0.0)
            risk = float((traits or {}).get("risk_tolerance", 0.0) or 0.0)
            rew = float((traits or {}).get("reward_seeking", 0.0) or 0.0)
            calm = float((traits or {}).get("calm", 0.0) or 0.0)
            # create a copy preserving timestamp
            s = type(base)(
                dopamine=base.dopamine,
                serotonin=base.serotonin,
                noradrenaline=base.noradrenaline,
                acetylcholine=base.acetylcholine,
                timestamp=getattr(base, "timestamp", None),
            )
            # Curiosity boosts focus (ACh)
            s.acetylcholine = max(0.0, min(0.1, 0.02 + 0.08 * cur))
            # Risk tolerance lowers NE (reduces thresholds)
            s.noradrenaline = max(0.0, min(0.1, 0.05 - 0.05 * risk))
            # Reward seeking boosts dopamine (error weight)
            s.dopamine = max(0.2, min(0.8, 0.4 + 0.3 * rew))
            # Calm (stability) slightly increases serotonin
            s.serotonin = max(0.0, min(1.0, base.serotonin + 0.2 * calm))
            return s
        except Exception:
            # If anything unexpected, return base unchanged
            return base
