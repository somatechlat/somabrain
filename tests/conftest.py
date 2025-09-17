from __future__ import annotations

import pytest


@pytest.fixture(autouse=True, scope="function")
def ensure_runtime_backend_and_clear_mirror():
    """Ensure a consistent in-process memory backend is available and
    clear global mirrors.

    This avoids cross-test coupling (mirror carry-over) and race conditions
    where the pipeline persists to a backend not visible to the reader in
    the same test.
    """
    # Ensure a runtime memory backend exists for the duration of the test
    try:
        from somabrain import runtime as rt
        from somabrain.app import app
        from somabrain.config import load_config as _load
        from somabrain.memory_pool import MultiTenantMemory

        # Create a single MultiTenantMemory instance for the test session and
        # make sure both the app and runtime singletons reference the same
        # object. This avoids races where different parts of the pipeline use
        # different memory instances and persistence is not visible to readers.
        if rt.mt_memory is None and getattr(app, "mt_memory", None) is None:
            shared = MultiTenantMemory(_load())
            rt.mt_memory = shared
            app.mt_memory = shared
        else:
            # If one exists, prefer it and make both point to it
            preferred = rt.mt_memory or getattr(app, "mt_memory", None)
            rt.mt_memory = preferred
            app.mt_memory = preferred

        # Clear any existing client pool to ensure a clean slate for tests
        try:
            if rt.mt_memory and hasattr(rt.mt_memory, "_pool"):
                rt.mt_memory._pool.clear()
        except Exception:
            pass
    except Exception:
        pass

    # Clear process-global payload mirror before each test
    try:
        import somabrain.memory_client as mc

        if hasattr(mc, "_GLOBAL_PAYLOADS"):
            mc._GLOBAL_PAYLOADS.clear()  # type: ignore[attr-defined]
        # Also clear any stub in-memory mirrors that tests may rely on
        try:
            if hasattr(mc, "_STUB_STORE"):
                mc._STUB_STORE.clear()  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass
    yield
