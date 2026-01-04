"""
Executive Controller Module for SomaBrain

This module implements an executive control system that manages cognitive resource
allocation, conflict resolution, and exploration strategies. It acts as the brain's
"executive function" component, making decisions about how to allocate attention
and cognitive resources.

Key Features:
- Conflict-aware policy generation
- Exploration vs exploitation balancing
- Multi-armed bandit for strategy optimization
- Recall quality monitoring and adaptation
- Dynamic top-k adjustment based on performance
- Graph augmentation exploration

The executive controller monitors system performance and makes meta-decisions about:
- How many memories to retrieve (top-k adjustment)
- Whether to use graph-based reasoning
- When to inhibit storage or action
- Which universe/context to focus on

Classes:
    ExecConfig: Configuration for executive control parameters
    Policy: Container for executive policy decisions
    ExecutiveController: Main executive control system

Biological Inspiration:
- Prefrontal cortex executive functions
- Anterior cingulate cortex conflict monitoring
- Basal ganglia action selection
- Dopamine system reward prediction and exploration

VIBE Compliance:
    - Uses direct imports from metrics.executive (no lazy imports for circular avoidance)
    - EXEC_BANDIT_ARM imported at module level (no circular deps)
    - All metrics calls are best-effort (silent failure on metrics errors)
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

from .metrics.executive import EXEC_BANDIT_ARM

logger = logging.getLogger(__name__)


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


@dataclass
class ExecConfig:
    """Executive controller configuration.

    Fields default to None, which triggers Settings lookup in __post_init__.
    After initialization, all fields are guaranteed to have non-None values.
    """

    window: Optional[int] = None
    conflict_threshold: Optional[float] = None
    explore_boost_k: int = 2
    use_bandits: bool = False
    bandit_eps: Optional[float] = None

    def __post_init__(self) -> None:
        """Apply Settings defaults for None values."""
        s = _get_settings()
        if self.window is None:
            self.window = s.exec_window
        if self.conflict_threshold is None:
            self.conflict_threshold = s.exec_conflict_threshold
        if self.bandit_eps is None:
            self.bandit_eps = s.exec_bandit_eps


@dataclass
class Policy:
    """Policy class implementation."""

    adj_top_k: int
    use_graph: bool
    inhibit_store: bool
    inhibit_act: bool
    target_universe: Optional[str] = None


class ExecutiveController:
    """Conflict-aware policy and exploration controller.

    Contract
    - observe(tenant, recall_strength): feed recent recall quality [0,1].
    - policy(tenant, base_top_k, switch_threshold, switch_universe): returns Policy
      with adjusted k, whether to use graph, and optional inhibit/switch.
    - Optional epsilon-greedy bandit to explore graph augmentation.
    """

    def __init__(self, cfg: ExecConfig) -> None:
        """Initialize the executive controller with configuration.

        Args:
            cfg: ExecConfig instance specifying window size, conflict threshold,
                 exploration boost, and bandit parameters. Defaults are sourced
                 from centralized Settings.

        Notes:
            - Creates per-tenant sliding windows for recall strength tracking
            - Initializes two-armed bandit state for exploration vs exploitation
            - Window size determines how many recent observations influence policy
            - Conflict threshold triggers graph-based reasoning when exceeded
            - Bandit epsilon controls exploration rate in epsilon-greedy strategy
        """
        self.cfg = cfg
        self._recall_strength: Dict[str, Deque[float]] = {}
        # Two-armed bandit per tenant: 0=baseline, 1=explore (use_graph+boost_k)
        self._bandit_counts: Dict[str, Tuple[int, int]] = {}
        self._bandit_rewards: Dict[str, Tuple[float, float]] = {}

    def _window(self, tenant: str) -> Deque[float]:
        """Get or create the per-tenant sliding window of recall strengths."""
        w = self._recall_strength.get(tenant)
        if w is None:
            # After __post_init__, window is guaranteed non-None
            window_size = self.cfg.window or 8
            w = deque(maxlen=max(1, int(window_size)))
            self._recall_strength[tenant] = w
        return w

    def observe(self, tenant: str, recall_strength: float) -> None:
        """Record a bounded recall strength [0,1] into the tenant window."""
        self._window(tenant).append(float(max(0.0, min(1.0, recall_strength))))
        # Update bandit reward with latest strength for last chosen arm if any

    def _bandit_state(self, tenant: str) -> Tuple[Tuple[int, int], Tuple[float, float]]:
        """Return (counts, rewards) tuples for the 2-armed bandit, initializing if missing."""
        c = self._bandit_counts.get(tenant)
        r = self._bandit_rewards.get(tenant)
        if c is None:
            c = (0, 0)
            self._bandit_counts[tenant] = c
        if r is None:
            r = (0.0, 0.0)
            self._bandit_rewards[tenant] = r
        return c, r

    def choose_arm(self, tenant: str) -> int:
        """Pick an arm using epsilon-greedy over average reward. Returns 0 (baseline) or 1 (explore)."""
        # epsilon-greedy on average reward
        c, r = self._bandit_state(tenant)
        import random

        # After __post_init__, bandit_eps is guaranteed non-None
        eps = self.cfg.bandit_eps or 0.1
        if random.random() < max(0.0, min(1.0, float(eps))):
            return random.choice([0, 1])
        avg0 = 0.0 if c[0] <= 0 else r[0] / c[0]
        avg1 = 0.0 if c[1] <= 0 else r[1] / c[1]
        return 1 if avg1 >= avg0 else 0

    def update_bandit(self, tenant: str, arm: int, reward: float) -> None:
        """Update counts and cumulative rewards for the chosen arm."""
        arm = 1 if arm else 0
        c, r = self._bandit_state(tenant)
        if arm == 0:
            self._bandit_counts[tenant] = (c[0] + 1, c[1])
            self._bandit_rewards[tenant] = (r[0] + float(reward), r[1])
        else:
            self._bandit_counts[tenant] = (c[0], c[1] + 1)
            self._bandit_rewards[tenant] = (r[0], r[1] + float(reward))

    def conflict(self, tenant: str) -> float:
        """Return conflict proxy in [0,1] as 1 - mean(recall_strength)."""
        w = self._window(tenant)
        if not w:
            return 0.0
        # conflict proxy: 1 - mean recall strength
        return float(max(0.0, min(1.0, 1.0 - (sum(w) / len(w)))))

    def policy(
        self,
        tenant: str,
        base_top_k: int,
        switch_threshold: float = 0.85,
        switch_universe: str = "cf:alt",
    ) -> Policy:
        """Compute a Policy using conflict and optional bandit exploration.

        - Adjusts top_k when exploring graph augmentation
        - May inhibit store/act under very high conflict
        - Can suggest a universe switch when conflict exceeds threshold
        """
        c = self.conflict(tenant)
        # After __post_init__, conflict_threshold is guaranteed non-None
        threshold = self.cfg.conflict_threshold or 0.0
        use_graph = c >= threshold
        if self.cfg.use_bandits:
            # choose between baseline and explore arm
            arm = self.choose_arm(tenant)
            use_graph = bool(arm == 1)
            try:
                EXEC_BANDIT_ARM.labels(
                    arm=("explore" if use_graph else "baseline")
                ).inc()
            except Exception as exc:
                logger.debug("Failed to record EXEC_BANDIT_ARM metric: %s", exc)
        adj_top_k = int(base_top_k + (self.cfg.explore_boost_k if use_graph else 0))
        inhibit_act = False
        inhibit_store = False
        if c >= 0.9:
            inhibit_act = True
            inhibit_store = True
        target_universe = None
        if c >= float(switch_threshold):
            target_universe = str(switch_universe)
        return Policy(
            adj_top_k=adj_top_k,
            use_graph=use_graph,
            inhibit_store=inhibit_store,
            inhibit_act=inhibit_act,
            target_universe=target_universe,
        )