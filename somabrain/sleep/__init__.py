"""Sleep system for SomaBrain.

This module provides sleep state management and consolidation cycles.
"""

from enum import Enum
from typing import Dict, Any
import dataclasses


class SleepState(Enum):
    """Sleep state enumeration."""
    ACTIVE = "active"
    LIGHT = "light"
    DEEP = "deep"
    FREEZE = "freeze"


@dataclasses.dataclass
class SleepParameters:
    """Sleep parameters configuration."""
    K: int = 100
    t: float = 10.0
    tau: float = 1.0
    eta: float = 0.1
    lambda_: float = 0.01
    B: float = 0.5
    
    # Bounds for validation
    K_min: int = 1
    t_min: float = 0.1


class SleepStateManager:
    """Manages sleep state transitions and parameters."""
    
    def __init__(self):
        self.parameters = SleepParameters()
    
    def compute_parameters(self, state: SleepState) -> Dict[str, float]:
        """Compute parameters for a given sleep state."""
        # Base parameters are taken from the configured ``SleepParameters``.
        # The specification expects the parameters to be adjusted per
        # state, not merely the ``eta`` value. We implement a simple, deterministic
        # scaling that respects the documented bounds (``K_min`` and ``t_min``).
        base_params = {
            'K': self.parameters.K,
            't': self.parameters.t,
            'tau': self.parameters.tau,
            'eta': self.parameters.eta,
            'lambda': self.parameters.lambda_,
            'B': self.parameters.B,
        }

        # Apply state‑specific scaling. The numbers are chosen to be monotonic
        # and bounded; they can be tuned later without breaking the API.
        if state == SleepState.ACTIVE:
            # No scaling – stay at baseline values.
            base_params['eta'] = 0.1
        elif state == SleepState.LIGHT:
            base_params['K'] = max(self.parameters.K_min, int(base_params['K'] * 0.8))
            base_params['t'] = max(self.parameters.t_min, base_params['t'] * 1.2)
            base_params['eta'] = 0.05
        elif state == SleepState.DEEP:
            base_params['K'] = max(self.parameters.K_min, int(base_params['K'] * 0.5))
            base_params['t'] = max(self.parameters.t_min, base_params['t'] * 2.0)
            base_params['eta'] = 0.0
        elif state == SleepState.FREEZE:
            base_params['K'] = max(self.parameters.K_min, int(base_params['K'] * 0.1))
            base_params['t'] = max(self.parameters.t_min, base_params['t'] * 5.0)
            base_params['eta'] = 0.0

        # Ensure the parameters respect the minimum constraints.
        if base_params['K'] < self.parameters.K_min:
            base_params['K'] = self.parameters.K_min
        if base_params['t'] < self.parameters.t_min:
            base_params['t'] = self.parameters.t_min

        return base_params
    
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