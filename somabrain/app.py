"""SomaBrain Cognitive Application
=================================

This module exposes the production FastAPI surface for SomaBrain. It wires
production transports, memory clients, neuromodulators, and control systems together
so that the runtime interacts with live infrastructure instead of mocks.

Main responsibilities:
- bootstrap global singletons (memory pools, working memory, scorers, etc.)
- expose REST endpoints for recalling, remembering, planning, and health
- register background maintenance jobs and safety middleware
- publish observability signals and readiness diagnostics

Usage:
    uvicorn somabrain.app:app --host 0.0.0.0 --port 9696
"""

from __future__ import annotations


# Threading and time for sleep logic


# Use the unified Settings instance for configuration.

# Cognitive Threads router (Phase 5)

# Oak health dependencies – Milvus client for persistence health checks.

# Oak feature imports

# Oak FastAPI router that now talks to Milvus


# Import the async tenant resolver (aliased as get_tenant_async) for use in endpoints.


# ---------------------------------------------------------------------------
# Simple OPA engine wrapper – provides a minimal health check for the OPA
# service configured via ``SOMABRAIN_OPA_URL`` (or ``settings.opa_url``).
# The wrapper is attached to ``app.state`` during startup so the health endpoint
# can report ``opa_ok`` and ``opa_required`` correctly.
# ---------------------------------------------------------------------------
class SimpleOPAEngine:
    """Lightweight wrapper around the OPA HTTP endpoint.

    The production code does not import a dedicated OPA client library. This
    class stores the base URL and offers an async ``health`` method used by the
    health endpoint to verify that the OPA service is reachable.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        """Return ``True`` if the OPA ``/health`` endpoint responds with 200.

        Any exception (network error, timeout, etc.) is treated as unhealthy.
        """
        try:
            import httpx  # type: ignore

            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


# Define OPA engine attachment function (will be registered after FastAPI app creation).
async def _attach_opa_engine() -> None:  # pragma: no cover
    """Initialize the OPA engine and store it in ``app.state``.

    This function is deliberately defined *before* the FastAPI ``app`` instance
    is created to avoid the ``NameError`` that occurs when using the
    ``@app.on_event`` decorator before ``app`` exists. The function will be
    registered as a startup event handler after the ``FastAPI`` instance is
    instantiated.
    """
    # ``settings`` may expose the URL via ``opa_url`` or the environment variable.
    opa_url = getattr(settings, "opa_url", None) or getattr(
        settings, "SOMABRAIN_OPA_URL", None
    )
    if opa_url:
        app.state.opa_engine = SimpleOPAEngine(opa_url)
    else:
        app.state.opa_engine = None


# Use the new TenantManager for tenant resolution.


try:  # Constitution engine is optional in minimal deployments.
    from somabrain.constitution import ConstitutionEngine
except Exception:  # pragma: no cover - optional dependency
    ConstitutionEngine = None  # type: ignore[assignment]
