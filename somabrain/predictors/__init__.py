"""Predictors package for SomaBrain.

This package provides concrete predictor services for the three cognitive
domains (state, agent, action). Each predictor is a thin wrapper around the
generic :class:`HeatDiffusionPredictor` defined in ``base.py``. The wrappers
expose a ``predict`` method that receives a source index (or source vector) and
an observed vector, returning the salience vector, error and confidence.

All configuration is read from the global ``settings`` object (``common.config
settings``) via the ``PredictorConfig`` dataclass, ensuring a single source of
truth for diffusion parameters.
"""

from .base import (
    HeatDiffusionPredictor,
    PredictorConfig,
    build_predictor_from_env,
    load_operator_from_file,
)

__all__ = [
    "HeatDiffusionPredictor",
    "PredictorConfig",
    "load_operator_from_file",
    "build_predictor_from_env",
]
