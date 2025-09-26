"""
Minimal Python client for SomaBrain API.

Usage:
    from clients.python.somabrain_client import SomaBrainClient
    api = SomaBrainClient(base_url="http://127.0.0.1:9696", tenant="public")
    api.remember({"task":"hello","importance":1,"memory_type":"episodic"})
    print(api.recall("hello", top_k=3))
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class SomaBrainClient:
    def __init__(
        self, base_url: str, token: Optional[str] = None, tenant: Optional[str] = None
    ):
        self.base = base_url.rstrip("/")
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        if tenant:
            self.headers["X-Tenant-ID"] = str(tenant)
        self._http = httpx.Client(
            base_url=self.base, headers=self.headers, timeout=10.0
        )

    def remember(
        self, payload: Dict[str, Any], coord: Optional[str] = None
    ) -> Dict[str, Any]:
        body = {"coord": coord, "payload": payload}
        r = self._http.post("/remember", json=body)
        r.raise_for_status()
        return r.json()

    def recall(
        self, query: str, top_k: int = 3, universe: Optional[str] = None
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"query": query, "top_k": int(top_k)}
        if universe:
            body["universe"] = universe
        r = self._http.post("/recall", json=body)
        r.raise_for_status()
        return r.json()

    def link(
        self,
        *,
        from_key: Optional[str] = None,
        to_key: Optional[str] = None,
        from_coord: Optional[str] = None,
        to_coord: Optional[str] = None,
        type: Optional[str] = None,
        weight: float = 1.0,
        universe: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "from_key": from_key,
            "to_key": to_key,
            "from_coord": from_coord,
            "to_coord": to_coord,
            "type": type,
            "weight": weight,
            "universe": universe,
        }
        r = self._http.post("/link", json=body)
        r.raise_for_status()
        return r.json()

    def plan_suggest(
        self,
        task_key: str,
        *,
        max_steps: Optional[int] = None,
        rel_types: Optional[List[str]] = None,
        universe: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"task_key": task_key}
        if max_steps is not None:
            body["max_steps"] = int(max_steps)
        if rel_types is not None:
            body["rel_types"] = rel_types
        if universe:
            body["universe"] = universe
        r = self._http.post("/plan/suggest", json=body)
        r.raise_for_status()
        return r.json()
