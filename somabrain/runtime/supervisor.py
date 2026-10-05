"""
Supervisor Module for SomaBrain.

Free-energy P-controller for neuromodulator state. Monitors prediction error
and novelty signals and moves the neuromodulators toward their documented
targets using the homeostatic law ``m ← Π(m + η (δ − m))`` (gain ``η`` =
``SupervisorConfig.gain``, step limited by ``SupervisorConfig.limit``).

Shared target laws (single source: ``somabrain.runtime.neuromodulators``):

- ``acetylcholine_target(novelty, pred_error)`` — THE ACh law (attention
  demand). Same law as the adaptive feedback path (DEBT-005).
- ``serotonin_target(pred_error)`` — THE 5-HT law (stability). 5-HT is not
  held constant; it tracks prediction accuracy and is consumed by
  ``AmygdalaSalience`` for response smoothing (DEBT-006).
- ``dopamine_target`` / ``noradrenaline_target`` — DA tracks success
  (``1 − pred_error``), NE tracks arousal (``novelty + pred_error``).

Free energy is the weighted sum ``α_err·pred_error + β_nov·novelty``.

Classes:
    SupervisorConfig: Configuration parameters for supervisor behavior.
    Supervisor: Main supervisor class for free energy minimization and neuromodulation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .neuromodulators import (
    NeuromodState,
    acetylcholine_target,
    dopamine_target,
    noradrenaline_target,
    project,
    serotonin_target,
)


@dataclass
class SupervisorConfig:
    """
    Configuration parameters for the Supervisor system.

    Defines the tuning parameters for free energy minimization and neuromodulator
    adjustment, controlling the sensitivity and bounds of the supervisory control.

    Attributes:
        gain (float): Proportional gain for neuromodulator adjustments. Default 0.2.
        limit (float): Maximum absolute change per adjustment step. Default 0.1.
        alpha_err (float): Weight for prediction error in free energy. Default 1.0.
        beta_nov (float): Weight for novelty in free energy. Default 1.0.

    Example:
        >>> config = SupervisorConfig(gain=0.3, limit=0.15, alpha_err=1.2, beta_nov=0.8)
    """

    gain: float = 0.2
    limit: float = 0.1
    alpha_err: float = 1.0
    beta_nov: float = 1.0


class Supervisor:
    """
    Supervisor for free energy minimization and neuromodulator adjustment.

    Calculates free energy as a weighted sum of prediction error and novelty,
    then moves dopamine, serotonin, noradrenaline and acetylcholine toward the
    shared homeostatic targets. High prediction errors or novelty raise the
    corresponding demands (attention, arousal) and lower stability, which the
    amygdala and the adaptation engine then observe.

    Attributes:
        cfg (SupervisorConfig): Configuration parameters for supervisor behavior.
    """

    def __init__(self, cfg: SupervisorConfig):
        """
        Initialize the Supervisor with configuration.

        Args:
            cfg (SupervisorConfig): Configuration parameters for supervisor behavior.
        """
        self.cfg = cfg
        # EWMA instances for smoothing neuromodulator adjustments
        # Separate EWMA per neuromodulator to smooth deltas over time
        from somabrain.core.utils.stats import EWMA

        self._ewma_da = EWMA(alpha=0.1)  # dopamine delta smoothing
        self._ewma_ach = EWMA(alpha=0.1)  # acetylcholine delta smoothing
        self._ewma_ne = EWMA(alpha=0.1)  # noradrenaline delta smoothing
        self._ewma_5ht = EWMA(alpha=0.1)  # serotonin delta smoothing

    def free_energy(self, novelty: float, pred_error: float) -> float:
        """
        Calculate free energy from novelty and prediction error signals.

        Free energy is computed as a weighted sum of prediction error and novelty,
        serving as a proxy for the system's uncertainty and need for adaptation.

        Args:
            novelty (float): Novelty signal (0.0 to 1.0), higher values indicate more novel input.
            pred_error (float): Prediction error (0.0 to 1.0), higher values indicate worse predictions.

        Returns:
            float: Free energy value as weighted sum of inputs.
        """
        n = float(max(0.0, min(1.0, novelty)))
        e = float(max(0.0, min(1.0, pred_error)))
        return float(self.cfg.alpha_err * e + self.cfg.beta_nov * n)

    def adjust(
        self, nm: NeuromodState, novelty: float, pred_error: float
    ) -> tuple[NeuromodState, float, float]:
        """
        Adjust neuromodulator states based on novelty and prediction error.

        Each modulator is moved toward its shared homeostatic target; the step
        is proportional to the gap (gain) and clipped to ``cfg.limit``, then
        EWMA-smoothed and projected onto ``NEURO_BOUNDS``.

        Args:
            nm (NeuromodState): Current neuromodulator state.
            novelty (float): Current novelty signal (0.0 to 1.0).
            pred_error (float): Current prediction error (0.0 to 1.0).

        Returns:
            tuple[NeuromodState, float, float]: New state, free energy, and
            total modulation magnitude (sum of absolute changes).
        """
        F = self.free_energy(novelty, pred_error)
        g = float(self.cfg.gain)
        lim = float(self.cfg.limit)

        da_t = dopamine_target(1.0 - float(pred_error))
        ach_t = acetylcholine_target(float(novelty), float(pred_error))
        ne_t = noradrenaline_target(0.5 * (float(pred_error) + float(novelty)))
        ht_t = serotonin_target(float(pred_error))

        def _step(current: float, target: float, ewma) -> float:
            raw = max(-lim, min(lim, g * (target - current)))
            return max(-lim, min(lim, ewma.update(raw)["mean"]))

        d_da = _step(nm.dopamine, da_t, self._ewma_da)
        d_ach = _step(nm.acetylcholine, ach_t, self._ewma_ach)
        d_ne = _step(nm.noradrenaline, ne_t, self._ewma_ne)
        d_ht = _step(nm.serotonin, ht_t, self._ewma_5ht)

        new = NeuromodState(
            dopamine=project("dopamine", nm.dopamine + d_da),
            serotonin=project("serotonin", nm.serotonin + d_ht),
            noradrenaline=project("noradrenaline", nm.noradrenaline + d_ne),
            acetylcholine=project("acetylcholine", nm.acetylcholine + d_ach),
            timestamp=nm.timestamp,
        )
        mag = abs(d_da) + abs(d_ach) + abs(d_ne) + abs(d_ht)
        return new, F, mag
