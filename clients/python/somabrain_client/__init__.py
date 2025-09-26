from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class SomaBrainClient:
    def __init__(self, base_url: str, api_token: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_token:
            self.session.headers["Authorization"] = f"Bearer {api_token}"
        self._load_ports()

    def _load_ports(self) -> None:
        ports_path = Path("ports.json")
        if ports_path.exists():
            try:
                ports = json.loads(ports_path.read_text())
                context_port = ports.get("SOMABRAIN_HOST_PORT")
                if context_port:
                    self.base_url = f"http://localhost:{context_port}/context"
            except Exception:
                pass

    def evaluate(self, session_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
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
