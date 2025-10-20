from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List
import time


@dataclass
class NeuromodState:
    dopamine: float = 0.4   # scales error weight [0.2,0.8]
    serotonin: float = 0.5  # smoothing
    noradrenaline: float = 0.0  # urgency/gain [0,0.1]
    acetylcholine: float = 0.0  # focus [0,0.1]
    timestamp: float = 0.0


class Neuromodulators:
    def __init__(self):
        self._state = NeuromodState(timestamp=time.time())
        self._subs: List[Callable[[NeuromodState], None]] = []

    def get_state(self) -> NeuromodState:
        return self._state

    def set_state(self, s: NeuromodState) -> None:
        self._state = s
        for cb in self._subs:
            try:
                cb(s)
            except Exception:
                pass

    def subscribe(self, cb: Callable[[NeuromodState], None]) -> None:
        self._subs.append(cb)

