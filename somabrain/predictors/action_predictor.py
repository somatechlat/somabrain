"""Action predictor service implementation.

Provides a concrete predictor for the *action* domain. It builds on the generic
``HeatDiffusionPredictor`` defined in ``base.py`` and reads its configuration
from the global ``settings`` object (``common.config.settings``). All tunable
parameters are sourced from ``settings`` – no hard‑coded values – satisfying the
VIBE requirement for a single source of truth.
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np

from common.config.settings import settings
shared_settings = settings
from .base import HeatDiffusionPredictor, PredictorConfig, load_operator_from_file


def _load_action_operator() -> Tuple[callable, int]:
    """Load the Laplacian operator for the *action* domain.

    The environment variable ``SOMABRAIN_GRAPH_FILE_ACTION`` is consulted first;
    if not set, ``SOMABRAIN_GRAPH_FILE`` is used as a fallback. When neither is
    defined a ``RuntimeError`` is raised – this matches the VIBE rule of failing
    fast on missing configuration.
    """
    graph_path = settings.getenv("SOMABRAIN_GRAPH_FILE_ACTION") or settings.getenv(
        "SOMABRAIN_GRAPH_FILE"
    )
    if not graph_path:
        raise RuntimeError(
            "Action predictor requires a graph file. Set SOMABRAIN_GRAPH_FILE_ACTION or SOMABRAIN_GRAPH_FILE."
        )
    return load_operator_from_file(graph_path)


class ActionPredictor(HeatDiffusionPredictor):
    """Predictor for the *action* domain.

    The constructor builds the underlying ``HeatDiffusionPredictor`` using the
    operator loaded by :func:`_load_action_operator` and a ``PredictorConfig``
    derived from the global ``settings``.
    """

    def __init__(self) -> None:
        apply_A, dim = _load_action_operator()
        cfg = PredictorConfig(
            diffusion_t=getattr(shared_settings, "diffusion_t", 0.5),
            alpha=getattr(shared_settings, "predictor_alpha", 2.0),
            chebyshev_K=getattr(shared_settings, "chebyshev_K", 30),
            lanczos_m=getattr(shared_settings, "lanczos_m", 20),
        )
        super().__init__(apply_A=apply_A, dim=dim, cfg=cfg)

    def predict(self, source_idx: int, observed: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """Run a single prediction step for the action domain.

        Parameters
        ----------
        source_idx: int
            Index of the one‑hot source vector.
        observed: np.ndarray
            Observed vector against which error and confidence are computed.

        Returns
        -------
        Tuple[np.ndarray, float, float]
            ``(salience, error, confidence)``
        """
        return self.step(source_idx, observed)
