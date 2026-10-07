"""Amygdala-like salience: compute novelty/error-driven gates.

Scores inputs with neuromod modulation and emits store/act gates (hard/soft).

Neuromod couplings (W2.5):
- Dopamine modulates the prediction-error weight of the salience score.
- Acetylcholine (attention demand) adds to salience so attended input is
  more likely to be stored and acted on.
- Noradrenaline raises both gate thresholds (urgency focuses action).
- Serotonin provides **response smoothing**: higher 5-HT increases gate
  hysteresis and the soft-gate temperature, so decisions flap less.

VAD couplings (W6.3 / T82) — optional arguments on ``score`` / ``gates``:
- ``affect_boost`` adds an arousal/valence salience term.
- ``temperature_scale`` multiplies the soft-gate temperature (arousal sharpens).
- ``threshold_offset`` shifts both gate thresholds (dominance lowers them).

VIBE Compliance:
    - Direct imports of metrics and salience backends (no lazy import shims)
    - All metrics calls are best-effort (silent failure on metrics errors)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from somabrain.admin.core.learning.salience import FDSalienceSketch
from somabrain.metrics.salience import (
    FD_ENERGY_CAPTURE,
    FD_PSD_INVARIANT,
    FD_RESIDUAL,
    FD_TRACE_ERROR,
)
from somabrain.runtime.neuromodulators import NeuromodState

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
    soft_temperature: float | None = None
    method: str = "dense"
    w_fd: float = 0.0
    fd_energy_floor: float | None = None

    def __post_init__(self) -> None:
        """Apply Settings defaults for None values."""
        if self.soft_temperature is None:
            self.soft_temperature = getattr(
                _get_settings(), "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE", 0.1
            )
        if self.fd_energy_floor is None:
            self.fd_energy_floor = getattr(
                _get_settings(), "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.9
            )


class AmygdalaSalience:
    """
    Salience scorer with hysteresis and optional soft gating.

    Computes salience scores based on novelty and prediction error, modulated by neuromodulators.
    Provides hard or soft gating for store and act decisions.
    """

    def __init__(
        self,
        cfg: SalienceConfig,
        fd_backend: FDSalienceSketch | None = None,
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
        wm_vector: np.ndarray | None = None,
        affect_boost: float = 0.0,
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
        affect_boost : float
            Optional VAD salience contribution (T82). Added after the
            neuromodulator terms; default 0.0 preserves the dense path.

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
        # ACh is attention demand: attended input gains salience (stored/acted)
        s += float(neuromod.acetylcholine)
        # VAD affect (T82): arousal/valence boost from EmotionModel
        s += float(affect_boost)
        # bound
        return max(0.0, min(1.0, s))

    def gates(
        self,
        s: float,
        neuromod: NeuromodState,
        *,
        temperature_scale: float = 1.0,
        threshold_offset: float = 0.0,
    ) -> tuple[bool, bool]:
        """
        Compute store and act gates from salience score.

        Parameters
        ----------
        s : float
            Salience score [0, 1].
        neuromod : NeuromodState
            Current neuromodulator state.
        temperature_scale : float
            Multiplier on the soft-gate temperature (T82 arousal coupling).
            1.0 leaves the configured temperature unchanged. Must be > 0.
        threshold_offset : float
            Added to both gate thresholds (T82 dominance coupling). Negative
            values lower thresholds. Must be finite.

        Returns
        -------
        tuple[bool, bool]
            (do_store, do_act) gate decisions.
        """
        th_store, th_act = self._thresholds(neuromod)
        th_store += float(threshold_offset)
        th_act += float(threshold_offset)
        if self.cfg.use_soft:
            ps, pa = self.gate_probs(
                s,
                neuromod,
                temperature_scale=temperature_scale,
                threshold_offset=threshold_offset,
            )
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
        """Execute last fd residual."""

        return float(self._last_fd_residual)

    @property
    def last_fd_capture(self) -> float:
        """Execute last fd capture."""

        return float(self._last_fd_capture)

    def gate_probs(
        self,
        s: float,
        neuromod: NeuromodState,
        *,
        temperature_scale: float = 1.0,
        threshold_offset: float = 0.0,
    ) -> tuple[float, float]:
        """
        Compute soft gate probabilities via sigmoid around thresholds.

        Parameters
        ----------
        s : float
            Salience score [0, 1].
        neuromod : NeuromodState
            Current neuromodulator state.
        temperature_scale : float
            Multiplier on the 5-HT-smoothed soft temperature (T82 arousal).
        threshold_offset : float
            Added to both thresholds (T82 dominance).

        Returns
        -------
        tuple[float, float]
            (p_store, p_act) probabilities [0, 1].
        """
        th_store, th_act = self._thresholds(neuromod)
        th_store += float(threshold_offset)
        th_act += float(threshold_offset)
        if not self.cfg.use_soft:
            return (1.0 if s >= th_store else 0.0, 1.0 if s >= th_act else 0.0)
        # 5-HT response smoothing: higher stability widens the sigmoid
        stability = max(0.0, min(1.0, float(neuromod.serotonin)))
        scale = float(temperature_scale)
        if not math.isfinite(scale) or scale <= 0.0:
            scale = 1.0
        T = max(1e-4, float(self.cfg.soft_temperature) * (1.0 + stability) * scale)

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
        """Gate thresholds with NE and 5-HT couplings.

        NE raises thresholds under urgency. 5-HT provides response smoothing:
        effective hysteresis is ``hysteresis · (1 + serotonin)``, so a stable
        (high 5-HT) system keeps gates sticky and flaps less.
        """
        th_store = self.cfg.threshold_store + float(neuromod.noradrenaline)
        th_act = self.cfg.threshold_act + float(neuromod.noradrenaline)
        # hysteresis to avoid flapping, scaled by serotonergic stability
        hyst = self.cfg.hysteresis * (1.0 + max(0.0, min(1.0, neuromod.serotonin)))
        if self._last_store:
            th_store -= hyst
        if self._last_act:
            th_act -= hyst
        return th_store, th_act
