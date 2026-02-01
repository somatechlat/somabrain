from typing import List, Tuple, Dict, Any

class HistoryManager:
    """Manages history of weight updates for rollback support."""

    def __init__(self, max_history: int):
        self._history: List[Tuple[Dict[str, float], Dict[str, float]]] = []
        self._max_history = max_history

    def save(self, retrieval: Any, utility: Any) -> None:
        """Save current weights to history."""
        if len(self._history) >= self._max_history:
            self._history.pop(0)
        self._history.append(
            (
                {
                    "alpha": retrieval.alpha,
                    "beta": retrieval.beta,
                    "gamma": retrieval.gamma,
                    "tau": retrieval.tau,
                },
                {
                    "lambda_": utility.lambda_,
                    "mu": utility.mu,
                    "nu": utility.nu,
                },
            )
        )

    def rollback(self, retrieval: Any, utility: Any) -> bool:
        """Rollback to previous weights."""
        if not self._history:
            return False
        prev_retrieval, prev_utility = self._history.pop()

        retrieval.alpha = prev_retrieval["alpha"]
        retrieval.beta = prev_retrieval["beta"]
        retrieval.gamma = prev_retrieval["gamma"]
        retrieval.tau = prev_retrieval["tau"]

        utility.lambda_ = prev_utility["lambda_"]
        utility.mu = prev_utility["mu"]
        utility.nu = prev_utility["nu"]

        return True

    def clear(self) -> None:
        """Clear history."""
        self._history.clear()
