"""Prefrontal working-memory admission gate.

Real mechanism (see SOMA-BR-MATH-TRUTH-001 T81): precision-weighted
working-memory admission. Content is admitted to WM only when its
precision-weighted salience reaches the admit threshold. Precision is
inverse prediction-error uncertainty.

Math:
    π     = 1 / (1 + pred_error)          # precision ∈ (0, 1]
    score = π · salience                  # precision-weighted evidence
    admit = score ≥ admit_threshold

This module is **not** a free-energy minimiser and does not implement
goal maintenance, cognitive switching, or inhibition. Free energy lives
in ``somabrain.runtime.supervisor.Supervisor`` only. Executive claims
beyond WM admission are not made.

Wired into ``POST /cognitive/act`` via ``eval_step``: the step's
``wm_admit`` flag gates ``FocusState.update`` so low-precision content
does not enter the session working-memory focus.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PrefrontalConfig:
    """Configuration for the prefrontal WM admission gate.

    Attributes
    ----------
    admit_threshold : float
        Minimum precision-weighted salience required to admit content.
    precision_floor : float
        Lower bound on the precision denominator guard (numerical safety).
    extra : dict
        Additional configuration parameters (ignored by the gate).
    """

    admit_threshold: float = 0.25
    precision_floor: float = 1e-6
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the configuration as a plain dictionary."""
        base = {
            "admit_threshold": self.admit_threshold,
            "precision_floor": self.precision_floor,
        }
        base.update(self.extra)
        return base


class PrefrontalCortex:
    """Precision-weighted working-memory admission gate.

    Attributes
    ----------
    config : PrefrontalConfig
        Gate configuration (threshold, numerical floor).
    state : dict
        Internal counters for observability (``calls``, ``admits``, ``last``).
    """

    def __init__(self, config: PrefrontalConfig | None = None) -> None:
        """Initialize the instance."""
        self.config = config or PrefrontalConfig()
        self.state: dict[str, Any] = {}

    @staticmethod
    def precision(pred_error: float, floor: float = 1e-6) -> float:
        """Precision π = 1 / (1 + pred_error), clamped to (floor, 1].

        ``pred_error`` is clamped to [0, ∞) so π stays in (0, 1]; a negative
        error is treated as 0 (perfect prediction).
        """
        err = float(pred_error)
        if not math.isfinite(err) or err < 0.0:
            err = 0.0
        denom = 1.0 + err
        if denom <= floor:
            denom = floor
        pi = 1.0 / denom
        return max(floor, min(1.0, pi))

    def admit_score(self, salience: float, pred_error: float) -> float:
        """Precision-weighted admission score = π · salience."""
        s = float(salience)
        if not math.isfinite(s):
            s = 0.0
        s = max(0.0, min(1.0, s))
        pi = self.precision(pred_error, floor=self.config.precision_floor)
        return pi * s

    def gate_wm(self, salience: float, pred_error: float) -> bool:
        """Return True when content should be admitted to working memory.

        ``admit = (π · salience ≥ admit_threshold)`` with π = 1/(1+pred_error).
        High prediction error (low precision) suppresses admission even when
        salience is high; high salience with confident prediction admits.
        """
        self.state["calls"] = int(self.state.get("calls", 0)) + 1
        score = self.admit_score(salience, pred_error)
        self.state["last_score"] = score
        admit = score >= float(self.config.admit_threshold)
        self.state["admits"] = int(self.state.get("admits", 0)) + (1 if admit else 0)
        self.state["last"] = {
            "salience": float(salience),
            "pred_error": float(pred_error),
            "score": score,
            "admit": admit,
        }
        return admit

    def __repr__(self) -> str:
        """Return object representation."""
        return f"PrefrontalCortex(config={self.config!r})"
