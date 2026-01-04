"""FocusState - Canonical working-memory focus signal.

This module provides FocusState which WRAPS the existing HRRContext
(composition, not inheritance). HRRContext handles the low-level HRR
vector operations. FocusState adds session-scoped state management,
previous/current focus tracking, and deterministic digest computation.

NO STUBS. NO MOCKS. Uses EXISTING infrastructure.

Requirements: 7.1-7.7, 8.1-8.5, 9.1-9.5
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from somabrain.context_hrr import HRRContext
    from somabrain.memory.graph_client import GraphClient

from somabrain.metrics.planning import FOCUS_UPDATE_LATENCY, FOCUS_PERSIST

logger = logging.getLogger(__name__)


class FocusState:
    """
    Canonical working-memory focus signal using EXISTING HRRContext.

    FocusState WRAPS HRRContext (composition, not inheritance).
    - HRRContext handles: superposition, decay, cleanup, novelty
    - FocusState adds: session tracking, previous/current vectors, persistence

    Requirements: 7.1-7.7
    """

    def __init__(
        self,
        hrr_context: "HRRContext",
        cfg: Any,
        *,
        session_id: str,
        tenant_id: str,
    ):
        """Initialize FocusState wrapping an HRRContext.

        Args:
            hrr_context: EXISTING HRRContext instance for vector operations
            cfg: Configuration object with focus settings
            session_id: Session identifier for tracking
            tenant_id: Tenant identifier for isolation
        """
        self._hrr = hrr_context  # EXISTING, WORKING (Requirement 7.1)
        self._cfg = cfg
        self._session_id = session_id
        self._tenant_id = tenant_id
        self._previous_focus_vec: Optional[np.ndarray] = None
        self._current_focus_vec: Optional[np.ndarray] = None
        self._focus_digest: Optional[str] = None
        self._tick = 0
        self._previous_coord: Optional[str] = None
        self._current_coord: Optional[str] = None

    def update(
        self,
        task_vec: np.ndarray,
        recall_hits: List[Tuple[str, np.ndarray]],
        *,
        timestamp: Optional[float] = None,
    ) -> None:
        """Update focus with task embedding and top-N recall hits.

        Args:
            task_vec: Task embedding vector (primary anchor)
            recall_hits: List of (id, vector) tuples from recall
            timestamp: Optional timestamp for decay calculation

        Requirements: 7.2, 7.3, 7.4, 7.5
        """
        t0 = time.perf_counter()
        ts = timestamp if timestamp is not None else time.time()

        # Save previous focus (Requirement 7.5)
        self._previous_focus_vec = self._current_focus_vec
        self._previous_coord = self._current_coord

        # Admit task as primary anchor via EXISTING HRRContext (Requirement 7.2)
        self._hrr.admit(f"task_{self._tick}", task_vec, timestamp=ts)

        # Admit top-N recall hits deterministically (Requirement 7.3)
        top_n = int(getattr(self._cfg, "focus_admit_top_n", 4))
        # Sort by ID for determinism (Requirement 7.7)
        sorted_hits = sorted(recall_hits, key=lambda x: x[0])[:top_n]
        for hit_id, hit_vec in sorted_hits:
            self._hrr.admit(hit_id, hit_vec, timestamp=ts)

        # Update current focus from HRRContext (Requirement 7.5)
        self._current_focus_vec = self._hrr.context.copy()

        # Compute deterministic digest (Requirement 7.7)
        self._focus_digest = self._compute_digest(self._current_focus_vec)
        self._tick += 1

        FOCUS_UPDATE_LATENCY.observe(time.perf_counter() - t0)

    def _compute_digest(self, vec: np.ndarray) -> str:
        """Deterministic hash of focus vector.

        Quantizes to 4 decimal places for stability across runs.

        Requirement: 7.7
        """
        quantized = np.round(vec, 4)
        return hashlib.sha256(quantized.tobytes()).hexdigest()[:16]

    @property
    def current_focus_vec(self) -> Optional[np.ndarray]:
        """Current focus vector (Requirement 7.5)."""
        return self._current_focus_vec

    @property
    def previous_focus_vec(self) -> Optional[np.ndarray]:
        """Previous focus vector for prediction comparison (Requirement 7.5)."""
        return self._previous_focus_vec

    @property
    def focus_digest(self) -> Optional[str]:
        """Deterministic digest of current focus (Requirement 7.7)."""
        return self._focus_digest

    @property
    def tick(self) -> int:
        """Current tick count."""
        return self._tick

    @property
    def session_id(self) -> str:
        """Session identifier."""
        return self._session_id

    @property
    def tenant_id(self) -> str:
        """Tenant identifier."""
        return self._tenant_id

    def novelty(self, vec: np.ndarray) -> float:
        """Compute novelty via EXISTING HRRContext (Requirement 7.6)."""
        return self._hrr.novelty(vec)

    def persist_snapshot(
        self,
        mem_client: Any,
        *,
        store_gate: bool,
        universe: Optional[str] = None,
    ) -> Optional[str]:
        """Persist focus snapshot to memory if gate allows.

        Args:
            mem_client: Memory client for storage
            store_gate: Whether storage is allowed
            universe: Optional namespace/universe

        Returns:
            Coordinate string if persisted, None otherwise

        Requirements: 8.1-8.5
        """
        # Check focus_persist config (Requirement 8.1)
        if not getattr(self._cfg, "focus_persist", False):
            return None

        # Check store gate (Requirement 8.1)
        if not store_gate:
            return None

        if self._current_focus_vec is None:
            return None

        try:
            # Create payload WITHOUT raw user text (Requirement 8.4)
            payload: Dict[str, Any] = {
                "type": "focus_snapshot",
                "session_id": self._session_id,
                "tick": self._tick,
                "focus_digest": self._focus_digest,
                "timestamp": time.time(),
                # NO raw user text - privacy safe
            }

            # Store with memory_type="episodic" (Requirement 8.2, 8.3)
            coord = mem_client.store(
                vec=self._current_focus_vec,
                payload=payload,
                memory_type="episodic",
                universe=universe,
            )

            self._current_coord = coord
            FOCUS_PERSIST.inc()
            return coord

        except Exception as exc:
            # Continue without failing (Requirement 8.5)
            logger.warning(f"Focus persist failed (non-fatal): {exc}")
            return None

    def create_links(
        self,
        graph_client: Optional["GraphClient"],
        used_memory_ids: List[str],
        selected_option_ids: Optional[List[str]] = None,
    ) -> None:
        """Create focus chain links using EXISTING GraphClient.

        Args:
            graph_client: GraphClient for link creation
            used_memory_ids: IDs of memories used in this step
            selected_option_ids: IDs of options selected

        Requirements: 9.1-9.5
        """
        # Check focus_links config
        if not getattr(self._cfg, "focus_links", False):
            return

        if graph_client is None:
            return

        selected_option_ids = selected_option_ids or []

        # "next" edge between consecutive snapshots (Requirement 9.1)
        if self._previous_coord and self._current_coord:
            try:
                graph_client.create_link(
                    from_coord=self._str_to_coord(self._previous_coord),
                    to_coord=self._str_to_coord(self._current_coord),
                    link_type="next",
                    strength=1.0,
                )
            except Exception as exc:
                # GraphClient queues to outbox on failure (Requirement 9.4)
                logger.debug(f"Focus next link failed: {exc}")

        # "attends_to" edges to used memories (Requirement 9.2)
        if self._current_coord:
            for mem_id in used_memory_ids:
                mem_coord = self._id_to_coord(mem_id)
                if mem_coord:
                    try:
                        graph_client.create_link(
                            from_coord=self._str_to_coord(self._current_coord),
                            to_coord=mem_coord,
                            link_type="attends_to",
                            strength=0.8,
                        )
                    except Exception as exc:
                        logger.debug(f"Focus attends_to link failed: {exc}")

        # "used_option" edges to selected options (Requirement 9.3)
        if self._current_coord:
            for opt_id in selected_option_ids:
                opt_coord = self._id_to_coord(opt_id)
                if opt_coord:
                    try:
                        graph_client.create_link(
                            from_coord=self._str_to_coord(self._current_coord),
                            to_coord=opt_coord,
                            link_type="used_option",
                            strength=0.7,
                        )
                    except Exception as exc:
                        logger.debug(f"Focus used_option link failed: {exc}")

    def _str_to_coord(self, coord_str: str) -> Tuple[float, ...]:
        """Convert string to coordinate tuple."""
        return tuple(float(c) for c in coord_str.split(","))

    def _id_to_coord(self, mem_id: str) -> Optional[Tuple[float, ...]]:
        """Convert memory ID to coordinate if possible."""
        try:
            return self._str_to_coord(mem_id)
        except (ValueError, AttributeError):
            return None