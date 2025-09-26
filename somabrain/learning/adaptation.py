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
    """
    Applies simple online updates to retrieval/utility weights.
    Now supports rollback and explicit constraint enforcement.
    """

    def __init__(
        self,
        retrieval: RetrievalWeights,
        utility: Optional[UtilityWeights] = None,
        learning_rate: float = 0.05,
        max_history: int = 10,
        constraints: Optional[dict] = None,
    ) -> None:
        self._retrieval = retrieval
        self._utility = utility or UtilityWeights()
        self._lr = learning_rate
        self._history = []  # Track (retrieval, utility) tuples for rollback
        self._max_history = max_history
        self._constraints = constraints or {
            "alpha": (0.1, 5.0),
            "gamma": (0.0, 1.0),
            "lambda_": (0.1, 5.0),
            "mu": (0.01, 5.0),
            "nu": (0.01, 5.0),
        }

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
        """
        Adjust weights based on observed utility/reward.
        Returns True when an update is applied, False otherwise.
        Saves previous state for rollback.
        """
        signal = reward if reward is not None else utility
        if signal is None:
            return False
        # Save current state for rollback
        self._save_history()
        delta = self._lr * float(signal)
        # Update retrieval emphasis: positive reward boosts semantic weight,
        # negative reward increases temporal penalty.
        self._retrieval.alpha = self._constrain("alpha", self._retrieval.alpha + delta)
        self._retrieval.gamma = self._constrain("gamma", self._retrieval.gamma - 0.5 * delta)
        # Update utility trade-offs
        self._utility.lambda_ = self._constrain("lambda_", self._utility.lambda_ + delta)
        self._utility.mu = self._constrain("mu", self._utility.mu - 0.25 * delta)
        self._utility.nu = self._constrain("nu", self._utility.nu - 0.25 * delta)
        self._utility.clamp()
        return True

    def rollback(self) -> bool:
        """
        Roll back to the previous set of weights, if available.
        Returns True if rollback succeeded, False otherwise.
        """
        if not self._history:
            return False
        prev_retrieval, prev_utility = self._history.pop()
        self._retrieval.alpha = prev_retrieval["alpha"]
        self._retrieval.beta = prev_retrieval["beta"]
        self._retrieval.gamma = prev_retrieval["gamma"]
        self._retrieval.tau = prev_retrieval["tau"]
        self._utility.lambda_ = prev_utility["lambda_"]
        self._utility.mu = prev_utility["mu"]
        self._utility.nu = prev_utility["nu"]
        return True

    def _save_history(self):
        # Save a shallow copy of current weights for rollback
        if len(self._history) >= self._max_history:
            self._history.pop(0)
        self._history.append((
            {
                "alpha": self._retrieval.alpha,
                "beta": self._retrieval.beta,
                "gamma": self._retrieval.gamma,
                "tau": self._retrieval.tau,
            },
            {
                "lambda_": self._utility.lambda_,
                "mu": self._utility.mu,
                "nu": self._utility.nu,
            },
        ))

    def _constrain(self, name: str, value: float) -> float:
        lower, upper = self._constraints.get(name, (None, None))
        if lower is not None and value < lower:
            return lower
        if upper is not None and value > upper:
            return upper
        return value


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
