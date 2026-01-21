"""Learning utilities for SomaBrain.

Decomposition:
    - Config dataclasses: somabrain/learning/config.py
    - Tenant cache: somabrain/learning/tenant_cache.py
    - Annealing/entropy: somabrain/learning/annealing.py
    - Persistence: somabrain/learning/persistence.py
    - Adaptation engine: somabrain/learning/adaptation.py
"""

from .adaptation import AdaptationEngine
from .annealing import (
    apply_tau_annealing,
    apply_tau_decay,
    check_entropy_cap,
    exponential_decay,
    get_entropy_cap,
    linear_decay,
)
from .config import AdaptationConstraints, AdaptationGains, UtilityWeights
from .dataset import TrainingExample, build_examples, export_examples, tokenize_examples
from .persistence import get_redis, is_persistence_enabled, load_state, persist_state
from .tenant_cache import TenantOverridesCache, get_tenant_override

__all__ = [
    # Dataset
    "TrainingExample",
    "build_examples",
    "tokenize_examples",
    "export_examples",
    # Config
    "UtilityWeights",
    "AdaptationGains",
    "AdaptationConstraints",
    # Tenant cache
    "TenantOverridesCache",
    "get_tenant_override",
    # Annealing
    "apply_tau_annealing",
    "apply_tau_decay",
    "check_entropy_cap",
    "get_entropy_cap",
    "linear_decay",
    "exponential_decay",
    # Persistence
    "get_redis",
    "is_persistence_enabled",
    "persist_state",
    "load_state",
    # Adaptation
    "AdaptationEngine",
]
