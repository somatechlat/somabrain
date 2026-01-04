"""OPA (Open Policy Agent) engine initialization for SomaBrain.

This module provides a lightweight wrapper around the OPA HTTP endpoint
for policy-based authorization and health checks.
"""

from __future__ import annotations

from django.conf import settings


class SimpleOPAEngine:
    """Lightweight wrapper around the OPA HTTP endpoint.

    The production code does not import a dedicated OPA client library. This
    class stores the base URL and offers an async ``health`` method used by the
    health endpoint to verify that the OPA service is reachable.
    """

    def __init__(self, base_url: str):
        """Initialize the instance."""

        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        """Return ``True`` if the OPA ``/health`` endpoint responds with 200.

        Any exception (network error, timeout, etc.) is treated as unhealthy.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


def get_opa_url() -> str | None:
    """Get the OPA URL from settings.

    Returns:
        The OPA URL if configured, None otherwise.
    """
    return getattr(settings, "SOMABRAIN_OPA_URL", None) or getattr(
        settings, "SOMABRAIN_OPA_URL", None
    )


def create_opa_engine() -> SimpleOPAEngine | None:
    """Create an OPA engine instance if configured.

    Returns:
        SimpleOPAEngine instance if OPA URL is configured, None otherwise.
    """
    opa_url = get_opa_url()
    if opa_url:
        return SimpleOPAEngine(opa_url)
    return None