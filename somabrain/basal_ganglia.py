from __future__ import annotations
from dataclasses import dataclass

"""
Basal Ganglia Policy Module for SomaBrain

This module implements basal ganglia-like policy decision making for the SomaBrain system.
The basal ganglia is a key brain structure involved in action selection, motor control,
and habit formation. In SomaBrain, it serves as the final decision-making component
that translates salience signals into concrete actions.

Key Features:
    pass
- Policy decision making based on store/act gates
- Action selection and motor control simulation
- Integration with salience and neuromodulator systems
- Support for both automatic and controlled processing

The basal ganglia works in concert with the amygdala (salience detection) and
prefrontal cortex (executive control) to determine what actions to take.

Classes:
    PolicyDecision: Container for policy decisions
    BasalGangliaPolicy: Main policy decision maker
"""




@dataclass
class PolicyDecision:
    """
    Represents a policy decision for store and act actions.

    Attributes
    ----------
    store : bool
        Whether to store the memory.
    act : bool
        Whether to act on the memory.
    """

    store: bool
    act: bool


class BasalGangliaPolicy:
    """
    Basal ganglia-like policy decision maker.

    Makes decisions based on store and act gates.
    """

def decide(self, store_gate: bool, act_gate: bool) -> PolicyDecision:
        """
        Decide on store and act based on gates.

        Parameters
        ----------
        store_gate : bool
            Store gate signal.
        act_gate : bool
            Act gate signal.

        Returns
        -------
        PolicyDecision
            Decision with store and act flags.
        """
        return PolicyDecision(store=bool(store_gate), act=bool(act_gate))
