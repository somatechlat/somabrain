from __future__ import annotations

from typing import Dict, Any
from .neuromodulators import NeuromodState
import time


class ThalamusRouter:
    def __init__(self):
        self.attention_filter = 0.5  # baseline attention level
        self.last_update = time.time()

    def normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # simple normalization placeholder; add rate limits/auth elsewhere
        return dict(payload)

    def filter_input(self, input_data: Dict[str, Any], neuromod: NeuromodState) -> Dict[str, Any]:
        """Filter and modulate incoming sensory input based on attention and neuromodulators."""
        # Update attention based on neuromodulators
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time

        # Noradrenaline increases attention/arousal
        attention_boost = neuromod.noradrenaline * 2.0
        # Acetylcholine increases focus
        focus_boost = neuromod.acetylcholine * 1.5

        self.attention_filter = min(1.0, self.attention_filter + (attention_boost + focus_boost) * dt)
        # Decay attention over time
        self.attention_filter = max(0.1, self.attention_filter * (1.0 - 0.1 * dt))

        # Filter input based on attention level
        if self.attention_filter < 0.3:
            # Low attention: only process high-importance signals
            if input_data.get('importance', 0) < 0.7:
                return {}  # Filter out low-importance input
        elif self.attention_filter > 0.8:
            # High attention: process all input but amplify important signals
            if input_data.get('importance', 0) > 0.5:
                input_data['amplified'] = True

        return input_data

    def get_attention_level(self) -> float:
        return self.attention_filter

