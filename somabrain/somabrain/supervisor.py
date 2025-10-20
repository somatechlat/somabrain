from __future__ import annotations

from dataclasses import dataclass
from .neuromodulators import NeuromodState


@dataclass
class SupervisorConfig:
    gain: float = 0.2
    limit: float = 0.1
    alpha_err: float = 1.0
    beta_nov: float = 1.0


class Supervisor:
    def __init__(self, cfg: SupervisorConfig):
        self.cfg = cfg

    def free_energy(self, novelty: float, pred_error: float) -> float:
        # simple proxy: weighted sum (can extend to KL terms later)
        n = float(max(0.0, min(1.0, novelty)))
        e = float(max(0.0, min(1.0, pred_error)))
        return float(self.cfg.alpha_err * e + self.cfg.beta_nov * n)

    def adjust(self, nm: NeuromodState, novelty: float, pred_error: float) -> tuple[NeuromodState, float, float]:
        """Return (modulated neuromod, free_energy, modulation_magnitude)."""
        F = self.free_energy(novelty, pred_error)
        g = float(self.cfg.gain)
        lim = float(self.cfg.limit)
        # proportional adjustments within bounds
        d_da = max(-lim, min(lim, g * pred_error))
        d_ach = max(-lim, min(lim, g * novelty))
        d_ne = max(-lim, min(lim, g * (pred_error + novelty) * 0.5))
        # serotonin unchanged in this proxy; could stabilize thresholds
        new = NeuromodState(
            dopamine=max(0.2, min(0.8, nm.dopamine + d_da)),
            serotonin=max(0.0, min(1.0, nm.serotonin)),
            noradrenaline=max(0.0, min(0.1, nm.noradrenaline + d_ne)),
            acetylcholine=max(0.0, min(0.1, nm.acetylcholine + d_ach)),
            timestamp=nm.timestamp,
        )
        mag = abs(d_da) + abs(d_ach) + abs(d_ne)
        return new, F, mag

