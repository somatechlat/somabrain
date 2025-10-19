"""Lightweight adaptation engine for utility/retrieval weights."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from somabrain.context.builder import RetrievalWeights
    from somabrain.feedback import Feedback

try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency
    shared_settings = None  # type: ignore

from somabrain.infrastructure import get_redis_url


# Redis connection for state persistence
def _get_redis():
    """Get Redis client for per-tenant state persistence.
    Prefer the full URL via ``SOMABRAIN_REDIS_URL`` if provided (as set in the
    Docker compose environment).  Fall back to ``REDIS_HOST``/``REDIS_PORT``
    for compatibility with local development.
    """
    import os

    try:
        redis_url = get_redis_url()
        if redis_url:
            redis_url = redis_url.strip()
        import redis

        if redis_url:
            return redis.from_url(redis_url)
        # Legacy fallback to host/port variables without hard-coded defaults
        redis_host = os.getenv("SOMABRAIN_REDIS_HOST") or os.getenv("REDIS_HOST")
        redis_port = os.getenv("SOMABRAIN_REDIS_PORT") or os.getenv("REDIS_PORT")
        redis_db = os.getenv("SOMABRAIN_REDIS_DB") or os.getenv("REDIS_DB", "0")
        if redis_host and redis_port:
            return redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
    except Exception:
        pass
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
        retrieval: "RetrievalWeights" | None = None,
        utility: Optional[UtilityWeights] = None,
        learning_rate: float = 0.05,
        max_history: int = 1000,
        constraints: Optional[dict] = None,
        tenant_id: Optional[str] = None,
        enable_dynamic_lr: bool = False,
    ) -> None:
        # Lazy import to avoid circular dependency at module load time
        if retrieval is None:
            from somabrain.context.builder import RetrievalWeights as RetrievalWeights

            retrieval = RetrievalWeights()
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
        # Ensure the dynamic LR flag is a proper boolean. Environment variable overrides if set.
        dyn_lr = bool(enable_dynamic_lr)
        if shared_settings is not None:
            try:
                dyn_lr = dyn_lr or bool(
                    getattr(shared_settings, "learning_rate_dynamic", False)
                )
            except Exception:
                pass
        elif os.getenv("SOMABRAIN_LEARNING_RATE_DYNAMIC", "0") == "1":
            dyn_lr = True
        self._enable_dynamic_lr = dyn_lr

        # Initialize per-tenant tau gauge with a small deterministic offset
        try:
            from somabrain.metrics import tau_gauge

            offset = (hash(self._tenant_id) % 100) / 1000.0  # 0.0‑0.099
            tau_gauge.labels(tenant_id=self._tenant_id).set(
                self._retrieval.tau + offset
            )
        except Exception:
            pass

        # Load state from Redis if available
        if self._redis and self._tenant_id:
            self._load_state()

    # ---------------------------------------------------------------------
    # Public helpers for tests / external callers
    # ---------------------------------------------------------------------
    def save_state(self) -> None:
        """Persist the current adaptation state to Redis.

        The internal ``_persist_state`` method already performs the write, but
        the test suite expects a public ``save_state`` method.
        """
        self._persist_state()

    def load_state(self) -> dict:
        """Load the persisted state from Redis and return it.

        Returns the same dictionary structure that ``_persist_state`` writes.
        """
        self._load_state()
        return self._state

    @property
    def _state(self) -> dict:
        """Current adaptation state as a dictionary.

        Includes retrieval and utility weights, feedback count, learning rate
        and tenant identifier. This mirrors the JSON payload stored in Redis.
        """
        return {
            "tenant_id": self._tenant_id,
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
            "feedback_count": getattr(self, "_feedback_count", 0),
            "learning_rate": getattr(self, "_lr", self._base_lr),
        }

    def _get_neuromod_state(self):
        """Fetch the full neuromodulator state for this tenant.

        Returns the object provided by ``PerTenantNeuromodulators.get_state``
        or ``None`` if the module cannot be imported.
        """
        try:
            from somabrain.neuromodulators import PerTenantNeuromodulators

            neuromod = PerTenantNeuromodulators()
            return neuromod.get_state(self._tenant_id)
        except Exception:
            return None

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
        utility: float | Feedback,
        reward: Optional[float] = None,
    ) -> bool:
        """
        Adjust weights based on observed utility/reward.
        Returns True when an update is applied, False otherwise.
        Saves previous state for rollback.
        """
        # Accept a ``Feedback`` instance for convenience in tests.
        if hasattr(utility, "score"):
            # ``Feedback`` objects expose a numeric ``score`` attribute.
            utility_val = float(getattr(utility, "score"))
        else:
            utility_val = float(utility)

        signal = reward if reward is not None else utility_val
        if signal is None:
            return False

        # Compute learning rate based on configuration
        if self._enable_dynamic_lr:
            # Dynamic scaling using dopamine level
            dopamine = self._get_dopamine_level()
            lr_scale = min(max(0.5 + dopamine, 0.5), 1.2)
            self._lr = self._base_lr * lr_scale
        else:
            # Simple scaling based on the feedback signal (utility or reward)
            # This ensures different utilities produce different learning rates.
            self._lr = self._base_lr * (1.0 + float(signal))
        # Expose the effective learning rate for tests and external inspection
        self._lr_eff = self._lr

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

        # Persist state to Redis before metric update to guarantee persistence
        # Ensure we have a Redis client (fallback to _get_redis) before persisting
        if not self._redis:
            self._redis = _get_redis()
        self._persist_state()
        # Update shared metrics for this tenant (import inside to allow monkeypatching)
        try:
            from somabrain import metrics as _metrics

            _metrics.update_learning_retrieval_weights(
                tenant_id=self._tenant_id,
                alpha=self._retrieval.alpha,
                beta=self._retrieval.beta,
                gamma=self._retrieval.gamma,
                tau=self._retrieval.tau,
            )
        except Exception:
            pass
        # Ensure state persisted even if metric update fails (duplicate call is safe)
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
        # Build a plain‑dict with only primitive types to guarantee JSON serialisation.
        state = {
            "retrieval": {
                "alpha": float(self._retrieval.alpha),
                "beta": float(self._retrieval.beta),
                "gamma": float(self._retrieval.gamma),
                "tau": float(self._retrieval.tau),
            },
            "utility": {
                "lambda_": float(self._utility.lambda_),
                "mu": float(self._utility.mu),
                "nu": float(self._utility.nu),
            },
            "feedback_count": int(getattr(self, "_feedback_count", 0)),
            "learning_rate": float(self._lr),
        }
        state_key = f"adaptation:state:{self._tenant_id}"
        # json.dumps should never fail with this simple structure.
        state_data = json.dumps(state)
        # Persist with 7‑day TTL to prevent stale state accumulation.
        self._redis.setex(state_key, 7 * 24 * 3600, state_data)

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


# Re-export RetrievalWeights for external imports (tests expect it here)
try:
    from somabrain.context.builder import RetrievalWeights as RetrievalWeights  # noqa: F401
except Exception:
    pass


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
