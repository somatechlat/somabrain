"""Thalamus router for sensory gating and attention modulation.

The thalamus acts as a relay and filtering station for incoming requests,
normalizing input data and applying attention-based filtering based on
neuromodulator state. This mirrors the biological thalamus which gates
sensory information before it reaches the cortex.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


class ThalamusRouter:
    """Thalamic router providing input normalization and attention gating.

    The thalamus performs three key functions:
    1. Route registration for endpoint handlers
    2. Input normalization to ensure consistent data format
    3. Attention-based filtering using neuromodulator state
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        self.routes: List[Tuple[str, Callable[..., Any]]] = []
        self._attention_level: float = 1.0

    def register(self, path: str, handler: Callable[..., Any]) -> None:
        """Register a route handler."""
        self.routes.append((path, handler))

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize input data for consistent processing.

        Ensures all expected fields are present with appropriate defaults
        and strips/cleans string values.
        """
        if not isinstance(data, dict):
            return {"query": str(data) if data else ""}

        normalized = dict(data)

        # Normalize string fields
        for key in ("query", "content", "text"):
            if key in normalized and isinstance(normalized[key], str):
                normalized[key] = normalized[key].strip()

        # Ensure k has a sensible default
        if "k" not in normalized:
            normalized["k"] = 10

        return normalized

    def filter_input(
        self,
        data: Dict[str, Any],
        neuromodulator_state: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Apply attention-based filtering to input data.

        Uses neuromodulator state (dopamine, noradrenaline, etc.) to
        modulate attention level and filter input accordingly.
        """
        if neuromodulator_state is None:
            return data

        # Extract attention-relevant neuromodulators from NeuromodState dataclass
        dopamine = getattr(neuromodulator_state, "dopamine", 0.5)
        noradrenaline = getattr(neuromodulator_state, "noradrenaline", 0.0)
        acetylcholine = getattr(neuromodulator_state, "acetylcholine", 0.0)

        # Compute attention level from neuromodulator state
        # High dopamine + noradrenaline + acetylcholine = high attention/focus
        self._attention_level = min(
            1.0, (dopamine + noradrenaline + acetylcholine) / 2.0 + 0.5
        )

        # Pass through data unchanged - attention affects downstream processing
        return data

    def get_attention_level(self) -> float:
        """Return current attention level (0.0 to 1.0)."""
        return self._attention_level

    def __repr__(self) -> str:
        """Return object representation."""

        return f"<ThalamusRouter routes={len(self.routes)} attention={self._attention_level:.2f}>"
