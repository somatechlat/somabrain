"""Bootstrap components for SomaBrain application initialization.

This package contains modules for application startup and initialization:
- logging: Cognitive logging setup
- opa: OPA engine initialization
- singletons: Core singleton factory functions
"""

from somabrain.bootstrap.logging import setup_logging, get_loggers
from somabrain.bootstrap.opa import SimpleOPAEngine, create_opa_engine, get_opa_url
from somabrain.bootstrap.singletons import (
    make_predictor,
    make_quantum_layer,
    make_embedder_with_dim,
    make_fd_sketch,
    make_unified_scorer,
)

__all__ = [
    "setup_logging",
    "get_loggers",
    "SimpleOPAEngine",
    "create_opa_engine",
    "get_opa_url",
    "make_predictor",
    "make_quantum_layer",
    "make_embedder_with_dim",
    "make_fd_sketch",
    "make_unified_scorer",
]
