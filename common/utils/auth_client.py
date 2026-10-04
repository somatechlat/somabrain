"""HTTP client for the shared Auth service."""

from __future__ import annotations

from typing import Any

import httpx


class AuthClient:
    """Best-effort client for the central JWT validation service.

    The concrete API surface may evolve; this client keeps SomaBrain aligned with
    the shared-infra architecture by providing a single integration point.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 5.0,
        api_key: str | None = None,
    ) -> None:
        """Initialize the instance.

        ``base_url`` is deployment topology. When omitted it is resolved from
        ``SOMABRAIN_AUTH_URL``; a missing setting raises. There is no cluster
        DNS name or localhost fallback at the call site (Rule 91).
        """
        from somabrain.settings.resolve import require_url

        resolved = require_url("SOMABRAIN_AUTH_URL") if base_url is None else str(base_url).strip()
        if "://" not in resolved:
            raise ValueError(
                "AuthClient base_url must be a URL with a scheme; protocol "
                "constants live in somabrain.settings.constants and the "
                "effective base is the SOMABRAIN_AUTH_URL setting."
            )

        headers = {"User-Agent": "somabrain-auth-client"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(base_url=resolved, timeout=timeout, headers=headers)

    def validate(self, token: str) -> dict[str, Any]:
        """Execute validate.

        Args:
            token: The token.
        """

        resp = self._client.post("/validate", json={"token": token})
        resp.raise_for_status()
        return resp.json()

    def issue_service_token(
        self, subject: str, scopes: list[str] | None = None
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
