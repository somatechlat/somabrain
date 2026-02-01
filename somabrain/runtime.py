"""SomaBrain Runtime Module.

VIBE COMPLIANT: Initializes memory, embedder, and working memory singletons.

This module provides the runtime singletons required by the memory API:
- embedder: Text-to-vector embedding service
- mt_wm: Multi-tenant working memory
- mt_memory: Multi-tenant memory pool

These are lazily initialized on first access to avoid startup overhead.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Runtime singletons - initialized lazily
embedder: Optional[Any] = None
mt_wm: Optional[Any] = None
mt_memory: Optional[Any] = None
cfg: Optional[Any] = None


def _initialize_embedder() -> Any:
    """Initialize the embedder singleton.

    VIBE COMPLIANT: Fails loudly if embedder cannot be initialized.
    Per Vibe Coding Rules: NO STUBS, NO FAKE RETURNS, NO HARDCODED VALUES.
    """
    global embedder
    if embedder is not None:
        return embedder

    try:
        from somabrain.apps.core.embeddings import make_embedder

        embedder = make_embedder(settings)
        logger.info("Embedder initialized successfully")
        return embedder
    except Exception as e:
        # VIBE: Fail loudly - do not silently return fake embeddings
        logger.error(f"CRITICAL: Failed to initialize Embedder: {e}")
        logger.error("Embedder is REQUIRED for SomaBrain operation.")
        logger.error("Please check your ML backend configuration.")

        # VIBE: Raise error to ensure system fails loudly (no silent fallbacks)
        raise RuntimeError(
            f"Embedder initialization failed: {e}. "
            "SomaBrain requires a working embedder. Check SOMABRAIN_EMBEDDER_PROVIDER setting."
        ) from e


def _initialize_working_memory() -> Any:
    """Initialize the multi-tenant working memory singleton."""
    global mt_wm
    if mt_wm is not None:
        return mt_wm

    try:
        from somabrain.mt_wm import MultiTenantWM

        # Use configured embedding dimension from settings
        mt_wm = MultiTenantWM(dim=settings.SOMABRAIN_EMBED_DIM)
        logger.info("Working memory initialized successfully")
        return mt_wm
    except Exception as e:
        logger.warning(f"Failed to initialize WorkingMemory: {e}")
        return None


def _initialize_memory_pool() -> Any:
    """Initialize the multi-tenant memory pool singleton."""
    global mt_memory
    if mt_memory is not None:
        return mt_memory

    try:
        from somabrain.memory_pool import MultiTenantMemory

        mt_memory = MultiTenantMemory(cfg=settings)
        logger.info("Memory pool initialized successfully")
        return mt_memory
    except Exception as e:
        logger.warning(f"Failed to initialize memory pool: {e}")
        return None


def initialize_runtime() -> dict:
    """Initialize all runtime singletons.

    Returns:
        Dict with initialization status for each component.
    """
    global cfg
    cfg = settings

    status = {
        "embedder": _initialize_embedder() is not None,
        "working_memory": _initialize_working_memory() is not None,
        "memory_pool": _initialize_memory_pool() is not None,
    }

    logger.info(f"Runtime initialized: {status}")
    return status


def get_embedder() -> Any:
    """Get or initialize the embedder singleton."""
    global embedder
    if embedder is None:
        _initialize_embedder()
    return embedder


def get_working_memory() -> Any:
    """Get or initialize the working memory singleton."""
    global mt_wm
    if mt_wm is None:
        _initialize_working_memory()
    return mt_wm


def get_memory_pool() -> Any:
    """Get or initialize the memory pool singleton."""
    global mt_memory
    if mt_memory is None:
        _initialize_memory_pool()
    return mt_memory
