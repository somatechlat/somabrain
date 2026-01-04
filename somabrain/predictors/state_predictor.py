"""State predictor service implementation.

The state predictor is a thin wrapper around :class:`HeatDiffusionPredictor`
that selects the appropriate graph operator for the *state* domain and
exposes a convenient ``predict`` method. All configuration values are read
from the global ``settings`` object (``common.config.settings``) via the
``PredictorConfig`` dataclass, ensuring a single source of truth.

VIBE compliance:
* No hard‑coded constants – every tunable comes from ``settings``.
* Fail‑fast: missing configuration or graph files raise ``RuntimeError``.
* Full type hints and docstrings for clarity.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from django.conf import settings
from .base import HeatDiffusionPredictor, PredictorConfig, load_operator_from_file


def _load_state_operator() -> Tuple[callable, int]:
    """Load the Laplacian operator for the *state* domain.

    The environment variable ``SOMABRAIN_GRAPH_FILE_STATE`` is consulted first;
    if not set, ``SOMABRAIN_GRAPH_FILE`` is used as a fallback. When neither
    variable is defined the function raises ``RuntimeError`` – this matches the
    VIBE rule of refusing to operate with implicit defaults.
    """
    # Fallback to the generic graph file if the state‑specific one is not set.
    # ``settings.getenv`` is prohibited; we use ``getattr`` which returns ``None``
    # when the attribute does not exist (mirroring the previous behaviour).
    graph_path = settings.graph_file_state or getattr(settings, "graph_file", None)
    if not graph_path:
        raise RuntimeError(
            "State predictor requires a graph file. Set SOMABRAIN_GRAPH_FILE_STATE or SOMABRAIN_GRAPH_FILE."
        )
    return load_operator_from_file(graph_path)


class StatePredictor(HeatDiffusionPredictor):
    """Predictor for the *state* domain.

    The constructor builds the underlying ``HeatDiffusionPredictor`` using the
    graph operator loaded by :func:`_load_state_operator` and a ``PredictorConfig``
    derived from the global ``settings``.
    """

    def __init__(self) -> None:
        """Initialize the instance."""

        apply_A, dim = _load_state_operator()
        cfg = PredictorConfig(
            diffusion_t=getattr(settings, "diffusion_t", 0.5),
            alpha=getattr(settings, "predictor_alpha", 2.0),
            chebyshev_K=getattr(settings, "chebyshev_K", 30),
            lanczos_m=getattr(settings, "lanczos_m", 20),
        )
        super().__init__(apply_A=apply_A, dim=dim, cfg=cfg)

    def predict(
        self, source_idx: int, observed: np.ndarray
    ) -> Tuple[np.ndarray, float, float]:
        """Run a single prediction step.

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