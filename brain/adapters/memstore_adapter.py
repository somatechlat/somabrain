"""HTTP adapter for the external memory service.

This adapter provides a minimal HTTP client to communicate with the memory
service (dev) typically served at http://127.0.0.1:9595.

Assumptions (inferred):
- Search endpoint: POST /search with JSON {"embedding": [...], "top_k": N}
  returns {"results": [{"id": "...", "score": 0.9, "metadata": {...}, "embedding": [...]}, ...]}
- Upsert endpoint: POST /upsert with JSON {"items": [{"id":"...","embedding": [...], "metadata": {...}}, ...]}
  returns {"upserted": N}
- Get: GET /items/{id}
- Delete: DELETE /items/{id}
- Health: GET /health

These are reasonable defaults for a dev memstore. If your memory service uses a different API,
adjust the endpoint paths in the adapter or provide an adapter shim in production.

The adapter intentionally keeps dependencies light (uses `requests`) and is safe to fake in tests.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests

from observability.otel import span


class MemstoreError(RuntimeError):
    pass


class MemstoreAdapter:
    def __init__(self, base_url: str = "http://127.0.0.1:9595", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    # Health check
    def health(self) -> Dict:
        url = f"{self.base_url}/health"
        with span("memstore.health"):
            resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            raise MemstoreError(f"health failed: {resp.status_code} {resp.text}")
        return resp.json()

    # Search by embedding
    def search(self, embedding: List[float], top_k: int = 10) -> List[Dict]:
        url = f"{self.base_url}/search"
        payload = {"embedding": embedding, "top_k": int(top_k)}
        with span("memstore.search", top_k=int(top_k)):
            resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise MemstoreError(f"search failed: {resp.status_code} {resp.text}")
        data = resp.json()
        return data.get("results", [])

    # Upsert items (batch)
    def upsert(self, items: List[Dict]) -> Dict:
        """Each item should be {"id":str, "embedding": [...], "metadata": {...}}
        Returns the memstore response JSON.
        """
        url = f"{self.base_url}/upsert"
        with span("memstore.upsert", items=len(items)):
            resp = requests.post(url, json={"items": items}, timeout=self.timeout)
        if resp.status_code != 200:
            raise MemstoreError(f"upsert failed: {resp.status_code} {resp.text}")
        return resp.json()

    # Get single item
    def get(self, item_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/items/{item_id}"
        with span("memstore.get", id=item_id):
            resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise MemstoreError(f"get failed: {resp.status_code} {resp.text}")
        return resp.json()

    # Delete
    def delete(self, item_id: str) -> bool:
        url = f"{self.base_url}/items/{item_id}"
        with span("memstore.delete", id=item_id):
            resp = requests.delete(url, timeout=self.timeout)
        if resp.status_code == 404:
            return False
        if resp.status_code != 200:
            raise MemstoreError(f"delete failed: {resp.status_code} {resp.text}")
        return True


# Small smoke run
if __name__ == "__main__":
    m = MemstoreAdapter()
    try:
        print("health:", m.health())
    except Exception as e:
        print("Memstore health check failed:", e)
