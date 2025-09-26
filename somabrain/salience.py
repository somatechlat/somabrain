"""
Salience Computation Module for SomaBrain

This module provides salience scoring functionality for determining the importance
and attention-worthiness of information. It combines novelty and prediction error
signals to compute salience scores for cognitive processing.

Key Features:
- Weighted combination of novelty and error signals
- Configurable salience weights
- Bounded output range [0,1] for interpretability
- Simple and efficient computation
- Integration with neuromodulatory systems

Salience Formula:
    salience = (w_novelty × novelty) + (w_error × prediction_error)
    salience = clamp(salience, 0, 1)

Applications:
- Memory storage decisions
- Attention allocation
- Cognitive resource prioritization
- Learning signal modulation

Classes:
    SalienceWeights: Configuration for salience computation weights

Functions:
    compute_salience: Main salience computation function
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SalienceWeights:
    novelty: float = 0.6
    error: float = 0.4


def compute_salience(novelty: float, error: float, w: SalienceWeights) -> float:
    s = (w.novelty * float(novelty)) + (w.error * float(error))
    # bound to [0,1] for interpretability
    return max(0.0, min(1.0, s))
