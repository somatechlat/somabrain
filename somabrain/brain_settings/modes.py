"""Brain Modes Registry - GMD MathCore v4.0 Presets.

Defines high-level operational modes that override low-level knobs.
Reference: GMD Theorem 5 (Sensitivity & Robustness).
"""
from typing import Any, Dict

# GMD Parameter Presets for each Mode
# Personas: GMD Analyst, UX Consultant, SRE
BRAIN_MODES: Dict[str, Dict[str, Any]] = {
    "TRAINING": {
        "description": "High-Velocity Learning (Max Plasticity)",
        "overrides": {
            "gmd_eta": 0.10,          # PLASTICITY: Max robust learning speed
            "salience_w_novelty": 1.0, # ELASTICITY: Complete focus on new patterns
            "neuro_acetyl_base": 0.5, # NEURO: High cholinergic drive
            "adapt_lr": 0.5,          # PLASTICITY: High adaptation rate
        }
    },
    "RECALL": {
        "description": "Deterministic Reproduction (Zero-Drift)",
        "overrides": {
            "gmd_eta": 0.01,          # PLASTICITY: Freeze weights
            "tau": 0.1,               # ELASTICITY: Sharp distribution (argmax)
            "determinism": True,      # ELASTICITY: No stochastic sampling
            "adapt_lr": 0.0,          # PLASTICITY: No learning drift
        }
    },
    "ANALYTIC": {
        "description": "Standard Multi-Shot Reasoning",
        "overrides": {
            "gmd_eta": 0.05,          # PLASTICITY: Balanced acquisition
            "tau": 0.7,               # ELASTICITY: Standard creative breadth
            "graph_hops": 2,          # ELASTICITY: Localized associations
        }
    },
    "SEARCH": {
        "description": "Creative/Associative Exploration",
        "overrides": {
            "gmd_eta": 0.03,          # PLASTICITY: Stabilize existing patterns
            "tau": 1.4,               # ELASTICITY: High temperature/stochasticity
            "graph_hops": 5,          # ELASTICITY: Deep associative walks
            "salience_w_novelty": 0.9, # ELASTICITY: Prefer obscure patterns
        }
    },
    "SLEEP": {
        "description": "ROAMDP Consolidation Cycle",
        "overrides": {
            "enable_sleep": True,      # RESOURCE: Entry trigger
            "sleep_state": "LIGHT",   # RESOURCE: Initial entry
            "gmd_eta": 0.0,           # PLASTICITY: Cognitive freeze
        }
    }
}

def get_mode_overrides(mode_name: str) -> Dict[str, Any]:
    """Get the parameter overrides for a given mode."""
    mode = BRAIN_MODES.get(mode_name, BRAIN_MODES["ANALYTIC"])
    return mode.get("overrides", {})
