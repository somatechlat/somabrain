"""Adaptive parameter utilities for SomaBrain.

This package provides small, real implementations of adaptive parameters and
performance metrics used by neuromodulators and (optionally) adaptive scorers.
"""

from .core import AdaptiveParameter, PerformanceMetrics
from .integration import AdaptiveIntegrator

__all__ = ["AdaptiveParameter", "PerformanceMetrics", "AdaptiveIntegrator"]
