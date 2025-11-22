"""Simple in‑process mock memory HTTP service used for end‑to‑end demos.

It implements two minimal endpoints:
* POST /remember – stores the JSON payload keyed by ``key`` (or ``content`` if ``key`` not provided).
* GET  /memory/get/{key} – retrieves the stored payload.

The service runs with ``uvicorn`` on port 9999 and is included in the
docker‑compose stack as the ``mock_memory`` service.
"""

from fastapi import FastAPI, Request
from typing import Any, Dict

app = FastAPI()
_store: Dict[str, Any] = {}


@app.post("/remember")
async def remember(request: Request):
    data = await request.json()
    # Use an explicit ``key`` field if present, otherwise fall back to ``content``
    key = data.get("key") or data.get("content") or "default"
    _store[key] = data
    return {"status": "saved", "key": key}


@app.get("/memory/get/{key}")
async def get(key: str):
    return _store.get(key, {})
