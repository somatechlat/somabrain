"""Context-aware planner for Evaluate API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from somabrain.learning import UtilityWeights

from django.conf import settings


@dataclass
class PlanCandidate:
    """Plancandidate class implementation."""

    prompt: str
    utility: float
    notes: str = ""


@dataclass
class PlanResult:
    """Planresult class implementation."""

    prompt: str
    utility: float
    candidates: List[PlanCandidate]


class ContextPlanner:
    """Context-aware planner using utility-based scoring.

    Configuration via Settings:
    - SOMABRAIN_PLANNER_LENGTH_PENALTY_SCALE: Scale for prompt length penalty (default 1024.0)
    - SOMABRAIN_PLANNER_MEMORY_PENALTY_SCALE: Scale for memory count penalty (default 10.0)
    """

    def __init__(self, utility_weights: UtilityWeights | None = None) -> None:
        """Initialize the instance."""

        self._utility = utility_weights or UtilityWeights()
        # Load configuration from centralized Settings
        self._length_penalty_scale = float(settings.planner_length_penalty_scale)
        self._memory_penalty_scale = float(settings.planner_memory_penalty_scale)
        # Ensure positive values
        if self._length_penalty_scale <= 0:
            self._length_penalty_scale = 1024.0
        if self._memory_penalty_scale <= 0:
            self._memory_penalty_scale = 10.0

    @property
    def utility_weights(self) -> UtilityWeights:
        """Execute utility weights."""

        return self._utility

    def plan(self, bundle) -> PlanResult:
        """Execute plan.

        Args:
            bundle: The bundle.
        """

        candidates = self._generate_candidates(bundle)
        ranked = sorted(candidates, key=lambda c: c.utility, reverse=True)
        best = ranked[0] if ranked else PlanCandidate(prompt=bundle.prompt, utility=0.0)
        return PlanResult(prompt=best.prompt, utility=best.utility, candidates=ranked)

    def _generate_candidates(self, bundle) -> List[PlanCandidate]:
        """Execute generate candidates.

        Args:
            bundle: The bundle.
        """

        base = PlanCandidate(prompt=bundle.prompt, utility=self._score(bundle, bundle.prompt))
        summaries = self._memory_highlights(bundle)
        candidates = [base]
        candidates.extend(summaries)
        return candidates

    def _memory_highlights(self, bundle) -> List[PlanCandidate]:
        """Execute memory highlights.

        Args:
            bundle: The bundle.
        """

        results: List[PlanCandidate] = []
        for mem, weight in zip(bundle.memories, bundle.weights, strict=False):
            text = mem.metadata.get("text") or mem.metadata.get("content")
            if not text:
                continue
            prompt = (
                f"Context:\n[{mem.id}]\n{text}\n\n"
                f"Query:\n{bundle.query}\n\n"
                "Respond succinctly using the cited memory."
            )
            util = self._score(bundle, prompt, emphasis=weight)
            results.append(PlanCandidate(prompt=prompt, utility=util, notes=f"highlight:{mem.id}"))
        return results

    def _score(self, bundle, prompt: str, emphasis: float = 1.0) -> float:
        """Execute score.

        Args:
            bundle: The bundle.
            prompt: The prompt.
            emphasis: The emphasis.
        """

        length_penalty = len(prompt) / max(self._length_penalty_scale, 1.0)
        context_gain = sum(bundle.weights) * emphasis
        memory_penalty = len(bundle.memories) / max(self._memory_penalty_scale, 1.0)
        return (
            self._utility.lambda_ * context_gain
            - self._utility.mu * length_penalty
            - self._utility.nu * memory_penalty
        )
