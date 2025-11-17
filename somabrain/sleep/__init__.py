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
        base_params = {
            'K': self.parameters.K,
            't': self.parameters.t,
            'tau': self.parameters.tau,
            'eta': self.parameters.eta,
            'lambda': self.parameters.lambda_,
            'B': self.parameters.B
        }
        
        if state == SleepState.ACTIVE:
            base_params['eta'] = 0.1
        elif state == SleepState.LIGHT:
            base_params['eta'] = 0.05
        elif state == SleepState.DEEP:
            base_params['eta'] = 0.0
        elif state == SleepState.FREEZE:
            base_params['eta'] = 0.0
            
        return base_params
    
    def can_transition(self, from_state: SleepState, to_state: SleepState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            SleepState.ACTIVE: [SleepState.LIGHT],
            SleepState.LIGHT: [SleepState.ACTIVE, SleepState.DEEP],
            SleepState.DEEP: [SleepState.FREEZE],
            SleepState.FREEZE: [SleepState.LIGHT]
        }
        
        return to_state in valid_transitions.get(from_state, [])