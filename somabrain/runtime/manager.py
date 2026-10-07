"""SomaBrain Runtime Module.

Encapsulates memory, embedder, and working-memory singletons in a thread-safe
RuntimeManager. Module-level names are retained as lazy proxies for backward
compatibility, but the actual state lives inside the RuntimeManager instance.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class _SettingsAdapter:
    """Bridge Django settings to the lowercase config shape used by runtime code."""

    _ALIASES = {
        "default_tenant": "SOMABRAIN_DEFAULT_TENANT",
        "embed_dim": "SOMABRAIN_EMBED_DIM",
        "embed_provider": "SOMABRAIN_EMBED_PROVIDER",
        "embed_model": "SOMABRAIN_EMBED_MODEL",
        "embed_cache_size": "SOMABRAIN_EMBED_CACHE_SIZE",
        "embed_dim_target_k": "SOMABRAIN_EMBED_DIM_TARGET_K",
        "use_hrr": "SOMABRAIN_USE_HRR",
        "hrr_dim": "SOMABRAIN_HRR_DIM",
        "hrr_seed": "SOMABRAIN_HRR_SEED",
        "fde_enabled": "SOMABRAIN_FDE_ENABLED",
    }

    def __init__(self, settings_obj: Any):
        self._settings = settings_obj
        self.http = settings_obj

    def __getattr__(self, name: str) -> Any:
        candidates = [
            name,
            self._ALIASES.get(name),
            f"SOMABRAIN_{name.upper()}",
            name.upper(),
        ]
        for candidate in candidates:
            if candidate and hasattr(self._settings, candidate):
                return getattr(self._settings, candidate)
        raise AttributeError(name)


class RuntimeManager:
    """Thread-safe container for runtime singletons.

    All heavy initialization is deferred until first access and guarded by a
    lock so concurrent callers cannot create duplicate singletons.
    """

    def __init__(self):
        self._embedder: Any | None = None
        self._mt_wm: Any | None = None
        self._mt_memory: Any | None = None
        self._cfg: Any | None = None
        self._lock = threading.Lock()
        self._initialized = False
        self._last_status: dict = {
            "embedder": False,
            "working_memory": False,
            "memory_pool": False,
        }

    def initialize_runtime(self) -> dict:
        """Initialize all runtime singletons.

        Returns:
            Dict with initialization status for each component.
        """
        with self._lock:
            if self._initialized:
                return self._last_status

            self._cfg = settings
            self._last_status = {
                "embedder": self._initialize_embedder() is not None,
                "working_memory": self._initialize_working_memory() is not None,
                "memory_pool": self._initialize_memory_pool() is not None,
            }
            self._attach_wm_promoter()
            self._initialized = True
            logger.info("Runtime initialized: %s", self._last_status)
            return self._last_status

    def _attach_wm_promoter(self) -> None:
        """Wire WM→LTM promotion once WM and the LTM pool both exist.

        Without this, ``WorkingMemory.set_promoter`` is never called and
        salient items never reach long-term memory (A2.1).
        """
        if self._mt_wm is None or self._mt_memory is None:
            return
        if not hasattr(self._mt_wm, "set_promoter_factory"):
            return

        def promoter_factory(tenant_id: str):
            """Build the per-tenant WM→LTM promoter.

            This factory is called from ``MultiTenantWM.get_or_create``, which
            runs on the async request path. Building the promoter reads
            ``BrainSetting`` (Django ORM), so doing it inline raises
            ``SynchronousOnlyOperation`` -- which the old ``except`` swallowed
            as "WM promoter unavailable" and the promoter was never attached.
            Nothing could ever reach long-term memory.

            The ORM work is handed to a worker thread so it is legal whatever
            context the caller is in. ``get_wm_ltm_promoter`` caches per tenant,
            so the thread hop is paid once per tenant, not per write.
            """
            from concurrent.futures import ThreadPoolExecutor

            def build():
                from somabrain.memory.promotion import get_wm_ltm_promoter
                from somabrain.services.memory_service import MemoryService

                ns = f"somabrain:{tenant_id}"
                memsvc = MemoryService(self._mt_memory, ns)
                client = memsvc.client()
                return get_wm_ltm_promoter(client, tenant_id=tenant_id)

            try:
                from django.conf import settings as _dj

                # Wait bound is the EXISTING consolidation timeout -- WM->LTM
                # promotion IS consolidation. AP-01 forbids inventing a name
                # when the knob already exists.
                # max_workers is deliberately omitted: the interpreter default
                # applies, and the hop size is not a tunable.
                wait_s = float(_dj.SOMABRAIN_CONSOLIDATION_TIMEOUT_S)
                with ThreadPoolExecutor(thread_name_prefix="wm-promoter") as ex:
                    return ex.submit(build).result(timeout=wait_s)
            except Exception as exc:
                logger.warning(
                    "WM promoter unavailable for tenant %s: %s", tenant_id, exc
                )
                return None

        self._mt_wm.set_promoter_factory(promoter_factory)
        logger.info("WM→LTM promoter factory attached")

    def _initialize_embedder(self) -> Any:
        if self._embedder is not None:
            return self._embedder

        try:
            from somabrain.admin.core.embeddings import make_embedder

            self._embedder = make_embedder(_SettingsAdapter(settings))
            logger.info("Embedder initialized successfully")
            return self._embedder
        except Exception as e:
            # VIBE: Fail loudly - do not silently return fake embeddings
            logger.error("CRITICAL: Failed to initialize Embedder: %s", e)
            logger.error("Embedder is REQUIRED for SomaBrain operation.")
            logger.error("Please check your ML backend configuration.")
            raise RuntimeError(
                f"Embedder initialization failed: {e}. "
                "SomaBrain requires a working embedder. Check SOMABRAIN_EMBEDDER_PROVIDER setting."
            ) from e

    def _initialize_working_memory(self) -> Any:
        if self._mt_wm is not None:
            return self._mt_wm

        try:
            from somabrain.memory.wm.mt_wm import MultiTenantWM

            # Use configured embedding dimension from settings
            self._mt_wm = MultiTenantWM(dim=settings.SOMABRAIN_EMBED_DIM)
            logger.info("Working memory initialized successfully")
            return self._mt_wm
        except Exception as e:
            logger.warning("Failed to initialize WorkingMemory: %s", e)
            return None

    def _initialize_memory_pool(self) -> Any:
        if self._mt_memory is not None:
            return self._mt_memory

        try:
            from somabrain.memory.pool import MultiTenantMemory

            embedder = self._initialize_embedder()
            scorer = None
            try:
                from somabrain.bootstrap.singletons import make_unified_scorer

                scorer = make_unified_scorer(settings)
            except Exception as se:
                logger.warning("UnifiedScorer init failed: %s", se)

            self._mt_memory = MultiTenantMemory(
                cfg=settings, scorer=scorer, embedder=embedder
            )
            logger.info("Memory pool initialized successfully")
            return self._mt_memory
        except Exception as e:
            logger.warning("Failed to initialize memory pool: %s", e)
            return None

    @property
    def embedder(self) -> Any | None:
        """Get or initialize the embedder singleton."""
        if self._embedder is None:
            self.initialize_runtime()
        return self._embedder

    @property
    def mt_wm(self) -> Any | None:
        """Get or initialize the working memory singleton."""
        if self._mt_wm is None:
            self.initialize_runtime()
        return self._mt_wm

    @property
    def mt_memory(self) -> Any | None:
        """Get or initialize the memory pool singleton."""
        if self._mt_memory is None:
            self.initialize_runtime()
        return self._mt_memory

    @property
    def cfg(self) -> Any | None:
        """Get the runtime configuration object."""
        if self._cfg is None:
            self.initialize_runtime()
        return self._cfg


# Singleton instance backing the module-level helpers and legacy attributes.
_runtime_manager = RuntimeManager()


def __getattr__(name: str) -> Any:
    """Backward-compatible lazy access to legacy module-level singletons."""
    if name in ("embedder", "mt_wm", "mt_memory", "cfg"):
        return getattr(_runtime_manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def initialize_runtime() -> dict:
    """Initialize all runtime singletons."""
    return _runtime_manager.initialize_runtime()


def get_embedder() -> Any:
    """Get or initialize the embedder singleton."""
    return _runtime_manager.embedder


def get_working_memory() -> Any:
    """Get or initialize the working memory singleton."""
    return _runtime_manager.mt_wm


def get_memory_pool() -> Any:
    """Get or initialize the memory pool singleton."""
    return _runtime_manager.mt_memory


class Runtime:
    """Facade for runtime singletons."""

    @staticmethod
    def initialize() -> dict:
        """Initialize all runtime singletons."""
        return _runtime_manager.initialize_runtime()

    @staticmethod
    def get_embedder() -> Any:
        """Get the embedder singleton."""
        return _runtime_manager.embedder

    @staticmethod
    def get_working_memory() -> Any:
        """Get the working memory singleton."""
        return _runtime_manager.mt_wm

    @staticmethod
    def get_memory_pool() -> Any:
        """Get the memory pool singleton."""
        return _runtime_manager.mt_memory
