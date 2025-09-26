"""Amygdala-like salience: compute novelty/error-driven gates.

Scores inputs with neuromod modulation and emits store/act gates (hard/soft).
"""

from __future__ import annotations

from dataclasses import dataclass

from .neuromodulators import NeuromodState


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
        Temperature for soft gating sigmoid (default: 0.15).
    """

    w_novelty: float
    w_error: float
    threshold_store: float
    threshold_act: float
    hysteresis: float
    use_soft: bool = False
    soft_temperature: float = 0.15


class AmygdalaSalience:
    """
    Salience scorer with hysteresis and optional soft gating.

    Computes salience scores based on novelty and prediction error, modulated by neuromodulators.
    Provides hard or soft gating for store and act decisions.
    """

    def __init__(self, cfg: SalienceConfig):
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

    def score(
        self, novelty: float, pred_error: float, neuromod: NeuromodState
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

        Returns
        -------
        float
            Salience score [0, 1].
        """
        # modulate error weight by dopamine
        w_err = max(0.2, min(0.8, neuromod.dopamine))
        s = (self.cfg.w_novelty * float(novelty)) + (w_err * float(pred_error))
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
            import math

            x = max(-20.0, min(20.0, x))
            return 1.0 / (1.0 + math.exp(-x))

        ps = _sig((s - th_store) / T)
        pa = _sig((s - th_act) / T)
        return ps, pa

    def _thresholds(self, neuromod: NeuromodState) -> tuple[float, float]:
        # NE raises thresholds under urgency
        th_store = self.cfg.threshold_store + float(neuromod.noradrenaline)
        th_act = self.cfg.threshold_act + float(neuromod.noradrenaline)
        # hysteresis to avoid flapping
        if self._last_store:
            th_store -= self.cfg.hysteresis
        if self._last_act:
            th_act -= self.cfg.hysteresis
        return th_store, th_act
