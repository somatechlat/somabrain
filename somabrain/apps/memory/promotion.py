"""WM-LTM Promotion Pipeline for SomaBrain.

Per Requirements A2.1-A2.5:
- A2.1: Promotes WM items with salience >= threshold for 3+ consecutive ticks
- A2.2: Promoted items retain reference to LTM coordinate
- A2.3: Recalled promoted items refresh WM recency
- A2.4: Failed promotions queue to outbox for retry
- A2.5: Metrics record promotion_count and promotion_latency_ms

This module implements the WM-LTM promotion pipeline that automatically
promotes salient working memory items to long-term memory storage.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from somabrain.apps.memory.graph_client import GraphClient
    from somabrain.apps.memory.client import MemoryClient

logger = logging.getLogger(__name__)

# Prometheus metrics per H2.5
WM_PROMOTION_TOTAL = Counter(
    "sb_wm_promotion_total",
    "Total WM to LTM promotions",
    ["tenant", "status"],
)
WM_PROMOTION_LATENCY = Histogram(
    "sb_wm_promotion_latency_seconds",
    "WM to LTM promotion latency",
    ["tenant"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


@dataclass
class PromotionCandidate:
    """Tracks a WM item's promotion eligibility.

    Per Requirement A2.1: Items must maintain salience >= threshold
    for 3+ consecutive ticks to be promoted.
    """

    item_id: str
    first_tick: int
    consecutive_count: int = 1
    last_salience: float = 0.0
    vector: List[float] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromotionResult:
    """Result of a promotion operation."""

    item_id: str
    promoted: bool
    ltm_coordinate: Optional[Tuple[float, float, float]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class PromotionTracker:
    """Tracks WM items eligible for WM→LTM promotion.

    Per Requirements A2.1-A2.5:
    - Tracks candidates with salience >= threshold
    - Promotes after 3+ consecutive ticks above threshold
    - Records metrics for promotion operations

    The tracker maintains a dictionary of candidates keyed by item_id.
    Each candidate tracks how many consecutive ticks it has maintained
    salience above the threshold.
    """

    def __init__(
        self,
        threshold: Optional[float] = None,
        min_ticks: Optional[int] = None,
        tenant_id: str = "default",
    ):
        """Initialize PromotionTracker.
...
            tenant_id: Tenant ID for metrics labeling.
        """
        from somabrain.brain_settings.models import BrainSetting

        if threshold is None:
            threshold = BrainSetting.get("promotion_threshold", tenant_id)
        if min_ticks is None:
            # Reusing min_ticks logic or adding new setting if needed.
            # Defaulting to 3 if not found or if setting doesn't exist yet.
            min_ticks = 3

        self._threshold = float(threshold)
        self._min_ticks = int(min_ticks)
        self._tenant_id = tenant_id
        self._candidates: Dict[str, PromotionCandidate] = {}
        # Track promoted items to avoid re-promotion
        self._promoted_ids: set[str] = set()

    @property
    def threshold(self) -> float:
        """Get the promotion threshold."""
        return self._threshold

    @property
    def min_ticks(self) -> int:
        """Get the minimum consecutive ticks required."""
        return self._min_ticks

    def check(
        self,
        item_id: str,
        salience: float,
        tick: int,
        vector: Optional[List[float]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if item should be promoted.

        Per Requirement A2.1: Returns True if salience >= threshold
        for min_ticks consecutive ticks.

        Args:
            item_id: Unique identifier for the WM item.
            salience: Current salience score (0.0-1.0).
            tick: Current tick number.
            vector: Optional vector data for promotion.
            payload: Optional payload data for promotion.

        Returns:
            True if item should be promoted to LTM.
        """
        # Skip already promoted items
        if item_id in self._promoted_ids:
            return False

        # If salience below threshold, remove from candidates
        if salience < self._threshold:
            self._candidates.pop(item_id, None)
            return False

        # Check if already a candidate
        if item_id not in self._candidates:
            # New candidate
            self._candidates[item_id] = PromotionCandidate(
                item_id=item_id,
                first_tick=tick,
                consecutive_count=1,
                last_salience=salience,
                vector=vector or [],
                payload=payload or {},
            )
            return False

        # Existing candidate - increment count
        candidate = self._candidates[item_id]
        candidate.consecutive_count += 1
        candidate.last_salience = salience
        if vector:
            candidate.vector = vector
        if payload:
            candidate.payload = payload

        # Check if ready for promotion
        return candidate.consecutive_count >= self._min_ticks

    def get_candidate(self, item_id: str) -> Optional[PromotionCandidate]:
        """Get promotion candidate by ID."""
        return self._candidates.get(item_id)

    def mark_promoted(self, item_id: str) -> None:
        """Mark item as promoted to prevent re-promotion.

        Per Requirement A2.2: Promoted items retain reference to LTM.
        """
        self._promoted_ids.add(item_id)
        self._candidates.pop(item_id, None)

    def reset_candidate(self, item_id: str) -> None:
        """Reset candidate tracking (e.g., after failed promotion)."""
        self._candidates.pop(item_id, None)

    def get_pending_candidates(self) -> List[PromotionCandidate]:
        """Get all candidates ready for promotion."""
        return [
            c
            for c in self._candidates.values()
            if c.consecutive_count >= self._min_ticks
        ]

    def clear(self) -> None:
        """Clear all tracking state."""
        self._candidates.clear()
        self._promoted_ids.clear()


