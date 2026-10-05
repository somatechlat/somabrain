"""Learning utilities for SomaBrain.

Decomposition:
    - Config dataclasses: somabrain/learning/config.py
    - Tenant cache: somabrain/learning/tenant_cache.py
    - Annealing/entropy: somabrain/learning/annealing.py
    - Persistence: somabrain/learning/persistence.py
    - Adaptation engine: somabrain/learning/adaptation.py

Exports are resolved lazily (PEP 562) so pure helpers — annealing schedules,
``weight_delta``/``clamp``, config dataclasses — import without a booted Django
settings module.  Heavy symbols (``AdaptationEngine``, persistence) are loaded
only when actually requested.
"""

from __future__ import annotations

from typing import Any

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
    # Numeric helpers
    "clamp",
    "weight_delta",
    # Persistence
    "get_redis",
    "is_persistence_enabled",
    "persist_state",
    "load_state",
    # Adaptation
    "AdaptationEngine",
]

_LAZY: dict[str, tuple[str, str]] = {
    "TrainingExample": (".dataset", "TrainingExample"),
    "build_examples": (".dataset", "build_examples"),
    "tokenize_examples": (".dataset", "tokenize_examples"),
    "export_examples": (".dataset", "export_examples"),
    "UtilityWeights": (".config", "UtilityWeights"),
    "AdaptationGains": (".config", "AdaptationGains"),
    "AdaptationConstraints": (".config", "AdaptationConstraints"),
    "TenantOverridesCache": (".tenant_cache", "TenantOverridesCache"),
    "get_tenant_override": (".tenant_cache", "get_tenant_override"),
    "apply_tau_annealing": (".annealing", "apply_tau_annealing"),
    "apply_tau_decay": (".annealing", "apply_tau_decay"),
    "check_entropy_cap": (".annealing", "check_entropy_cap"),
    "get_entropy_cap": (".annealing", "get_entropy_cap"),
    "linear_decay": (".annealing", "linear_decay"),
    "exponential_decay": (".annealing", "exponential_decay"),
    "clamp": (".adaptation.utils", "clamp"),
    "weight_delta": (".adaptation.utils", "weight_delta"),
    "get_redis": (".persistence", "get_redis"),
    "is_persistence_enabled": (".persistence", "is_persistence_enabled"),
    "persist_state": (".persistence", "persist_state"),
    "load_state": (".persistence", "load_state"),
    "AdaptationEngine": (".adaptation", "AdaptationEngine"),
}


def __getattr__(name: str) -> Any:
    """Load a learning export on first access."""
    try:
        module_name, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module

    module = import_module(module_name, __name__)
    value = getattr(module, attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
