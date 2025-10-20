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

