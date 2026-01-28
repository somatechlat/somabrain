"""
Rust Adaptation Engine Bridge.

Requires the Rust AdaptationEngine. No Python fallback permitted.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from somabrain_rs import AdaptationEngine as RustAdaptationEngine
    from somabrain_rs import RetrievalWeights as RustRetrievalWeights
    from somabrain_rs import UtilityWeights as RustUtilityWeights

    RUST_ADAPTATION_AVAILABLE = True
    logger.info("✅ Rust AdaptationEngine loaded - using high-performance backend")
except ImportError as exc:
    RUST_ADAPTATION_AVAILABLE = False
    logger.error("Rust AdaptationEngine required but not available", exc_info=True)
    raise RuntimeError(
        "Rust AdaptationEngine not available. Build/install somabrain_rs before running."
    ) from exc


def is_rust_adaptation_available() -> bool:
    """Check if Rust adaptation engine is available."""
    return RUST_ADAPTATION_AVAILABLE


class AdaptationEngineBridge:
    """Bridge to Rust AdaptationEngine. No fallback path."""

    def __init__(
        self,
        learning_rate: Optional[float] = None,
        tenant_id: str = "default",
    ) -> None:
        """Initialize bridge with required Rust backend."""
        from somabrain.brain_settings.models import BrainSetting

        if learning_rate is None:
            learning_rate = BrainSetting.get("adapt_lr", tenant_id)

        if not RUST_ADAPTATION_AVAILABLE:
            raise RuntimeError("Rust AdaptationEngine is required and must be installed.")

        self._tenant_id = tenant_id
        self._rust_engine = RustAdaptationEngine(learning_rate)
        logger.debug("Using Rust AdaptationEngine")

    @property
    def using_rust(self) -> bool:
        """Check if using Rust backend."""
        return True

    def set_retrieval(
        self, alpha: float, beta: float, gamma: float, tau: float
    ) -> None:
        """Set retrieval weights."""
        self._rust_engine.set_retrieval(alpha, beta, gamma, tau)

    def get_retrieval(self) -> Tuple[float, float, float, float]:
        """Get retrieval weights."""
        return self._rust_engine.get_retrieval()

    def set_utility(self, lambda_: float, mu: float, nu: float) -> None:
        """Set utility weights."""
        self._rust_engine.set_utility(lambda_, mu, nu)

    def get_utility(self) -> Tuple[float, float, float]:
        """Get utility weights."""
        return self._rust_engine.get_utility()

    def apply_feedback(self, utility_signal: float, reward: float) -> bool:
        """Apply feedback and update weights - CPU-bound hot path."""
        return self._rust_engine.apply_feedback(utility_signal, reward)

    def get_tau(self) -> float:
        """Get current tau value."""
        return self._rust_engine.get_tau()

    def set_tau(self, tau: float) -> None:
        """Set tau value."""
        self._rust_engine.set_tau(tau)

    def apply_tau_decay(self, decay_rate: float, min_tau: float) -> None:
        """Apply tau decay."""
        self._rust_engine.apply_tau_decay(decay_rate, min_tau)

    @property
    def learning_rate(self) -> float:
        """Get learning rate."""
        return self._rust_engine.learning_rate

    def update_learning_rate(self, dopamine: float) -> None:
        """Update learning rate based on dopamine level."""
        self._rust_engine.update_learning_rate(dopamine)

    def reset(self) -> None:
        """Reset engine to defaults."""
        self._rust_engine.reset()

    def get_feedback_count(self) -> int:
        """Get feedback count."""
        return self._rust_engine.get_feedback_count()


# Convenience function for quick instantiation
def get_adaptation_engine(
    learning_rate: float = 0.05,
) -> AdaptationEngineBridge:
    """
    Get an AdaptationEngine instance.

    Uses Rust backend; no fallback path.
    """
    return AdaptationEngineBridge(learning_rate=learning_rate)
