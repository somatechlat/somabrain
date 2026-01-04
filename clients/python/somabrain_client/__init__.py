"""Module __init__."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional
import requests


class SomaBrainClient:
    """Thin HTTP client for the SomaBrain REST API.

    The client is deliberately lightweight – it only wraps ``requests`` and
    provides a handful of convenience methods used by the test suite and the
    example scripts.  All configuration is driven by the ``base_url`` argument
    and an optional ``api_token`` for bearer‑token authentication.
    """

    def __init__(self, base_url: str, api_token: Optional[str] = None) -> None:
        """Create a new :class:`SomaBrainClient`.

        Parameters
        ----------
        base_url:
            The base URL of the SomaBrain service (e.g. ``"http://localhost:9696"``).
            Trailing slashes are stripped to avoid double ``//`` when constructing
            endpoint URLs.
        api_token:
            Optional JWT token used for ``Authorization: Bearer`` authentication.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_token:
            self.session.headers["Authorization"] = f"Bearer {api_token}"
        self._load_ports()

    def _load_ports(self) -> None:
        """Override ``base_url`` if a ``ports.json`` file is present.

        Some local development setups expose a ``ports.json`` artifact that maps
        service names to dynamically assigned host ports.  When the file exists
        and contains a ``SOMABRAIN_HOST_PORT`` entry, the client rewrites its
        ``base_url`` to point at ``http://localhost:<port>/context``.
        Errors while reading or parsing the file are logged rather than silently
        ignored, which aids debugging in CI environments.
        """
        ports_path = Path("ports.json")
        if not ports_path.exists():
            return
        try:
            ports = json.loads(ports_path.read_text())
            context_port = ports.get("SOMABRAIN_HOST_PORT")
            if context_port:
                self.base_url = f"http://localhost:{context_port}/context"
        except Exception as exc:  # pragma: no cover
            # Import the logger lazily to avoid circular imports at module load.
            from common.logging import logger

            logger.exception("Failed to load ports from ports.json: %s", exc)

    def evaluate(self, session_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
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
        reward: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
