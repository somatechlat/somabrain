"""
Thalamus Module for SomaBrain.

This module implements the thalamus router, which serves as a sensory gateway and attention filter
for the brain-inspired cognitive architecture. The thalamus modulates incoming sensory information
based on current attention levels and neuromodulator states, controlling information flow to higher
cognitive regions.

Key Features:
- Attention-based input filtering
- Neuromodulator-driven arousal modulation
- Dynamic attention level adaptation
- Sensory input normalization and routing

Classes:
    ThalamusRouter: Main router class for sensory input processing and filtering.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from .neuromodulators import NeuromodState


class ThalamusRouter:
    """
    Thalamus router for sensory input filtering and modulation.

    The ThalamusRouter acts as a gatekeeper for incoming sensory information, filtering and
    modulating inputs based on current attention levels and neuromodulator states. It implements
    attention-driven processing where low attention filters out unimportant signals, while high
    attention amplifies important ones.

    Attributes:
        attention_filter (float): Current attention level (0.0 to 1.0).
        last_update (float): Timestamp of last attention update.

    Example:
        >>> router = ThalamusRouter()
        >>> neuromod = NeuromodState()
        >>> input_data = {'importance': 0.8, 'data': 'sensory_input'}
        >>> filtered = router.filter_input(input_data, neuromod)
    """

    def __init__(self):
        """
        Initialize the ThalamusRouter with baseline attention level.

        Sets up the router with a default attention filter of 0.5 and records the initialization
        timestamp for attention decay calculations.
        """
        self.attention_filter = 0.5  # baseline attention level
        self.last_update = time.time()

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize incoming payload data.

        This is a placeholder method for payload normalization. In a full implementation,
        this would handle data format standardization, validation, and basic preprocessing
        before routing to cognitive regions.

        Args:
            payload (Dict[str, Any]): Raw input payload to normalize.

        Returns:
            Dict[str, Any]: Normalized payload dictionary.

        Note:
            Currently returns the payload unchanged. Rate limiting and authentication
            should be handled elsewhere in the pipeline.
        """
        # simple normalization placeholder; add rate limits/auth elsewhere
        return dict(payload)

    def filter_input(
        self, input_data: Dict[str, Any], neuromod: NeuromodState
    ) -> Dict[str, Any]:
        """
        Filter and modulate incoming sensory input based on attention and neuromodulators.

        Updates attention levels based on neuromodulator states (noradrenaline for arousal,
        acetylcholine for focus) and filters input data accordingly. Low attention filters
        out unimportant signals, while high attention processes all input and amplifies
        important signals.

        Args:
            input_data (Dict[str, Any]): Incoming sensory data with optional 'importance' key.
            neuromod (NeuromodState): Current neuromodulator state for attention modulation.

        Returns:
            Dict[str, Any]: Filtered input data, potentially empty if filtered out, or
                           with 'amplified' flag if important signal under high attention.

        Example:
            >>> neuromod = NeuromodState(noradrenaline=0.8, acetylcholine=0.6)
            >>> data = {'importance': 0.9, 'signal': 'important_info'}
            >>> filtered = router.filter_input(data, neuromod)
            >>> print(filtered.get('amplified', False))
            True
        """
        # Update attention based on neuromodulators
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time

        # Noradrenaline increases attention/arousal
        attention_boost = neuromod.noradrenaline * 2.0
        # Acetylcholine increases focus
        focus_boost = neuromod.acetylcholine * 1.5

        self.attention_filter = min(
            1.0, self.attention_filter + (attention_boost + focus_boost) * dt
        )
        # Decay attention over time
        self.attention_filter = max(0.1, self.attention_filter * (1.0 - 0.1 * dt))

        # Filter input based on attention level
        if self.attention_filter < 0.3:
            # Low attention: only process high-importance signals
            if input_data.get("importance", 0) < 0.7:
                return {}  # Filter out low-importance input
        elif self.attention_filter > 0.8:
            # High attention: process all input but amplify important signals
            if input_data.get("importance", 0) > 0.5:
                input_data["amplified"] = True

        return input_data

    def get_attention_level(self) -> float:
        """
        Get the current attention level.

        Returns:
            float: Current attention filter value between 0.1 and 1.0.
        """
        return self.attention_filter
