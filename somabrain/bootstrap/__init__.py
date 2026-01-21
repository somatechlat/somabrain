"""Bootstrap components for SomaBrain application initialization.

This package contains modules for application startup and initialization:
- logging: Cognitive logging setup
- opa: OPA engine initialization
- singletons: Core singleton factory functions
- runtime_init: Runtime module loading and singleton registration
- core_singletons: Application-level singleton creation
"""

from somabrain.bootstrap.core_singletons import (
    create_amygdala,
    create_drift_monitor,
    create_ewma_monitors,
    create_exec_controller,
    create_hippocampus,
    create_mc_wm,
    create_mt_ctx,
    create_mt_wm,
    create_quotas,
    create_rate_limiter,
    create_sdr_encoder,
    create_supervisor,
    create_unified_brain,
)
from somabrain.bootstrap.logging import get_loggers, setup_logging
from somabrain.bootstrap.opa import SimpleOPAEngine, create_opa_engine, get_opa_url
from somabrain.bootstrap.runtime_init import (
    create_mt_memory,
    load_runtime_module,
    register_singletons,
    should_enforce_backends,
)
from somabrain.bootstrap.singletons import (
    make_embedder_with_dim,
    make_fd_sketch,
    make_predictor,
    make_quantum_layer,
    make_unified_scorer,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_loggers",
    # OPA
    "SimpleOPAEngine",
    "create_opa_engine",
    "get_opa_url",
    # Singletons factory
    "make_predictor",
    "make_quantum_layer",
    "make_embedder_with_dim",
    "make_fd_sketch",
    "make_unified_scorer",
    # Runtime init
    "load_runtime_module",
    "create_mt_memory",
    "register_singletons",
    "should_enforce_backends",
    # Core singletons
    "create_mt_wm",
    "create_mc_wm",
    "create_mt_ctx",
    "create_quotas",
    "create_rate_limiter",
    "create_amygdala",
    "create_hippocampus",
    "create_supervisor",
    "create_exec_controller",
    "create_drift_monitor",
    "create_sdr_encoder",
    "create_ewma_monitors",
    "create_unified_brain",
]
