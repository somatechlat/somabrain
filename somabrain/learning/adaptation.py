"""Lightweight adaptation engine for utility/retrieval weights."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from somabrain.context.builder import RetrievalWeights


# Redis connection for state persistence
def _get_redis():
    """Get Redis client for per-tenant state persistence."""
    try:
        import redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        return redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    except Exception:
        return None


@dataclass
class UtilityWeights:
    lambda_: float = 1.0
    mu: float = 0.1
    nu: float = 0.05

    def clamp(self, lower: float = 0.0, upper: float = 5.0) -> None:
        self.lambda_ = min(max(self.lambda_, lower), upper)
        self.mu = min(max(self.mu, lower), upper)
        self.nu = min(max(self.nu, lower), upper)


class AdaptationEngine:
    """
    Applies simple online updates to retrieval/utility weights.
    Now supports:
    - Per-tenant state persistence to Redis
    - Dynamic learning rate driven by neuromodulators
    - Rollback and explicit constraint enforcement
    """

    def __init__(
        self,
        retrieval: RetrievalWeights,
        utility: Optional[UtilityWeights] = None,
        learning_rate: float = 0.05,
        max_history: int = 1000,
        constraints: Optional[dict] = None,
        tenant_id: Optional[str] = None,
        enable_dynamic_lr: bool = False,
    ) -> None:
        self._retrieval = retrieval
        self._utility = utility or UtilityWeights()
        self._lr = learning_rate
        self._base_lr = learning_rate  # Store base LR for dynamic scaling
        self._history = []  # Track (retrieval, utility) tuples for rollback
        self._max_history = max_history
        self._constraints = constraints or {
            "alpha": (0.1, 5.0),
            "gamma": (0.0, 1.0),
            "lambda_": (0.1, 5.0),
            "mu": (0.01, 5.0),
            "nu": (0.01, 5.0),
        }
        # Counter for how many feedback applications have occurred – used for observability
        self._feedback_count = 0
        
        # Per-tenant state management
        self._tenant_id = tenant_id or "default"
        self._redis = _get_redis()
        self._enable_dynamic_lr = enable_dynamic_lr or bool(
            os.getenv("SOMABRAIN_LEARNING_RATE_DYNAMIC", "0") == "1"
        )
        
        # Load state from Redis if available
        if self._redis and self._tenant_id:
            self._load_state()

    @property
    def retrieval_weights(self) -> RetrievalWeights:
        return self._retrieval

    @property
    def utility_weights(self) -> UtilityWeights:
        return self._utility
    
    @property
    def tenant_id(self) -> str:
        return self._tenant_id

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
        
        # Compute dynamic learning rate if enabled
        if self._enable_dynamic_lr:
            dopamine = self._get_dopamine_level()
            # lr_eff = base_lr * clamp(0.5 + dopamine, 0.5, 1.2)
            lr_scale = min(max(0.5 + dopamine, 0.5), 1.2)
            self._lr = self._base_lr * lr_scale
        
        # Save current state for rollback
        self._save_history()
        delta = self._lr * float(signal)
        # Update retrieval emphasis: positive reward boosts semantic weight,
        # negative reward increases temporal penalty.
        self._retrieval.alpha = self._constrain("alpha", self._retrieval.alpha + delta)
        self._retrieval.gamma = self._constrain(
            "gamma", self._retrieval.gamma - 0.5 * delta
        )
        # Update utility trade-offs
        self._utility.lambda_ = self._constrain(
            "lambda_", self._utility.lambda_ + delta
        )
        self._utility.mu = self._constrain("mu", self._utility.mu - 0.25 * delta)
        self._utility.nu = self._constrain("nu", self._utility.nu - 0.25 * delta)
        self._utility.clamp()
        # Track that a feedback event was applied
        try:
            self._feedback_count = getattr(self, "_feedback_count", 0) + 1
        except Exception:
            pass
        
        # Persist state to Redis
        self._persist_state()
        
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
        self._history.append(
            (
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
            )
        )

    def _constrain(self, name: str, value: float) -> float:
        lower, upper = self._constraints.get(name, (None, None))
        if lower is not None and value < lower:
            return lower
        if upper is not None and value > upper:
            return upper
        return value
    
    def _get_dopamine_level(self) -> float:
        """Fetch dopamine level from neuromodulator state for this tenant."""
        try:
            from somabrain.neuromodulators import PerTenantNeuromodulators
            neuromod = PerTenantNeuromodulators()
            state = neuromod.get_state(self._tenant_id)
            return state.dopamine
        except Exception:
            return 0.0  # Neutral if unavailable
    
    def _persist_state(self):
        """Save current adaptation state to Redis with tenant prefix."""
        if not self._redis:
            return
        try:
            state_key = f"adaptation:state:{self._tenant_id}"
            state_data = json.dumps({
                "retrieval": {
                    "alpha": self._retrieval.alpha,
                    "beta": self._retrieval.beta,
                    "gamma": self._retrieval.gamma,
                    "tau": self._retrieval.tau,
                },
                "utility": {
                    "lambda_": self._utility.lambda_,
                    "mu": self._utility.mu,
                    "nu": self._utility.nu,
                },
                "feedback_count": self._feedback_count,
                "learning_rate": self._lr,
            })
            # Persist with 7-day TTL to prevent stale state accumulation
            self._redis.setex(state_key, 7 * 24 * 3600, state_data)
        except Exception:
            pass  # Non-critical; continue without persistence
    
    def _load_state(self):
        """Load adaptation state from Redis if present."""
        if not self._redis:
            return
        try:
            state_key = f"adaptation:state:{self._tenant_id}"
            state_data = self._redis.get(state_key)
            if not state_data:
                return
            
            state = json.loads(state_data)
            # Restore retrieval weights
            if "retrieval" in state:
                r = state["retrieval"]
                self._retrieval.alpha = r.get("alpha", self._retrieval.alpha)
                self._retrieval.beta = r.get("beta", self._retrieval.beta)
                self._retrieval.gamma = r.get("gamma", self._retrieval.gamma)
                self._retrieval.tau = r.get("tau", self._retrieval.tau)
            
            # Restore utility weights
            if "utility" in state:
                u = state["utility"]
                self._utility.lambda_ = u.get("lambda_", self._utility.lambda_)
                self._utility.mu = u.get("mu", self._utility.mu)
                self._utility.nu = u.get("nu", self._utility.nu)
            
            # Restore counters
            self._feedback_count = state.get("feedback_count", 0)
            self._lr = state.get("learning_rate", self._base_lr)
        except Exception:
            pass  # Continue with defaults if load fails


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
