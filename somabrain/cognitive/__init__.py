"""
Cognitive Enhancements package for SomaBrain.

Provides higher‑level cognitive capabilities such as multi‑step planning,
emotional state modelling, and collaborative agent interaction.
"""

from .collaboration import CollaborationManager
from .emotion import EmotionModel
from .planning import Planner

__all__ = ["Planner", "EmotionModel", "CollaborationManager"]