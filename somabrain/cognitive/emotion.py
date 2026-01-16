"""
Emotion modelling – Phase 3 Cognitive Capability

This module provides a **lightweight emotional state model** that can be
integrated with the autonomous learning loop.  The design follows a simple
*dimensional* approach (valence, arousal, dominance) and exposes a small
public API:

* ``EmotionModel`` – holds the current emotional vector.
* ``update`` – adjusts the vector based on a stimulus (e.g., success/failure
  of a plan, reward signals, external events).
* ``decay`` – slowly drifts the state toward a neutral baseline.
* ``as_dict`` – convenient serialization for logging or persistence.

The implementation is deliberately minimal – it does **not** attempt to
model complex affective dynamics, but it provides a solid foundation for
future research or for tying emotions to neuromodulators in ``somabrain.
neuromodulators``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class EmotionVector:
    """Three‑dimensional affective vector.

    * ``valence`` – positive vs. negative affect (‑1.0 .. 1.0).
    * ``arousal`` – activation level (0.0 .. 1.0).
    * ``dominance`` – sense of control (‑1.0 .. 1.0).
    """

    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def clamp(self) -> None:
        """Clamp each dimension to its allowed range."""
        self.valence = max(min(self.valence, 1.0), -1.0)
        self.arousal = max(min(self.arousal, 1.0), 0.0)
        self.dominance = max(min(self.dominance, 1.0), -1.0)


class EmotionModel:
    """Simple affective state holder.

    The model can be *updated* with a stimulus tuple ``(valence, arousal,
    dominance)``.  Positive values push the state in the indicated direction;
    negative values pull it opposite.  A decay factor slowly returns the
    vector toward neutral (0, 0, 0).
    """

    def __init__(self, decay_rate: float | None = None):
        """Initialize the instance."""

        self.state = EmotionVector()
        # Use Settings default if not explicitly provided
        rate = decay_rate if decay_rate is not None else float(settings.emotion_decay_rate)
        self.decay_rate = max(min(rate, 1.0), 0.0)
        logger.info("EmotionModel initialised with decay_rate=%s", self.decay_rate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, stimulus: Tuple[float, float, float]) -> None:
        """Apply a stimulus to the current emotional vector.

        ``stimulus`` is a ``(valence, arousal, dominance)`` tuple where each
        component is in the range ``[-1.0, 1.0]``.  The method adds the stimulus to
        the current state and then clamps the result.
        """
        v, a, d = stimulus
        logger.debug("Emotion update – before: %s, stimulus: %s", self.state, stimulus)
        self.state.valence += v
        self.state.arousal += a
        self.state.dominance += d
        self.state.clamp()
        logger.debug("Emotion update – after: %s", self.state)

    def decay(self) -> None:
        """Apply exponential decay towards the neutral baseline.

        Each dimension moves a fraction ``self.decay_rate`` of the distance to
        zero.  This mimics the natural fading of affect over time.
        """
        logger.debug("Emotion decay – before: %s", self.state)
        self.state.valence *= 1 - self.decay_rate
        self.state.arousal *= 1 - self.decay_rate
        self.state.dominance *= 1 - self.decay_rate
        # Small values close to zero are snapped to exactly zero for stability.
        if abs(self.state.valence) < 1e-4:
            self.state.valence = 0.0
        if abs(self.state.arousal) < 1e-4:
            self.state.arousal = 0.0
        if abs(self.state.dominance) < 1e-4:
            self.state.dominance = 0.0
        logger.debug("Emotion decay – after: %s", self.state)

    def as_dict(self) -> Dict[str, float]:
        """Return the current state as a serialisable ``dict``."""
        return {
            "valence": self.state.valence,
            "arousal": self.state.arousal,
            "dominance": self.state.dominance,
        }

    # ------------------------------------------------------------------
    # Helper utilities – useful for debugging or logging
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover – trivial
        """Return object representation."""

        return f"EmotionModel(state={self.state}, decay_rate={self.decay_rate})"
