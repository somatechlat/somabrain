
## `somabrain/context/builder.py`

### `ContextBuilder`

```python
class ContextBuilder:
    """Construct multi-view context bundles for agent requests."""

    def __init__(
        self,
        embed_fn: Callable[[str], Iterable[float]],
        memory: Optional[object] = None,
        weights: Optional[RetrievalWeights] = None,
        working_memory: Optional["WorkingMemoryBuffer"] = None,
    ) -> None:
        """Initializes the ContextBuilder.

        Args:
            embed_fn: The function to use for embedding text.
            memory: The memory client to use for retrieving memories.
            weights: The weights to use for scoring memories.
            working_memory: The working memory buffer to use for storing session
                data.
        """
        ...

    def set_tenant(self, tenant_id: str) -> None:
        """Store the tenant ID so weight updates can be attributed correctly."""
        ...

    def build(
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
    ) -> ContextBundle:
        """Builds a context bundle for the given query.

        Args:
            query: The query to build the context for.
            top_k: The number of memories to retrieve.
            session_id: The ID of the session.

        Returns:
            The context bundle.
        """
        ...
```

## `somabrain/scoring.py`

### `UnifiedScorer`

```python
class UnifiedScorer:
    """Combine multiple similarity signals."""

    def __init__(
        self,
        *,
        w_cosine: float,
        w_fd: float,
        w_recency: float,
        weight_min: float,
        weight_max: float,
        recency_tau: float,
        fd_backend: Optional[FDSalienceSketch] = None,
    ) -> None:
        """Initializes the UnifiedScorer.

        Args:
            w_cosine: The weight for the cosine similarity component.
            w_fd: The weight for the FD subspace cosine component.
            w_recency: The weight for the recency component.
            weight_min: The minimum value for the weights.
            weight_max: The maximum value for the weights.
            recency_tau: The tau value for the recency decay.
            fd_backend: The FD salience sketch backend.
        """
        ...

    def score(
        self,
        query: np.ndarray,
        candidate: np.ndarray,
        *,
        recency_steps: Optional[int] = None,
        cosine: Optional[float] = None,
    ) -> float:
        """Calculates the unified score for a candidate memory.

        Args:
            query: The query vector.
            candidate: The candidate memory vector.
            recency_steps: The number of recency steps.
            cosine: The pre-computed cosine similarity.

        Returns:
            The unified score.
        """
        ...

    def stats(self) -> dict[str, float | dict[str, float | bool]]:
        """Returns a dictionary of the scorer's statistics."""
        ...
```

## `somabrain/learning/adaptation.py`

### `AdaptationEngine`

```python
class AdaptationEngine:
    """
    Applies simple online updates to retrieval/utility weights.
    """

    def __init__(
        self,
        retrieval: "RetrievalWeights" | None = None,
        utility: Optional[UtilityWeights] = None,
        learning_rate: Optional[float] = None,
        max_history: Optional[int] = None,
        constraints: AdaptationConstraints | dict | None = None,
        tenant_id: Optional[str] = None,
        enable_dynamic_lr: bool = False,
        gains: Optional[AdaptationGains] = None,
    ) -> None:
        """Initializes the AdaptationEngine.

        Args:
            retrieval: The initial retrieval weights.
            utility: The initial utility weights.
            learning_rate: The learning rate.
            max_history: The maximum number of history entries to keep for
                rollback.
            constraints: The constraints for the weights.
            tenant_id: The ID of the tenant.
            enable_dynamic_lr: Whether to enable dynamic learning rate.
            gains: The gains for the adaptation.
        """
        ...

    def set_constraints(self, constraints: AdaptationConstraints) -> None:
        """Replace constraint bounds at runtime and rebuild internal map."""
        ...

    def set_gains(self, gains: AdaptationGains) -> None:
        """Replace per-parameter gains at runtime."""
        ...

    def set_base_learning_rate(self, base_lr: float) -> None:
        """Update base learning rate and reset effective LR to base."""
        ...

    def reset(
        self,
        retrieval_defaults: Optional["RetrievalWeights"] = None,
        utility_defaults: Optional[UtilityWeights] = None,
        base_lr: Optional[float] = None,
        clear_history: bool = True,
    ) -> None:
        """Reset weights and counters to defaults for a clean run.

        Args:
            retrieval_defaults: Optional RetrievalWeights to copy into engine.
            utility_defaults: Optional UtilityWeights to copy into engine.
            base_lr: Optional new base learning rate.
            clear_history: When True, drops rollback history and feedback count.
        """
        ...

    def save_state(self) -> None:
        """Persist the current adaptation state to Redis."""
        ...

    def load_state(self) -> dict:
        """Load the persisted state from Redis and return it."""
        ...

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
        ...

    def rollback(self) -> bool:
        """
        Roll back to the previous set of weights, if available.
        Returns True if rollback succeeded, False otherwise.
        """
        ...
```

## `somabrain/neuromodulators.py`

### `Neuromodulators`

```python
class Neuromodulators:
    """
    Publish/subscribe hub for NeuromodState updates.
    """

    def __init__(self):
        """Initializes the Neuromodulators hub."""
        ...

    def get_state(self) -> NeuromodState:
        """Returns the current neuromodulator state."""
        ...

    def set_state(self, s: NeuromodState) -> None:
        """Set the current neuromodulator state."""
        ...

    def subscribe(self, cb: Callable[[NeuromodState], None]) -> None:
        """Subscribes a callback to neuromodulator state changes."""
        ...
```

### `PerTenantNeuromodulators`

```python
class PerTenantNeuromodulators:
    """Simple container that keeps a NeuromodState per tenant."""

    def __init__(self):
        """Initializes the per-tenant neuromodulator store."""
        ...

    def get_state(self, tenant_id: str | None = None) -> NeuromodState:
        """Gets the neuromodulator state for the given tenant."""
        ...

    def set_state(self, tenant_id: str, state: NeuromodState) -> None:
        """Sets the neuromodulator state for the given tenant."""
        ...
```

### `AdaptiveNeuromodulators`

```python
@dataclass
class AdaptiveNeuromodulators:
    """True learning neuromodulator system with adaptive parameters."""

    def __init__(self):
        """Initializes the adaptive neuromodulators."""
        ...

    def get_current_state(self) -> NeuromodState:
        """Get current neuromodulator state from adaptive parameters."""
        ...

    def update_from_performance(
        self, performance: PerformanceMetrics, task_type: str = "general"
    ) -> NeuromodState:
        """Update neuromodulators based on performance feedback."""
        ...
```

### `AdaptivePerTenantNeuromodulators`

```python
class AdaptivePerTenantNeuromodulators:
    """Per-tenant adaptive neuromodulator system."""

    def __init__(self):
        """Initializes the per-tenant adaptive neuromodulator system."""
        ...

    def get_adaptive_system(self, tenant_id: str) -> AdaptiveNeuromodulators:
        """Get or create adaptive system for tenant."""
        ...

    def get_state(self, tenant_id: str | None = None) -> NeuromodState:
        """Get current neuromodulator state."""
        ...

    def adapt_from_performance(
        self,
        tenant_id: str,
        performance: PerformanceMetrics,
        task_type: str = "general",
    ) -> NeuromodState:
        """Adapt neuromodulators based on performance for specific tenant."""
        ...
```
