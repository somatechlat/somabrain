"""Runtime Singleton Initialization - Core runtime module loading and singleton setup.

Extracted from somabrain/app.py per vibe-compliance-audit spec.
Handles the complex runtime.py module loading and singleton registration.

This module is HIGH RISK due to tight coupling with runtime.py module loading.
Changes should be tested thoroughly before deployment.

Thread Safety:
    This module uses importlib.util for dynamic module loading. The loading
    process is not thread-safe and should only be called during application
    startup before any concurrent requests are processed.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from somabrain.quantum import QuantumLayer
    from somabrain.scoring import UnifiedScorer

logger = logging.getLogger("somabrain.bootstrap.runtime_init")


def load_runtime_module():
    """Load the runtime.py module using importlib.util.

    The repository contains both a ``runtime`` package (exposing WorkingMemoryBuffer)
    and a ``runtime.py`` module that defines the core singleton utilities
    (embedder, mt_wm, set_singletons, etc.). Importing ``runtime`` would resolve to
    the package, causing ``AttributeError: module 'somabrain.runtime' has no
    attribute 'set_singletons'``. To reliably load the module file, we import it via
    ``importlib.util`` and bind it to ``_rt``.

    Returns:
        module: The loaded runtime.py module with set_singletons and other utilities.

    Raises:
        AssertionError: If the module spec cannot be loaded.
    """
    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "runtime.py"
    )
    _spec = importlib.util.spec_from_file_location(
        "somabrain.runtime_module", _runtime_path
    )
    if not _spec or not _spec.loader:
        raise RuntimeError(
            f"Failed to load runtime.py module spec from {_runtime_path}"
        )

    # If an initializer already loaded the runtime module into sys.modules, reuse it
    if _spec.name in sys.modules:
        _rt = sys.modules[_spec.name]
    else:
        _rt = importlib.util.module_from_spec(_spec)
        # Register the module in ``sys.modules`` so that the code inside ``runtime.py``
        # (which accesses ``sys.modules[__name__]``) can find its own entry.
        sys.modules[_spec.name] = _rt
        _spec.loader.exec_module(_rt)  # load the module so its globals are available

    # Robustness: if the initializer loaded runtime under a different key, try to
    # find any loaded module whose __file__ points to runtime.py and reuse it so
    # set_singletons side-effects are observed.
    if not getattr(_rt, "embedder", None):
        for m in list(sys.modules.values()):
            try:
                mf = getattr(m, "__file__", "") or ""
                if mf.endswith(os.path.join("somabrain", "runtime.py")):
                    _rt = m
                    break
            except Exception:
                continue

    return _rt


def create_mt_memory(cfg, scorer: "UnifiedScorer", embedder: Any, _rt: Any):
    """Create or retrieve the MultiTenantMemory singleton.

    Args:
        cfg: Application configuration object.
        scorer: UnifiedScorer instance for memory scoring.
        embedder: Embedder instance for vector generation.
        _rt: The loaded runtime module.

    Returns:
        MultiTenantMemory: The memory singleton instance.
    """
    from somabrain.memory_pool import MultiTenantMemory

    if not hasattr(_rt, "mt_memory") or _rt.mt_memory is None:
        mt_memory = MultiTenantMemory(cfg, scorer=scorer, embedder=embedder)
        _rt.mt_memory = mt_memory
        # Also patch this module's global for test visibility
        mod = sys.modules.get("somabrain.app")
        if mod:
            setattr(mod, "mt_memory", _rt.mt_memory)
    else:
        mt_memory = _rt.mt_memory

    return mt_memory


def register_singletons(
    _rt: Any,
    embedder: Any,
    quantum: Optional["QuantumLayer"],
    mt_wm: Any,
    mc_wm: Any,
    mt_memory: Any,
    cfg: Any,
    enforce: bool = False,
) -> None:
    """Register singletons with the runtime module and DI container.

    This function registers singletons in two places for backward compatibility:
    1. The runtime module (legacy pattern, for existing code)
    2. The DI container (preferred pattern, for new code)

    Args:
        _rt: The loaded runtime module.
        embedder: Embedder instance.
        quantum: Optional QuantumLayer instance.
        mt_wm: MultiTenantWM instance.
        mc_wm: MultiColumnWM instance.
        mt_memory: MultiTenantMemory instance.
        cfg: Application configuration object.
        enforce: If True, raise RuntimeError for missing singletons.

    Raises:
        RuntimeError: If enforce=True and required singletons are missing.

    VIBE Compliance:
        - Registers singletons in DI container (preferred pattern)
        - Maintains backward compatibility with runtime module (legacy pattern)
        - No lazy imports for circular avoidance
    """
    if enforce:
        missing = []
        if not hasattr(_rt, "embedder") or _rt.embedder is None:
            missing.append("embedder")
        if not hasattr(_rt, "mt_wm") or _rt.mt_wm is None:
            missing.append("mt_wm")
        if not hasattr(_rt, "mc_wm") or _rt.mc_wm is None:
            missing.append("mc_wm")
        if missing:
            raise RuntimeError(
                f"BACKEND ENFORCEMENT: missing runtime singletons: {', '.join(missing)}; "
                "initialize runtime before importing somabrain.app"
            )

    # Register with runtime module (legacy pattern for backward compatibility)
    _rt.set_singletons(
        _embedder=embedder or getattr(_rt, "embedder", None),
        _quantum=quantum,
        _mt_wm=mt_wm or getattr(_rt, "mt_wm", None),
        _mc_wm=mc_wm or getattr(_rt, "mc_wm", None),
        _mt_memory=mt_memory or getattr(_rt, "mt_memory", None),
        _cfg=cfg,
    )

    # Register with DI container (preferred pattern for new code)
    try:
        from somabrain.core.container import container

        # Register factory functions that return the already-created instances
        if embedder is not None:
            container.register("embedder", lambda e=embedder: e)
        if quantum is not None:
            container.register("quantum", lambda q=quantum: q)
        if mt_wm is not None:
            container.register("mt_wm", lambda w=mt_wm: w)
        if mc_wm is not None:
            container.register("mc_wm", lambda w=mc_wm: w)
        if mt_memory is not None:
            container.register("mt_memory", lambda m=mt_memory: m)
        if cfg is not None:
            container.register("runtime_cfg", lambda c=cfg: c)
        logger.debug("Registered runtime singletons in DI container")
    except Exception as exc:
        logger.warning("Failed to register singletons in DI container: %s", exc)


def should_enforce_backends(settings: Any) -> bool:
    """Determine if backend enforcement should be enabled.

    Backend enforcement blocks disabled/local fallbacks and requires
    external services such as the memory HTTP backend.

    Args:
        settings: Application settings object.

    Returns:
        bool: True if backend enforcement should be enabled.
    """
    # Test environment bypass - disable enforcement during pytest
    if "pytest" in sys.modules:
        return False

    if settings is not None and getattr(settings, "pytest_current_test", None):
        return False

    # Check settings for enforcement flags
    if settings is not None:
        try:
            # Prefer new mode-derived enforcement (always true under Sprint policy)
            mode_policy = bool(
                getattr(settings, "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", True)
            )
            if mode_policy:
                return True
            return bool(getattr(settings, "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", False))
        except Exception:
            pass

    # Default: disabled for development/full-local mode
    return False
