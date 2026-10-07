"""Emotion model – valence / arousal / dominance (VAD) affective state.

This module holds a lightweight dimensional affective vector and the
**real couplings** of that vector into the cognitive step (see
SOMA-BR-MATH-TRUTH-001 T82). VAD is not an orphan state: it is wired into
salience, soft-gate temperature, and gate thresholds on ``POST /cognitive/act``.

Couplings (evaluated in ``eval_step`` and applied by ``AmygdalaSalience``):

* **Arousal** raises salience and sharpens soft gates:
  ``s ← s + w_arousal · arousal`` and ``T ← T · 1/(1 + arousal)``.
* **Valence** shifts salience (positive affect amplifies):
  ``s ← s + w_valence · max(0, valence)``.
* **Dominance** lowers gate thresholds (agency → more action):
  ``th ← th − w_dominance · dominance``.

The VAD state is updated each step from the step's own signals
(``valence = 1 − 2·pred_error``, ``arousal = novelty``,
``dominance = 1 − pred_error``), then optionally decayed toward neutral.

This module does **not** implement free-energy minimisation; that lives in
``somabrain.runtime.supervisor.Supervisor`` only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)

#: Default salience weight on arousal (emotional activation amplifies salience).
AROUSAL_SALIENCE_WEIGHT: float = 0.2
#: Default salience weight on non-negative valence.
VALENCE_SALIENCE_WEIGHT: float = 0.1
#: Default gate-threshold reduction per unit dominance.
DOMINANCE_THRESHOLD_WEIGHT: float = 0.1


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


def affect_salience_boost(
    state: EmotionVector,
    *,
    w_arousal: float = AROUSAL_SALIENCE_WEIGHT,
    w_valence: float = VALENCE_SALIENCE_WEIGHT,
) -> float:
    """Salience contribution from VAD: ``w_a·arousal + w_v·max(0, valence)``."""
    arousal = max(0.0, min(1.0, float(state.arousal)))
    valence = max(0.0, float(state.valence))
    return float(w_arousal) * arousal + float(w_valence) * valence


def affect_temperature_scale(state: EmotionVector) -> float:
    """Soft-gate temperature scale from arousal: ``1 / (1 + arousal)``.

    Higher arousal → smaller scale → sharper (more decisive) soft gates.
    Always in (0, 1].
    """
    arousal = max(0.0, min(1.0, float(state.arousal)))
    return 1.0 / (1.0 + arousal)


def affect_threshold_offset(
    state: EmotionVector,
    *,
    w_dominance: float = DOMINANCE_THRESHOLD_WEIGHT,
) -> float:
    """Gate-threshold offset from dominance: ``−w_d · dominance``.

    Positive dominance lowers thresholds (more agency → more action).
    """
    dominance = max(-1.0, min(1.0, float(state.dominance)))
    return -float(w_dominance) * dominance


def stimulus_from_signals(novelty: float, pred_error: float) -> tuple[float, float, float]:
    """Map step signals to a VAD stimulus tuple.

    ``valence = 1 − 2·pred_error`` (error → negative affect),
    ``arousal = novelty`` (novel input activates),
    ``dominance = 1 − pred_error`` (confident prediction → control).
    Inputs are clamped to [0, 1] first.
    """
    err = max(0.0, min(1.0, float(pred_error)))
    nov = max(0.0, min(1.0, float(novelty)))
    return (1.0 - 2.0 * err, nov, 1.0 - err)


class EmotionModel:
    """Simple affective state holder with real VAD couplings.

    The model can be *updated* with a stimulus tuple ``(valence, arousal,
    dominance)``.  Positive values push the state in the indicated direction;
    negative values pull it opposite.  A decay factor slowly returns the
    vector toward neutral (0, 0, 0).  Coupling helpers above turn the state
    into salience / temperature / threshold modifiers for the amygdala.
    """

    def __init__(self, decay_rate: float | None = None):
        """Initialize the instance."""

        self.state = EmotionVector()
        # Use Settings default if not explicitly provided
        rate = (
            decay_rate
            if decay_rate is not None
            else float(settings.SOMABRAIN_EMOTION_DECAY_RATE)
        )
        self.decay_rate = max(min(rate, 1.0), 0.0)
        logger.info("EmotionModel initialised with decay_rate=%s", self.decay_rate)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, stimulus: tuple[float, float, float]) -> None:
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

    def update_from_signals(self, novelty: float, pred_error: float) -> None:
        """Update VAD from the cognitive step's novelty and prediction error."""
        self.update(stimulus_from_signals(novelty, pred_error))

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

    def salience_boost(
        self,
        *,
        w_arousal: float = AROUSAL_SALIENCE_WEIGHT,
        w_valence: float = VALENCE_SALIENCE_WEIGHT,
    ) -> float:
        """Salience boost implied by the current VAD state."""
        return affect_salience_boost(
            self.state, w_arousal=w_arousal, w_valence=w_valence
        )

    def temperature_scale(self) -> float:
        """Soft-gate temperature scale implied by the current VAD state."""
        return affect_temperature_scale(self.state)

    def threshold_offset(
        self, *, w_dominance: float = DOMINANCE_THRESHOLD_WEIGHT
    ) -> float:
        """Gate-threshold offset implied by the current VAD state."""
        return affect_threshold_offset(self.state, w_dominance=w_dominance)

    def as_dict(self) -> dict[str, float]:
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
