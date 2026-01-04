"""Integrator Hub service.

This module provides a thin wrapper around the existing ``integrator_hub_triplet``
implementation. It exposes a public ``IntegratorHub`` class that can be imported
by other components without needing to know the internal triplet details. The
wrapper simply re‑exports the class, preserving the VIBE principle of a single
source of truth and avoiding code duplication.

All configuration (Kafka bootstrap, topics, temperature, etc.) continues to be
read from the global ``settings`` object. Errors are raised immediately if any
required configuration is missing, matching the fail‑fast behavior required by
VIBE.
"""

from __future__ import annotations

# Re‑export the full implementation from the triplet module.
# The triplet file already contains the complete logic, metrics, health server
# and OPA integration. By importing it here we keep a single implementation.
from .services.integrator_hub_triplet import IntegratorHub  # noqa: F401

__all__ = ["IntegratorHub"]