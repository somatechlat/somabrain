"""Lightweight adaptation engine for utility/retrieval weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from somabrain.context.builder import RetrievalWeights


@dataclass
class UtilityWeights:
    lambda_: float = 1.0
    mu: float = 0.1
    nu: float = 0.05

    def clamp(self, lower: float = 0.0, upper: float = 10.0) -> None:
        self.lambda_ = min(max(self.lambda_, lower), upper)
        self.mu = min(max(self.mu, lower), upper)
        self.nu = min(max(self.nu, lower), upper)


class AdaptationEngine:
    """Applies simple online updates to retrieval/utility weights."""

    def __init__(
        self,
        retrieval: RetrievalWeights,
        utility: Optional[UtilityWeights] = None,
        learning_rate: float = 0.05,
    ) -> None:
        self._retrieval = retrieval
        self._utility = utility or UtilityWeights()
        self._lr = learning_rate

    @property
    def retrieval_weights(self) -> RetrievalWeights:
        return self._retrieval

    @property
    def utility_weights(self) -> UtilityWeights:
        return self._utility

    def apply_feedback(
        self,
        utility: float,
        reward: Optional[float] = None,
    ) -> bool:
        """Adjust weights based on observed utility/reward.

        Returns True when an update is applied, False otherwise.
        """
        signal = reward if reward is not None else utility
        if signal is None:
            return False
        delta = self._lr * float(signal)
        # Update retrieval emphasis: positive reward boosts semantic weight,
        # negative reward increases temporal penalty.
        self._retrieval.alpha = _clamp(self._retrieval.alpha + delta, 0.1, 5.0)
        self._retrieval.gamma = _clamp(self._retrieval.gamma - 0.5 * delta, 0.0, 1.0)
        # Update utility trade-offs
        self._utility.lambda_ = _clamp(self._utility.lambda_ + delta, 0.1, 5.0)
        self._utility.mu = _clamp(self._utility.mu - 0.25 * delta, 0.01, 5.0)
        self._utility.nu = _clamp(self._utility.nu - 0.25 * delta, 0.01, 5.0)
        self._utility.clamp()
        return True


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
