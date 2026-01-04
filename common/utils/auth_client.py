"""HTTP client for the shared Auth service."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class AuthClient:
    """Best-effort client for the central JWT validation service.

    The concrete API surface may evolve; this client keeps SomaBrain aligned with
    the shared-infra architecture by providing a single integration point.
    """

    def __init__(
        self,
        base_url: str = "http://auth.soma-infra.svc.cluster.local:8080",
        timeout: float = 5.0,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the instance."""

        headers = {"User-Agent": "somabrain-auth-client"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def validate(self, token: str) -> Dict[str, Any]:
        """Execute validate.

            Args:
                token: The token.
            """

        resp = self._client.post("/validate", json={"token": token})
        resp.raise_for_status()
        return resp.json()

    def issue_service_token(
        self, subject: str, scopes: Optional[list[str]] = None
    ) -> str:
        """Execute issue service token.

            Args:
                subject: The subject.
                scopes: The scopes.
            """

        resp = self._client.post(
            "/token", json={"subject": subject, "scopes": scopes or []}
        )
        resp.raise_for_status()
        payload = resp.json()
        token = payload.get("token")
        if not token:
            raise RuntimeError("Auth service did not return a token")
        return str(token)


__all__ = ["AuthClient"]