from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from .neuromodulators import NeuromodState


@dataclass
class PersonalityStateInMem:
    traits: Dict[str, Any]


class PersonalityStore:
    def __init__(self):
        self._by_tenant: Dict[str, PersonalityStateInMem] = {}

    def get(self, tenant_id: str) -> Dict[str, Any]:
        return dict(self._by_tenant.get(tenant_id, PersonalityStateInMem(traits={})).traits)

    def set(self, tenant_id: str, traits: Dict[str, Any]) -> None:
        self._by_tenant[tenant_id] = PersonalityStateInMem(traits=dict(traits))

    @staticmethod
    def modulate_neuromods(base: NeuromodState, traits: Dict[str, Any]) -> NeuromodState:
        # Copy base
        s = NeuromodState(
            dopamine=base.dopamine,
            serotonin=base.serotonin,
            noradrenaline=base.noradrenaline,
            acetylcholine=base.acetylcholine,
            timestamp=base.timestamp,
        )
        # Curiosity boosts focus (ACh)
        cur = float(traits.get("curiosity", 0.0) or 0.0)
        s.acetylcholine = max(0.0, min(0.1, 0.02 + 0.08 * cur))
        # Risk tolerance lowers NE (reduces thresholds)
        risk = float(traits.get("risk_tolerance", 0.0) or 0.0)
        s.noradrenaline = max(0.0, min(0.1, 0.05 - 0.05 * risk))
        # Reward seeking boosts dopamine (error weight)
        rew = float(traits.get("reward_seeking", 0.0) or 0.0)
        s.dopamine = max(0.2, min(0.8, 0.4 + 0.3 * rew))
        # Calm (stability) slightly increases serotonin (not directly used yet)
        calm = float(traits.get("calm", 0.0) or 0.0)
        s.serotonin = max(0.0, min(1.0, base.serotonin + 0.2 * calm))
        return s

