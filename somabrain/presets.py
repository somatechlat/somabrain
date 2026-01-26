"""Presets for SomaBrain configuration optimization.

This module defines high-level "modes" or "presets" that map to specific
ranges of cognitive parameters. This allows for meta-control of the brain's
plasticity and stability without manually tuning hundreds of knobs.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class CognitivePreset:
    """A collection of parameter targets for a specific cognitive mode."""
    name: str
    description: str
    params: Dict[str, Any]

# -----------------------------------------------------------------------------
# Tier 3: Cognitive Dynamics Presets
# -----------------------------------------------------------------------------

STABLE = CognitivePreset(
    name="stable",
    description="Reliable, factual recall. High precision, low plasticity.",
    params={
        "learning_rate": 0.01,
        "retrieval_tau": 0.7,      # Lower temperature = more deterministic
        "retrieval_alpha": 1.0,    # High weight on cosine similarity
        "neuro_dopamine_base": 0.4,
        "neuro_serotonin_base": 0.8, # High stability
        "enable_dynamic_lr": False,
    }
)

PLASTIC = CognitivePreset(
    name="plastic",
    description="Rapid learning, fast adaptation. High plasticity.",
    params={
        "learning_rate": 0.1,
        "retrieval_tau": 1.0,      # Moderate temperature
        "neuro_dopamine_base": 0.7, # High motivation/reward seeking
        "neuro_serotonin_base": 0.4,
        "enable_dynamic_lr": True,
    }
)

LATERAL = CognitivePreset(
    name="lateral",
    description="Creative association, brainstorming. High entropy.",
    params={
        "learning_rate": 0.05,
        "retrieval_tau": 2.0,      # High temperature = more exploration
        "retrieval_alpha": 0.5,    # Less weight on strict similarity
        "neuro_acetylcholine_base": 0.08, # High attentional focus spread
        "enable_dynamic_lr": True,
    }
)

PRESETS = {
    "stable": STABLE,
    "plastic": PLASTIC,
    "lateral": LATERAL,
}

def get_preset(name: str) -> CognitivePreset:
    """Retrieve a preset by name (defaulting to STABLE)."""
    return PRESETS.get(name.lower(), STABLE)