class WMLTMPromoter:
    """Promotes WM items to LTM via SFM.

    Per Requirements A2.1-A2.5:
    - A2.1: Promotes items with salience >= threshold for 3+ ticks
    - A2.2: Stores LTM coordinate reference
    - A2.4: Queues to outbox on SFM unavailability
    - A2.5: Records promotion metrics
    """

    def __init__(
        self,
        memory_client: "MemoryClient",
        graph_client: Optional["GraphClient"] = None,
        tenant_id: str = "default",
        threshold: Optional[float] = None,
        min_ticks: Optional[int] = None,
    ):
        """Initialize WMLTMPromoter.

        Args:
            memory_client: MemoryClient for SFM communication.
            graph_client: Optional GraphClient for creating promotion links.
            tenant_id: Tenant ID for isolation and metrics.
            threshold: Salience threshold for promotion (default 0.85).
            min_ticks: Minimum consecutive ticks (default 3).
        """
        self._client = memory_client
        self._graph_client = graph_client
        self._tenant_id = tenant_id
        self._tracker = PromotionTracker(
            threshold=threshold,
            min_ticks=min_ticks,
            tenant_id=tenant_id,
        )
        # Map item_id -> LTM coordinate for reference (A2.2)
        self._ltm_references: Dict[str, Tuple[float, float, float]] = {}

    @property
    def tracker(self) -> PromotionTracker:
        """Get the promotion tracker."""
        return self._tracker

    def get_ltm_reference(self, item_id: str) -> Optional[Tuple[float, float, float]]:
        """Get LTM coordinate for a promoted item.

        Per Requirement A2.2: Promoted items retain reference to LTM coordinate.
        """
        return self._ltm_references.get(item_id)

    async def check_and_promote(
        self,
        item_id: str,
        salience: float,
        tick: int,
        vector: List[float],
        payload: Dict[str, Any],
        wm_coordinate: Optional[Tuple[float, float, float]] = None,
    ) -> Optional[PromotionResult]:
        """Check if item should be promoted and promote if ready.

        Per Requirement A2.1: Promotes if salience >= threshold for 3+ ticks.

        Args:
            item_id: Unique identifier for the WM item.
            salience: Current salience score.
            tick: Current tick number.
            vector: Vector embedding for the item.
            payload: Payload data for the item.
            wm_coordinate: Optional WM coordinate for graph linking.

        Returns:
            PromotionResult if promotion was attempted, None otherwise.
        """
        # Check if ready for promotion
        should_promote = self._tracker.check(
            item_id=item_id,
            salience=salience,
            tick=tick,
            vector=vector,
            payload=payload,
        )

        if not should_promote:
            return None

        # Promote to LTM
        return await self.promote(item_id, vector, payload, wm_coordinate)

    async def promote(
        self,
        item_id: str,
        vector: List[float],
        payload: Dict[str, Any],
        wm_coordinate: Optional[Tuple[float, float, float]] = None,
    ) -> PromotionResult:
        """Promote a WM item to LTM.

        Per Requirements A2.1-A2.5:
        - Stores to LTM with memory_type="episodic" and promoted_from_wm=true
        - Creates "promoted_from" link in graph store
        - Records metrics
        - Queues to outbox on failure

        Args:
            item_id: Unique identifier for the WM item.
            vector: Vector embedding for the item.
            payload: Payload data for the item.
            wm_coordinate: Optional WM coordinate for graph linking.

        Returns:
            PromotionResult with success/failure status.
        """
        start_time = time.perf_counter()

        try:
            # Prepare LTM payload (A2.5: memory_type="episodic", promoted_from_wm=true)
            ltm_payload = {
                **payload,
                "memory_type": "episodic",
                "promoted_from_wm": True,
                "original_wm_id": item_id,
                "promotion_timestamp": time.time(),
                "tenant_id": self._tenant_id,
            }

            # Store to LTM via SFM
            # MemoryClient.aremember returns Tuple[float, float, float] directly
            coord_key = f"ltm_promoted:{item_id}"
            ltm_coord = await self._client.aremember(coord_key, ltm_payload)

            # Store LTM reference (A2.2)
            # aremember returns the coordinate tuple directly
            self._ltm_references[item_id] = ltm_coord

            # Create "promoted_from" link in graph store (A2.6)
            # Note: GraphClient.create_link is synchronous
            if self._graph_client and wm_coordinate:
                try:
                    self._graph_client.create_link(
                        from_coord=ltm_coord,
                        to_coord=wm_coordinate,
                        link_type="promoted_from",
                        strength=1.0,
                        metadata={
                            "original_wm_id": item_id,
                            "promotion_timestamp": time.time(),
                        },
                    )
                except Exception as link_exc:
                    logger.warning(
                        "Failed to create promotion link",
                        item_id=item_id,
                        error=str(link_exc),
                    )

            # Mark as promoted
            self._tracker.mark_promoted(item_id)

            # Record metrics (A2.5)
            latency = time.perf_counter() - start_time
            WM_PROMOTION_TOTAL.labels(tenant=self._tenant_id, status="success").inc()
            WM_PROMOTION_LATENCY.labels(tenant=self._tenant_id).observe(latency)

            logger.info(
                "WM item promoted to LTM",
                item_id=item_id,
                ltm_coord=ltm_coord,
                latency_ms=latency * 1000,
            )

            return PromotionResult(
                item_id=item_id,
                promoted=True,
                ltm_coordinate=ltm_coord,
                latency_ms=latency * 1000,
            )

        except Exception as exc:
            latency = time.perf_counter() - start_time

            # Record failure metrics
            WM_PROMOTION_TOTAL.labels(tenant=self._tenant_id, status="error").inc()
            WM_PROMOTION_LATENCY.labels(tenant=self._tenant_id).observe(latency)

            # Queue to outbox for retry (A2.4)
            self._queue_to_outbox(item_id, vector, payload)

            logger.error(
                "WM promotion failed, queued to outbox",
                item_id=item_id,
                error=str(exc),
            )

            return PromotionResult(
                item_id=item_id,
                promoted=False,
                error=str(exc),
                latency_ms=latency * 1000,
            )

    def _queue_to_outbox(
        self,
        item_id: str,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> None:
        """Queue failed promotion to outbox for retry.

        Per Requirement A2.4: Failed promotions queue to outbox.

        Note: enqueue_event is synchronous (uses SQLAlchemy session).
        """
        from somabrain.db.outbox import enqueue_event

        try:
            enqueue_event(
                topic="wm.promote",
                payload={
                    "item_id": item_id,
                    "vector": vector,
                    "payload": payload,
                    "tenant_id": self._tenant_id,
                    "queued_at": time.time(),
                },
                tenant_id=self._tenant_id,
            )
        except Exception as exc:
            # Log but don't raise - promotion failure is already recorded
            logger.error(
                "Failed to queue promotion to outbox",
                item_id=item_id,
                error=str(exc),
            )

    async def refresh_recency(self, item_id: str) -> bool:
        """Refresh WM recency when promoted item is recalled from LTM.

        Per Requirement A2.3: Recalled promoted items refresh WM recency.

        Args:
            item_id: ID of the promoted item that was recalled.

        Returns:
            True if recency was refreshed.
        """
        # This would be called by the recall path when a promoted item is found
        # The actual recency refresh happens in WM, this just tracks the event
        if item_id in self._ltm_references:
            logger.debug("Refreshing recency for promoted item", item_id=item_id)
            return True
        return False


# Global promoter instances per tenant
_promoters: Dict[str, WMLTMPromoter] = {}


def get_wm_ltm_promoter(
    memory_client: "MemoryClient",
    graph_client: Optional["GraphClient"] = None,
    tenant_id: str = "default",
    threshold: Optional[float] = None,
    min_ticks: Optional[int] = None,
) -> WMLTMPromoter:
    """Get or create WMLTMPromoter for tenant.

    Args:
        memory_client: MemoryClient for SFM communication.
        graph_client: Optional GraphClient for graph operations.
        tenant_id: Tenant ID for isolation.
        threshold: Salience threshold for promotion.
        min_ticks: Minimum consecutive ticks.

    Returns:
        WMLTMPromoter instance for the tenant.
    """
    if tenant_id not in _promoters:
        _promoters[tenant_id] = WMLTMPromoter(
            memory_client=memory_client,
            graph_client=graph_client,
            tenant_id=tenant_id,
            threshold=threshold,
            min_ticks=min_ticks,
        )
    return _promoters[tenant_id]
