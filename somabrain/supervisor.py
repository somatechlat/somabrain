"""
Supervisor Module for SomaBrain.

This module implements the supervisory system responsible for free energy minimization and
neuromodulator state adjustment. The supervisor monitors prediction errors and novelty signals
to modulate neuromodulator levels, implementing active inference principles for cognitive control.

Key Features:
- Free energy calculation based on prediction error and novelty
- Proportional neuromodulator adjustments within bounds
- Active inference-inspired cognitive control
- Configurable gain and limit parameters

Classes:
    SupervisorConfig: Configuration parameters for supervisor behavior.
    Supervisor: Main supervisor class for free energy minimization and neuromodulation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .neuromodulators import NeuromodState


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

    The Supervisor implements active inference principles by monitoring prediction errors
    and novelty signals to adjust neuromodulator states. It calculates free energy as
    a weighted sum of prediction error and novelty, then modulates dopamine, acetylcholine,
    and noradrenaline levels proportionally.

    This creates a control loop where high prediction errors or novelty trigger
    neuromodulator changes to improve future predictions and adaptation.

    Attributes:
        cfg (SupervisorConfig): Configuration parameters for supervisor behavior.

    Example:
        >>> config = SupervisorConfig()
        >>> supervisor = Supervisor(config)
        >>> neuromod = NeuromodState()
        >>> new_nm, free_energy, magnitude = supervisor.adjust(neuromod, 0.3, 0.1)
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
        from somabrain.stats import EWMA

        self._ewma_da = EWMA(alpha=0.1)  # dopamine delta smoothing
        self._ewma_ach = EWMA(alpha=0.1)  # acetylcholine delta smoothing
        self._ewma_ne = EWMA(alpha=0.1)  # noradrenaline delta smoothing

    def free_energy(self, novelty: float, pred_error: float) -> float:
        """
        Calculate free energy from novelty and prediction error signals.

        Free energy is computed as a weighted sum of prediction error and novelty,
        serving as a proxy for the system's uncertainty and need for adaptation.
        This implements a simplified version of the free energy principle.

        Args:
            novelty (float): Novelty signal (0.0 to 1.0), higher values indicate more novel input.
            pred_error (float): Prediction error (0.0 to 1.0), higher values indicate worse predictions.

        Returns:
            float: Free energy value as weighted sum of inputs.

        Note:
            Values are clamped to [0.0, 1.0] range before calculation.
            Can be extended to include KL divergence terms in future implementations.
        """
        # simple proxy: weighted sum (can extend to KL terms later)
        n = float(max(0.0, min(1.0, novelty)))
        e = float(max(0.0, min(1.0, pred_error)))
        return float(self.cfg.alpha_err * e + self.cfg.beta_nov * n)

    def adjust(
        self, nm: NeuromodState, novelty: float, pred_error: float
    ) -> tuple[NeuromodState, float, float]:
        """
        Adjust neuromodulator states based on novelty and prediction error.

        Calculates free energy and applies proportional adjustments to neuromodulator
        levels within configured bounds. Returns the new neuromodulator state along
        with free energy and total modulation magnitude.

        Args:
            nm (NeuromodState): Current neuromodulator state.
            novelty (float): Current novelty signal (0.0 to 1.0).
            pred_error (float): Current prediction error (0.0 to 1.0).

        Returns:
            tuple[NeuromodState, float, float]: A tuple containing:
                - New neuromodulator state after adjustments
                - Free energy value
                - Total modulation magnitude (sum of absolute changes)

        Note:
            Adjustments are bounded by cfg.limit and neuromodulator-specific ranges.
            Dopamine responds to prediction error, acetylcholine to novelty,
            noradrenaline to combined signals. Serotonin is held constant.
        """
        F = self.free_energy(novelty, pred_error)
        g = float(self.cfg.gain)
        lim = float(self.cfg.limit)
        # proportional adjustments within bounds
        raw_d_da = max(-lim, min(lim, g * pred_error))
        raw_d_ach = max(-lim, min(lim, g * novelty))
        raw_d_ne = max(-lim, min(lim, g * (pred_error + novelty) * 0.5))

        # Apply EWMA smoothing to deltas
        # EWMA.update returns a dict; extract the smoothed mean value
        d_da = max(-lim, min(lim, self._ewma_da.update(raw_d_da)["mean"]))
        d_ach = max(-lim, min(lim, self._ewma_ach.update(raw_d_ach)["mean"]))
        d_ne = max(-lim, min(lim, self._ewma_ne.update(raw_d_ne)["mean"]))
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