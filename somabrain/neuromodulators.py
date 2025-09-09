"""
Neuromodulators Module for SomaBrain

This module implements a neuromodulatory system that simulates key neurotransmitters
and their effects on cognitive processing. Neuromodulators play crucial roles in
learning, motivation, attention, and adaptive behavior in biological brains.

Key Features:
- Dopamine: Motivation, reward prediction, and error weighting
- Serotonin: Emotional stability and smoothing of neural responses
- Noradrenaline: Urgency, arousal, and gain control
- Acetylcholine: Attention, focus, and memory consolidation
- Publish/subscribe pattern for state changes
- Timestamped state tracking

Neuromodulator Functions:
- Dopamine: Modulates learning rate and motivation (0.2-0.8 range)
- Serotonin: Provides emotional stability and response smoothing (0.0-1.0 range)
- Noradrenaline: Controls urgency and neural gain (0.0-0.1 range)
- Acetylcholine: Enhances attention and focus (0.0-0.1 range)

Integration:
- Affects salience computation in amygdala
- Modulates learning rates in various systems
- Influences decision thresholds in executive control
- Adapts behavior based on internal state and external feedback

Classes:
    NeuromodState: Container for neuromodulator values and timestamp
    Neuromodulators: Publish/subscribe hub for neuromodulator state management

Biological Inspiration:
- Mesolimbic dopamine system for reward and motivation
- Serotonergic system for mood and emotional regulation
- Locus coeruleus noradrenergic system for arousal
- Cholinergic system for attention and memory
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, List


@dataclass
class NeuromodState:
    """
    Represents the neuromodulatory state for cognitive control.

    Attributes
    ----------
    dopamine : float
        Motivation and error weighting [0.2, 0.8].
    serotonin : float
        Smoothing and stability [0.0, 1.0].
    noradrenaline : float
        Urgency/gain [0, 0.1].
    acetylcholine : float
        Focus [0, 0.1].
    timestamp : float
        Time of last update.
    """

    dopamine: float = 0.4
    serotonin: float = 0.5
    noradrenaline: float = 0.0
    acetylcholine: float = 0.0
    timestamp: float = 0.0


class Neuromodulators:
    """
    Publish/subscribe hub for NeuromodState updates.

    Allows components to subscribe to neuromodulator changes for adaptive control.
    """

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
