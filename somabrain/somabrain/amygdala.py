from __future__ import annotations

from dataclasses import dataclass
from .neuromodulators import NeuromodState


@dataclass
class SalienceConfig:
    w_novelty: float
    w_error: float
    threshold_store: float
    threshold_act: float
    hysteresis: float
    use_soft: bool = False
    soft_temperature: float = 0.15


class AmygdalaSalience:
    def __init__(self, cfg: SalienceConfig):
        self.cfg = cfg
        self._last_store = False
        self._last_act = False

    def score(self, novelty: float, pred_error: float, neuromod: NeuromodState) -> float:
        # modulate error weight by dopamine
        w_err = max(0.2, min(0.8, neuromod.dopamine))
        s = (self.cfg.w_novelty * float(novelty)) + (w_err * float(pred_error))
        # ACh increases focus -> require higher novelty
        s += float(neuromod.acetylcholine)
        # bound
        return max(0.0, min(1.0, s))

    def gates(self, s: float, neuromod: NeuromodState) -> tuple[bool, bool]:
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
        """Soft gate probabilities via sigmoid around thresholds.

        Returns (p_store, p_act) in [0,1]. If soft disabled, returns 1.0/0.0 as hard outcomes.
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
