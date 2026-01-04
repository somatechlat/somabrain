"""Integrator hub compatibility module.

Provides the real ``IntegratorHub`` implementation (re‑exported from
``integrator_hub_triplet``) together with lightweight ``SoftmaxIntegrator`` and
``DomainObs`` classes required by the test suite.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

# Re‑export the main hub implementation
from .integrator_hub_triplet import IntegratorHub  # noqa: F401

__all__ = ["IntegratorHub", "SoftmaxIntegrator", "DomainObs"]


@dataclass
class DomainObs:
    """Observation for a single domain.

    Attributes
    ----------
    ts: float
        Timestamp of the observation (seconds since epoch).
    confidence: float
        Confidence value in the range ``[0, 1]``.
    delta_error: float
        Error metric used by the full integrator – retained for API
        compatibility.
    """

    ts: float
    confidence: float
    delta_error: float


class SoftmaxIntegrator:
    """Minimal softmax‑based integrator used in tests.

    Stores the most recent observation per ``tenant`` and ``domain``. ``snapshot``
    returns the leader (domain with highest softmax weight), a ``weights``
    mapping and the raw observations.
    """

    def __init__(self, tau: float = 1.0, stale_seconds: float = 5.0):
        """Initialize the instance."""

        self.tau = max(tau, 1e-9)  # avoid division by zero
        self.stale_seconds = stale_seconds
        self._data: Dict[str, Dict[str, DomainObs]] = {}

    def update(self, tenant: str, domain: str, obs: DomainObs) -> None:
        """Record an observation for *tenant*/*domain*.

        Observations are overwritten if a newer timestamp is provided.
        """
        self._data.setdefault(tenant, {})[domain] = obs

    def _evict_stale(self, tenant: str, now: float) -> None:
        """Remove observations older than ``stale_seconds`` for *tenant*."""
        recent: Dict[str, DomainObs] = {}
        for dom, obs in self._data.get(tenant, {}).items():
            if now - obs.ts <= self.stale_seconds:
                recent[dom] = obs
        self._data[tenant] = recent

    def snapshot(
        self, tenant: str
    ) -> Tuple[str, Dict[str, float], Dict[str, DomainObs]]:
        """Return ``(leader, weights, raw)`` for *tenant*.

        *leader* – domain with highest softmax weight (or ``"state"`` if no data).
        *weights* – mapping domain → softmax probability.
        *raw* – the underlying ``DomainObs`` objects.
        """
        now = time.time()
        self._evict_stale(tenant, now)
        raw = self._data.get(tenant, {})
        if not raw:
            return "state", {"state": 1.0}, {}

        # Use confidence as score, apply temperature tau
        scores = {d: max(obs.confidence, 1e-12) for d, obs in raw.items()}
        max_score = max(scores.values())
        exp_vals = {d: (s - max_score) / self.tau for d, s in scores.items()}
        exp_vals = {d: pow(2.718281828459045, v) for d, v in exp_vals.items()}
        total = sum(exp_vals.values()) or 1.0
        weights = {d: v / total for d, v in exp_vals.items()}
        leader = max(weights, key=weights.get)
        return leader, weights, raw