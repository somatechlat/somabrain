"""
Planner module – Phase 3 Cognitive Capability

Implements a high‑level *multi‑step planning* engine for SomaBrain agents.
The design is deliberately lightweight: it provides a clear API that can be
extended later with sophisticated search, back‑tracking, and heuristic
evaluation.

Key concepts:
- **Goal** – a user‑defined target expressed as a string or structured dict.
- **Context** – current state of the agent (memory snapshot, neuromodulators,
  recent observations).  The Planner receives a dictionary so callers can
  decide what to pass.
- **Plan** – ordered list of *Step* objects.  Each step contains an action
  name, optional parameters, and an optional *precondition* function that
  validates whether the step can be executed given the current context.

The implementation focuses on:
1. Defining the public API (`Planner.plan`, `Planner.validate_step`,
   `Planner.backtrack`).
2. Providing a simple *depth‑first* planner with back‑tracking support.
3. Hook points for future extensions (e.g., integration with the autonomous
   learning module for heuristic scoring).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Step:
    """A single planning step.

    Attributes
    ----------
    name: str
        Human‑readable identifier for the action (e.g., "retrieve_memory").
    params: Dict[str, Any]
        Parameters required to execute the action.
    precondition: Optional[Callable[[Dict[str, Any]], bool]]
        Callable that receives the *current* context and returns ``True`` if the
        step is applicable.  ``None`` means the step is always applicable.
    """

    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    precondition: Optional[Callable[[Dict[str, Any]], bool]] = None

    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """Return ``True`` if the step can run under the supplied *context*."""
        if self.precondition is None:
            return True
        try:
            return bool(self.precondition(context))
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Precondition raised an exception: %s", exc)
            return False


class Planner:
    """High‑level multi‑step planner.

    The planner is deliberately *stateless* – it receives the *goal* and the
    *context* as arguments and returns a ``Plan`` (list of :class:`Step`).  This
    makes the component easy to test and to integrate with the autonomous
    learning loop (e.g., the planner can be re‑trained based on plan success).
    """

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        logger.info("Planner created with max_depth=%s", max_depth)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def plan(self, goal: Any, context: Dict[str, Any]) -> List[Step]:
        """Generate a plan for *goal* given the current *context*.

        The default implementation performs a simple depth‑first search using
        ``self._expand`` to generate candidate steps.  Sub‑classes can override
        ``_expand`` to plug in domain‑specific actions.
        """
        logger.debug("Planning for goal=%s with context keys=%s", goal, list(context))
        plan: List[Step] = []
        success = self._search(goal, context, plan, depth=0)
        if not success:
            logger.warning("Planner could not find a viable plan for goal=%s", goal)
        return plan

    # ---------------------------------------------------------------------
    # Extension points – override in a subclass for richer behaviour
    # ---------------------------------------------------------------------
    def _expand(self, goal: Any, context: Dict[str, Any]) -> List[Step]:
        """Return a list of candidate steps that *might* move the system towards *goal*.

        The base implementation provides a very small generic catalogue:
        1. ``"retrieve_memory"`` – fetch something from working memory.
        2. ``"update_state"`` – modify an internal variable.
        3. ``"communicate"`` – send a message to another agent.
        Concrete deployments should subclass :class:`Planner` and replace this
        method with domain‑specific actions.
        """
        # Very generic placeholder actions – real systems will replace these.
        return [
            Step(name="retrieve_memory", params={"key": goal}),
            Step(name="update_state", params={"key": "last_goal", "value": goal}),
            Step(name="communicate", params={"message": f"Goal {goal} achieved?"}),
        ]

    # ---------------------------------------------------------------------
    # Internal search algorithm (depth‑first with back‑tracking)
    # ---------------------------------------------------------------------
    def _search(
        self,
        goal: Any,
        context: Dict[str, Any],
        plan: List[Step],
        depth: int,
    ) -> bool:
        """Recursive depth‑first search.

        Returns ``True`` when a complete plan has been assembled.  The search
        stops when ``depth`` reaches ``self.max_depth``.
        """
        if depth >= self.max_depth:
            logger.debug("Maximum depth reached (%s)", self.max_depth)
            return False

        candidates = self._expand(goal, context)
        logger.debug("Depth %s – %s candidate(s)", depth, len(candidates))

        for step in candidates:
            if not step.is_applicable(context):
                logger.debug("Step %s not applicable, skipping", step.name)
                continue

            # Simulate applying the step – in a real system this would mutate a
            # copy of the context.  Here we just log and assume it moves us
            # closer to the goal.
            logger.info("Applying step %s (depth %s)", step.name, depth)
            plan.append(step)

            # Simple termination condition: if the step name matches the goal
            # string we consider the plan complete.  This is a placeholder for
            # a more sophisticated evaluation function.
            if isinstance(goal, str) and step.name == goal:
                logger.info("Goal satisfied by step %s", step.name)
                return True

            # Recurse – give the next step a chance to finish the plan.
            if self._search(goal, context, plan, depth + 1):
                return True

            # Backtrack – remove the step and try the next candidate.
            logger.debug("Backtracking from step %s", step.name)
            plan.pop()

        return False

    # ---------------------------------------------------------------------
    # Utility helpers
    # ---------------------------------------------------------------------
    def validate_step(self, step: Step, context: Dict[str, Any]) -> bool:
        """Public wrapper around ``Step.is_applicable`` for external callers."""
        return step.is_applicable(context)

    def backtrack(self, plan: List[Step]) -> List[Step]:
        """Return a new plan with the last step removed (simple back‑track)."""
        if not plan:
            return []
        return plan[:-1]


# End of Planner implementation
