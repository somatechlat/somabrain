"""
Cognitive Enhancements package for SomaBrain.

Provides higher-level cognitive capabilities such as multi-step planning
and emotional state modelling. These modules are on the LIVE eval_step path
(BG/PFC/amygdala/emotion/personality) or used by the planner proofs.
"""

from .emotion import EmotionModel
from .planning import Planner

__all__ = ["EmotionModel", "Planner"]
