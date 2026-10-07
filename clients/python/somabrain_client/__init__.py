"""Thin SomaBrain REST client.

The caller-supplied ``base_url`` is authoritative. There is no local
``ports.json`` rewrite and no silent endpoint hijack.
"""

from __future__ import annotations

from typing import Any

import requests


class SomaBrainClient:
    """Thin HTTP client for the SomaBrain REST API.

    The client is deliberately lightweight – it only wraps ``requests`` and
    provides a handful of convenience methods used by the test suite and the
    example scripts.  All configuration is driven by the ``base_url`` argument
    and an optional ``api_token`` for bearer‑token authentication.
    """

    def __init__(self, base_url: str, api_token: str | None = None) -> None:
        """Create a new :class:`SomaBrainClient`.

        Parameters
        ----------
        base_url:
            The base URL of the SomaBrain service (e.g. ``"http://localhost:30101"``).
            Trailing slashes are stripped to avoid double ``//`` when constructing
            endpoint URLs.
        api_token:
            Optional JWT token used for ``Authorization: Bearer`` authentication.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_token:
            self.session.headers["Authorization"] = f"Bearer {api_token}"

    def evaluate(self, session_id: str, query: str, top_k: int = 5) -> dict[str, Any]:
        """Send an evaluation request to the SomaBrain service.

        Parameters
        ----------
        session_id:
            Identifier for the user/session.
        query:
            The natural‑language query to be evaluated.
        top_k:
            Number of top results to return (default 5).
        """
        payload = {"session_id": session_id, "query": query, "top_k": top_k}
        resp = self.session.post(f"{self.base_url}/evaluate", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def feedback(
        self,
        session_id: str,
        query: str,
        prompt: str,
        response_text: str,
        utility: float,
        reward: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit feedback about a previous prediction.

        Parameters
        ----------
        session_id:
            Identifier for the user/session.
        query:
            Original query string.
        prompt:
            Prompt that was sent to the model.
        response_text:
            Model's textual response.
        utility:
            Numeric utility score supplied by the caller.
        reward:
            Optional reward signal (e.g., from reinforcement learning).
        metadata:
            Optional additional key/value data.
        """
        payload = {
            "session_id": session_id,
            "query": query,
            "prompt": prompt,
            "response_text": response_text,
            "utility": utility,
            "reward": reward,
            "metadata": metadata,
        }
        resp = self.session.post(f"{self.base_url}/feedback", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
