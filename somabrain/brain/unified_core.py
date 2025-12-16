"""Unified Brain Core - Unified mathematical core for memory processing."""

from __future__ import annotations

import time
from typing import Any, Dict

from somabrain.neuromodulators import NeuromodState


class UnifiedBrainCore:
    """Unified mathematical core replacing complex component interactions."""

    def __init__(self, fractal_memory, fnom_memory, neuromods):
        self.fractal = fractal_memory
        self.fnom = fnom_memory
        self.neuromods = neuromods
        self.dopamine_baseline = 0.4
        self.serotonin_baseline = 0.5

    def process_memory(
        self, content: Dict[str, Any], importance: float = 0.8
    ) -> Dict[str, Any]:
        """Single entry point for memory processing."""
        neuro_state = self.neuromods.get_state()
        adjusted_importance = importance * (0.7 + 0.3 * neuro_state.dopamine)
        adjusted_importance = min(1.0, max(0.1, adjusted_importance))

        fractal_nodes = self.fractal.encode_fractal(
            content, importance=adjusted_importance
        )
        fnom_result = self.fnom.encode(content, importance=adjusted_importance)
        self._update_neuromodulators(len(fractal_nodes), fnom_result)

        return {
            "fractal_nodes": len(fractal_nodes),
            "fnom_components": len(fnom_result.frequency_spectrum),
            "adjusted_importance": adjusted_importance,
            "processing_time": time.time(),
            "unified": True,
        }

    def retrieve_memory(self, query: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        """Single entry point for memory retrieval."""
        fractal_results = self.fractal.retrieve_fractal(query, top_k=top_k)
        fnom_results = self.fnom.retrieve(query, top_k=top_k)
        combined_results = self._combine_results(fractal_results, fnom_results, top_k)

        return {
            "results": combined_results,
            "fractal_count": len(fractal_results),
            "fnom_count": len(fnom_results),
            "unified": True,
        }

    def _update_neuromodulators(self, fractal_nodes: int, fnom_result):
        """Update dopamine/serotonin based on processing success."""
        success_score = min(
            1.0, (fractal_nodes + len(fnom_result.frequency_spectrum)) / 50.0
        )

        new_dopamine = self.dopamine_baseline + (success_score - 0.5) * 0.2
        new_dopamine = max(0.2, min(0.8, new_dopamine))

        new_serotonin = self.serotonin_baseline + (success_score - 0.5) * 0.1
        new_serotonin = max(0.3, min(0.7, new_serotonin))

        current_state = self.neuromods.get_state()
        new_state = NeuromodState(
            dopamine=new_dopamine,
            serotonin=new_serotonin,
            noradrenaline=current_state.noradrenaline,
            acetylcholine=current_state.acetylcholine,
            timestamp=time.time(),
        )
        self.neuromods.set_state(new_state)

    def _combine_results(self, fractal_results, fnom_results, top_k):
        """Combine and rank results from both systems."""
        combined = []

        for i, (node, resonance) in enumerate(fractal_results[: top_k // 2]):
            combined.append(
                {
                    "content": node.memory_trace,
                    "score": float(resonance),
                    "system": "fractal",
                    "rank": i + 1,
                }
            )

        for i, (trace, similarity) in enumerate(fnom_results[: top_k // 2]):
            combined.append(
                {
                    "content": trace.content,
                    "score": float(similarity),
                    "system": "fnom",
                    "rank": i + 1,
                }
            )

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:top_k]
