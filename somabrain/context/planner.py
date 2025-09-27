"""Context-aware planner for Evaluate API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from somabrain.learning import UtilityWeights


@dataclass
class PlanCandidate:
    prompt: str
    utility: float
    notes: str = ""


@dataclass
class PlanResult:
    prompt: str
    utility: float
    candidates: List[PlanCandidate]


class ContextPlanner:
    def __init__(self, utility_weights: UtilityWeights | None = None) -> None:
        self._utility = utility_weights or UtilityWeights()

    @property
    def utility_weights(self) -> UtilityWeights:
        return self._utility

    def plan(self, bundle) -> PlanResult:
        candidates = self._generate_candidates(bundle)
        ranked = sorted(candidates, key=lambda c: c.utility, reverse=True)
        best = ranked[0] if ranked else PlanCandidate(prompt=bundle.prompt, utility=0.0)
        return PlanResult(prompt=best.prompt, utility=best.utility, candidates=ranked)

    def _generate_candidates(self, bundle) -> List[PlanCandidate]:
        base = PlanCandidate(
            prompt=bundle.prompt, utility=self._score(bundle, bundle.prompt)
        )
        summaries = self._memory_highlights(bundle)
        candidates = [base]
        candidates.extend(summaries)
        return candidates

    def _memory_highlights(self, bundle) -> List[PlanCandidate]:
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
            results.append(
                PlanCandidate(prompt=prompt, utility=util, notes=f"highlight:{mem.id}")
            )
        return results

    def _score(self, bundle, prompt: str, emphasis: float = 1.0) -> float:
        length_penalty = len(prompt) / 1024.0
        context_gain = sum(bundle.weights) * emphasis
        return (
            self._utility.lambda_ * context_gain
            - self._utility.mu * length_penalty
            - self._utility.nu * (len(bundle.memories) / 10.0)
        )
