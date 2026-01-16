"""Context route state management for DI container.

Extracted from api/context_route.py per monolithic-decomposition spec.
Provides ContextRouteState class for feedback, token ledger, and adaptation management.
"""

from __future__ import annotations

import collections
import time
from typing import Dict, Optional

from ninja.errors import HttpError

from somabrain.core.container import container
from somabrain.context import ContextPlanner
from somabrain.learning import AdaptationEngine
from somabrain.storage.feedback import FeedbackStore
from somabrain.storage.token_ledger import TokenLedger
from django.conf import settings


class ContextRouteState:
    """Encapsulates context route state for DI container management.

    This class holds:
    - FeedbackStore (lazy-initialized)
    - TokenLedger (lazy-initialized)
    - Per-tenant AdaptationEngine cache
    - Feedback counter
    - Rate limiting windows

    Thread Safety:
        The state uses simple dict operations which are atomic in CPython.
        For production use with multiple threads, consider adding explicit
        locking if state consistency is critical.
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        self._feedback_store: Optional[FeedbackStore] = None
        self._token_ledger: Optional[TokenLedger] = None
        self._adaptation_engines: Dict[str, AdaptationEngine] = {}
        self._feedback_counter: int = 0
        self._feedback_rate_window: Dict[str, collections.deque] = (
            collections.defaultdict(collections.deque)
        )

    def get_feedback_store(self) -> FeedbackStore:
        """Get or create the FeedbackStore instance."""
        if self._feedback_store is None:
            self._feedback_store = FeedbackStore()
        return self._feedback_store

    def get_token_ledger(self) -> TokenLedger:
        """Get or create the TokenLedger instance."""
        if self._token_ledger is None:
            self._token_ledger = TokenLedger()
        return self._token_ledger

    def get_adaptation_engine(
        self,
        builder,
        planner: ContextPlanner,
        tenant_id: str = "default",
    ) -> AdaptationEngine:
        """Get or create a per-tenant AdaptationEngine instance."""
        if tenant_id not in self._adaptation_engines:
            adaptation = AdaptationEngine(
                retrieval=builder.weights,
                utility=planner.utility_weights,
                tenant_id=tenant_id,
                enable_dynamic_lr=True,
            )
            self._adaptation_engines[tenant_id] = adaptation
        return self._adaptation_engines[tenant_id]

    @property
    def feedback_counter(self) -> int:
        """Get the current feedback counter value."""
        return self._feedback_counter

    @feedback_counter.setter
    def feedback_counter(self, value: int) -> None:
        """Set the feedback counter value."""
        self._feedback_counter = value

    def increment_feedback_counter(self) -> int:
        """Increment and return the feedback counter."""
        self._feedback_counter += 1
        return self._feedback_counter

    def enforce_rate_limit(self, tenant_id: str) -> None:
        """Enforce per-tenant rate limiting for feedback requests."""
        limit = getattr(settings, "feedback_rate_limit_per_minute", 0) or 0
        if limit <= 0:
            return
        now = time.time()
        window = self._feedback_rate_window[tenant_id]
        # Trim entries older than 60 seconds
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit:
            raise HttpError(
                429,
                f"feedback rate exceeded ({limit}/min). Slow down or raise SOMABRAIN_FEEDBACK_RATE_LIMIT_PER_MIN.",
            )
        window.append(now)

    def reset(self) -> None:
        """Reset all state (for testing)."""
        self._feedback_store = None
        self._token_ledger = None
        self._adaptation_engines.clear()
        self._feedback_counter = 0
        self._feedback_rate_window.clear()


def _create_context_route_state() -> ContextRouteState:
    """Factory function for DI container registration."""
    return ContextRouteState()


# Register with DI container
container.register("context_route_state", _create_context_route_state)


def get_context_route_state() -> ContextRouteState:
    """Get the context route state from the DI container."""
    return container.get("context_route_state")
