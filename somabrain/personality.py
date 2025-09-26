"""
Personality Module for Trait-Based Neuromodulation.

This module implements a personality system that modulates neuromodulator states
based on learned personality traits. It provides persistent storage of personality
traits per tenant and applies trait-based adjustments to the neuromodulator system.

Key Features:
- Tenant-specific personality trait storage
- Neuromodulator modulation based on personality traits
- Support for traits like curiosity, risk tolerance, reward seeking, and calm
- Integration with the neuromodulator system for cognitive control

Personality traits influence various aspects of cognitive processing:
- Curiosity: Affects acetylcholine levels, influencing focus and attention
- Risk tolerance: Modulates noradrenaline, affecting decision thresholds
- Reward seeking: Influences dopamine levels, affecting learning from rewards
- Calm: Modulates serotonin, affecting emotional stability

Classes:
    PersonalityStateInMem: In-memory representation of personality traits.
    PersonalityStore: Manages personality trait storage and neuromodulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .neuromodulators import NeuromodState


@dataclass
class PersonalityStateInMem:
    """
    In-memory representation of personality traits for a tenant.

    Stores personality trait values as a dictionary of trait names to values.
    Traits are typically floating-point values between 0.0 and 1.0.

    Attributes:
        traits (Dict[str, Any]): Dictionary mapping trait names to their values.
            Common traits include 'curiosity', 'risk_tolerance', 'reward_seeking', 'calm'.
    """

    traits: Dict[str, Any]


class PersonalityStore:
    """
    Manages personality trait storage and neuromodulator modulation.

    Provides tenant-specific storage of personality traits and applies personality-based
    modulation to neuromodulator states. This allows the system to adapt its cognitive
    processing style based on learned personality characteristics.

    Attributes:
        _by_tenant (Dict[str, PersonalityStateInMem]): Internal storage mapping
            tenant IDs to their personality states.
    """

    def __init__(self):
        """Initialize an empty personality store."""
        self._by_tenant: Dict[str, PersonalityStateInMem] = {}

    def get(self, tenant_id: str) -> Dict[str, Any]:
        """
        Retrieve personality traits for a tenant.

        Returns a copy of the personality traits for the specified tenant.
        If the tenant has no stored traits, returns an empty dictionary.

        Args:
            tenant_id (str): Unique identifier for the tenant.

        Returns:
            Dict[str, Any]: Dictionary of personality trait names to values.
        """
        return dict(
            self._by_tenant.get(tenant_id, PersonalityStateInMem(traits={})).traits
        )

    def set(self, tenant_id: str, traits: Dict[str, Any]) -> None:
        """
        Store personality traits for a tenant.

        Updates or creates the personality state for the specified tenant with
        the provided trait values.

        Args:
            tenant_id (str): Unique identifier for the tenant.
            traits (Dict[str, Any]): Dictionary of trait names to values to store.
        """
        self._by_tenant[tenant_id] = PersonalityStateInMem(traits=dict(traits))

    @staticmethod
    def modulate_neuromods(
        base: NeuromodState, traits: Dict[str, Any]
    ) -> NeuromodState:
        """
        Apply personality-based modulation to neuromodulator state.

        Modulates the base neuromodulator state based on personality traits to create
        a personalized neuromodulator profile. Each trait influences different
        neuromodulators in biologically plausible ways.

        Args:
            base (NeuromodState): Base neuromodulator state to modulate.
            traits (Dict[str, Any]): Personality traits to apply for modulation.

        Returns:
            NeuromodState: New neuromodulator state with personality-based adjustments.

        Modulation Rules:
            - Curiosity: Boosts acetylcholine (0.02 + 0.08 * curiosity) for enhanced focus
            - Risk tolerance: Reduces noradrenaline (0.05 - 0.05 * risk) for lower thresholds
            - Reward seeking: Increases dopamine (0.4 + 0.3 * reward_seeking) for reward learning
            - Calm: Increases serotonin (base + 0.2 * calm) for emotional stability

        Note:
            All neuromodulator values are clamped to biologically reasonable ranges.
        """
        # Copy base
        s = NeuromodState(
            dopamine=base.dopamine,
            serotonin=base.serotonin,
            noradrenaline=base.noradrenaline,
            acetylcholine=base.acetylcholine,
            timestamp=base.timestamp,
        )
        # Curiosity boosts focus (ACh)
        cur = float(traits.get("curiosity", 0.0) or 0.0)
        s.acetylcholine = max(0.0, min(0.1, 0.02 + 0.08 * cur))
        # Risk tolerance lowers NE (reduces thresholds)
        risk = float(traits.get("risk_tolerance", 0.0) or 0.0)
        s.noradrenaline = max(0.0, min(0.1, 0.05 - 0.05 * risk))
        # Reward seeking boosts dopamine (error weight)
        rew = float(traits.get("reward_seeking", 0.0) or 0.0)
        s.dopamine = max(0.2, min(0.8, 0.4 + 0.3 * rew))
        # Calm (stability) slightly increases serotonin (not directly used yet)
        calm = float(traits.get("calm", 0.0) or 0.0)
        s.serotonin = max(0.0, min(1.0, base.serotonin + 0.2 * calm))
        return s
