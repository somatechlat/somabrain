"""Sleep system for SomaBrain.

This module provides sleep state management and consolidation cycles.
"""

from enum import Enum
from typing import Dict, Any
import dataclasses
from common.config.settings import settings as settings


class SleepState(Enum):
    """Sleep state enumeration."""

    ACTIVE = "active"
    LIGHT = "light"
    DEEP = "deep"
    FREEZE = "freeze"


@dataclasses.dataclass
class SleepParameters:
    """Sleep parameters configuration."""

    K: int = settings.sleep_k0
    t: float = settings.sleep_t0
    tau: float = settings.sleep_tau0
    eta: float = settings.sleep_eta0
    lambda_: float = settings.sleep_lambda0
    B: float = settings.sleep_B0
    # Bounds for validation
    K_min: int = settings.sleep_K_min
    t_min: float = settings.sleep_t_min
    alpha_K: float = settings.sleep_alpha_K
    alpha_t: float = settings.sleep_alpha_t
    alpha_tau: float = settings.sleep_alpha_tau
    alpha_eta: float = settings.sleep_alpha_eta
    beta_B: float = settings.sleep_beta_B


class SleepStateManager:
    """Manages sleep state transitions and parameters."""

    def __init__(self):
        self.parameters = SleepParameters()

    def compute_parameters(self, state: SleepState) -> Dict[str, float]:
        """Compute parameters for a given sleep state (hot-configurable)."""
        p = self.parameters  # already sourced from settings
        state_scalar = {
            SleepState.ACTIVE: 0.0,
            SleepState.LIGHT: 0.5,
            SleepState.DEEP: 1.0,
            SleepState.FREEZE: 10.0,  # treat freeze as effectively infinite
        }[state]

        s = state_scalar
        K = max(p.K_min, int((1 - p.alpha_K * s) * p.K))
        t = max(p.t_min, (1 - p.alpha_t * s) * p.t)
        tau = max(1e-6, (1 - p.alpha_tau * s) * p.tau)
        if s >= 1:
            eta = 0.0
        else:
            eta = max(0.0, (1 - p.alpha_eta * s) * p.eta)
        B = p.B + p.beta_B * s
        if state == SleepState.FREEZE:
            lambda_ = 0.0
        elif state == SleepState.DEEP:
            lambda_ = max(0.0, p.lambda_ * 0.5)
        elif state == SleepState.LIGHT:
            lambda_ = max(0.0, p.lambda_ * 0.8)
        else:
            lambda_ = p.lambda_

        return {
            "K": K,
            "t": t,
            "tau": tau,
            "eta": eta,
            "lambda": lambda_,
            "B": B,
        }

    def can_transition(self, from_state: SleepState, to_state: SleepState) -> bool:
        """Check if state transition is valid."""
        # The allowed state transition graph is:
        #   ACTIVE → LIGHT → DEEP → FREEZE → LIGHT (and then back to ACTIVE is NOT allowed)
        # Only the forward edges are permitted.  The previous implementation also
        # allowed ``LIGHT → ACTIVE`` which contradicts the specification and the
        # test suite expectations.  We therefore restrict the mapping to the
        # minimal set of forward transitions.
        valid_transitions = {
            SleepState.ACTIVE: [SleepState.LIGHT],
            SleepState.LIGHT: [SleepState.DEEP],
            SleepState.DEEP: [SleepState.FREEZE],
            SleepState.FREEZE: [SleepState.LIGHT],
        }

        return to_state in valid_transitions.get(from_state, [])
