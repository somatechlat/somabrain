from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PolicyDecision:
    store: bool
    act: bool


class BasalGangliaPolicy:
    def decide(self, store_gate: bool, act_gate: bool) -> PolicyDecision:
        return PolicyDecision(store=bool(store_gate), act=bool(act_gate))

