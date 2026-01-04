"""Amygdala-like salience: compute novelty/error-driven gates.

Scores inputs with neuromod modulation and emits store/act gates (hard/soft).

VIBE Compliance:
    - Uses direct imports from metrics.salience (no lazy imports for circular avoidance)
    - FD metrics imported at module level (no circular deps)
    - All metrics calls are best-effort (silent failure on metrics errors)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .metrics.salience import (
    FD_ENERGY_CAPTURE,
    FD_PSD_INVARIANT,
    FD_RESIDUAL,
    FD_TRACE_ERROR,
)
from .neuromodulators import NeuromodState
from .salience import FDSalienceSketch

logger = logging.getLogger(__name__)


def _get_settings():
    """Lazy settings access to avoid circular imports."""
    from django.conf import settings

    return settings


@dataclass
class SalienceConfig:
    """
    Configuration for salience computation in the amygdala-like component.

    Attributes
    ----------
    w_novelty : float
        Weight for novelty in salience score.
    w_error : float
        Weight for prediction error in salience score.
    threshold_store : float
        Threshold for store gate activation.
    threshold_act : float
        Threshold for act gate activation.
    hysteresis : float
        Hysteresis value for gate stability.
    use_soft : bool, optional
        Whether to use soft gating (default: False).
    soft_temperature : float, optional
        Temperature for soft gating sigmoid (default from Settings).
        method : str, optional
            Salience pathway to use: ``"dense"`` (default) or ``"fd"``.
        w_fd : float, optional
            Weight for FD residual energy when ``method="fd"``.
        fd_energy_floor : float, optional
            Minimum acceptable energy capture before adding corrective boost (default from Settings).
    """

    w_novelty: float
    w_error: float
    threshold_store: float
    threshold_act: float
    hysteresis: float
    use_soft: bool = False
    soft_temperature: Optional[float] = None
    method: str = "dense"
    w_fd: float = 0.0
    fd_energy_floor: Optional[float] = None

    def __post_init__(self) -> None:
        """Apply Settings defaults for None values."""
        if self.soft_temperature is None:
            self.soft_temperature = getattr(_get_settings(), "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE", 0.1)
        if self.fd_energy_floor is None:
            self.fd_energy_floor = getattr(_get_settings(), "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.9)


class AmygdalaSalience:
    """
    Salience scorer with hysteresis and optional soft gating.

    Computes salience scores based on novelty and prediction error, modulated by neuromodulators.
    Provides hard or soft gating for store and act decisions.
    """

    def __init__(
        self,
        cfg: SalienceConfig,
        fd_backend: Optional[FDSalienceSketch] = None,
    ):
        """
        Initialize the AmygdalaSalience component.

        Parameters
        ----------
        cfg : SalienceConfig
            Configuration for salience computation.
        """
        self.cfg = cfg
        self._last_store = False
        self._last_act = False
        self._method = (cfg.method or "dense").lower()
        if self._method not in {"dense", "fd"}:
            raise ValueError(f"Unknown salience method: {cfg.method}")
        if self._method == "fd":
            if fd_backend is None:
                raise ValueError("FD salience requires an FDSalienceSketch backend")
            self._fd = fd_backend
        else:
            self._fd = None
        self._last_fd_residual = 0.0
        self._last_fd_capture = 1.0

    def score(
        self,
        novelty: float,
        pred_error: float,
        neuromod: NeuromodState,
        wm_vector: Optional[np.ndarray] = None,
    ) -> float:
        """
        Compute salience score from novelty and prediction error.

        Parameters
        ----------
        novelty : float
            Novelty value [0, 1].
        pred_error : float
            Prediction error value [0, 1].
        neuromod : NeuromodState
            Current neuromodulator state.
        wm_vector : Optional[np.ndarray]
            Working-memory vector providing FD energy signals when the FD
            salience pathway is enabled. Ignored for dense salience.

        Returns
        -------
        float
            Salience score [0, 1].
        """
        # modulate error weight by dopamine
        w_err = max(0.2, min(0.8, neuromod.dopamine))
        s = (self.cfg.w_novelty * float(novelty)) + (
            self.cfg.w_error * float(pred_error)
        )
        s += (w_err - self.cfg.w_error) * float(pred_error)
        fd_boost = 0.0
        if self._method == "fd" and self._fd is not None:
            if wm_vector is None:
                raise ValueError("FD salience requires wm_vector for scoring")
            residual_ratio, capture_ratio = self._fd.observe(wm_vector)
            self._last_fd_residual = residual_ratio
            self._last_fd_capture = capture_ratio
            fd_boost = self.cfg.w_fd * max(0.0, residual_ratio)
            if capture_ratio < self.cfg.fd_energy_floor:
                fd_boost += self.cfg.w_fd * (self.cfg.fd_energy_floor - capture_ratio)
            try:
                FD_ENERGY_CAPTURE.set(capture_ratio)
                FD_RESIDUAL.observe(residual_ratio)
                stats = self._fd.stats()
                FD_TRACE_ERROR.set(stats["trace_norm_error"])
                FD_PSD_INVARIANT.set(1.0 if stats["psd_ok"] else 0.0)
            except Exception as exc:
                logger.debug("Failed to record FD salience metrics: %s", exc)
        else:
            self._last_fd_residual = 0.0
            self._last_fd_capture = 1.0
        s += fd_boost
        # ACh increases focus -> require higher novelty
        s += float(neuromod.acetylcholine)
        # bound
        return max(0.0, min(1.0, s))

    def gates(self, s: float, neuromod: NeuromodState) -> tuple[bool, bool]:
        """
        Compute store and act gates from salience score.

        Parameters
        ----------
        s : float
            Salience score [0, 1].
        neuromod : NeuromodState
            Current neuromodulator state.

        Returns
        -------
        tuple[bool, bool]
            (do_store, do_act) gate decisions.
        """
        th_store, th_act = self._thresholds(neuromod)
        if self.cfg.use_soft:
            ps, pa = self.gate_probs(s, neuromod)
            do_store = ps >= 0.5
            do_act = pa >= 0.5
        else:
            do_store = s >= th_store
            do_act = s >= th_act
        self._last_store = do_store
        self._last_act = do_act
        return do_store, do_act

    @property
    def last_fd_residual(self) -> float:
        """Execute last fd residual.
            """

        return float(self._last_fd_residual)

    @property
    def last_fd_capture(self) -> float:
        """Execute last fd capture.
            """

        return float(self._last_fd_capture)

    def gate_probs(self, s: float, neuromod: NeuromodState) -> tuple[float, float]:
        """
        Compute soft gate probabilities via sigmoid around thresholds.

        Parameters
        ----------
        s : float
            Salience score [0, 1].
        neuromod : NeuromodState
            Current neuromodulator state.

        Returns
        -------
        tuple[float, float]
            (p_store, p_act) probabilities [0, 1].
        """
        th_store, th_act = self._thresholds(neuromod)
        if not self.cfg.use_soft:
            return (1.0 if s >= th_store else 0.0, 1.0 if s >= th_act else 0.0)
        T = max(1e-4, float(self.cfg.soft_temperature))

        def _sig(x: float) -> float:
            # numerically stable sigmoid
            """Execute sig.

                Args:
                    x: The x.
                """

            import math

            x = max(-20.0, min(20.0, x))
            return 1.0 / (1.0 + math.exp(-x))

        ps = _sig((s - th_store) / T)
        pa = _sig((s - th_act) / T)
        return ps, pa

    def _thresholds(self, neuromod: NeuromodState) -> tuple[float, float]:
        # NE raises thresholds under urgency
        """Execute thresholds.

            Args:
                neuromod: The neuromod.
            """

        th_store = self.cfg.threshold_store + float(neuromod.noradrenaline)
        th_act = self.cfg.threshold_act + float(neuromod.noradrenaline)
        # hysteresis to avoid flapping
        if self._last_store:
            th_store -= self.cfg.hysteresis
        if self._last_act:
            th_act -= self.cfg.hysteresis
        return th_store, th_act