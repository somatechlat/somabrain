"""Development Memory HTTP Service (for local testing only).

This small FastAPI app implements the minimal SomaMemory HTTP surface used by
Somabrain integration tests:

- GET /health -> 200 JSON with ok and simple subsystem flags
- POST /remember -> accepts a JSON body {tenant, namespace, key, value}
- POST /recall -> accepts {tenant, namespace, query, top_k} and returns matches

It stores data in-process using a per-(tenant,namespace) dictionary keyed by
string keys and performs a trivial recall by case-insensitive substring match on
"task"/"fact"/"text" fields of the stored payloads. This service is only for
developer workflows; do not use in production.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Somamemory Dev", version="0.1.0")


class RememberBody(BaseModel):
    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    key: str = Field(..., min_length=1)
    value: Dict[str, Any]


class RecallBody(BaseModel):
    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=50)


_STORE: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "kv_store": True,
        "vector_store": True,
        "graph_store": False,
        "ts": time.time(),
    }


@app.post("/remember")
async def remember(body: RememberBody) -> Dict[str, Any]:
    key = (body.tenant.strip(), body.namespace.strip())
    bucket = _STORE.setdefault(key, {})
    # Shallow copy to avoid mutation by caller
    payload = dict(body.value or {})
    # Attach simple timestamp if missing
    payload.setdefault("timestamp", time.time())
    bucket[body.key] = payload
    return {"ok": True, "coordinate": None}


def _payload_text(p: Dict[str, Any]) -> str:
    for k in ("task", "fact", "text"):
        v = p.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    # Fallback: join stringy fields
    parts = [str(v) for v in p.values() if isinstance(v, (str, int, float))]
    return " ".join(parts).lower()


@app.post("/recall")
async def recall(body: RecallBody) -> Dict[str, Any]:
    key = (body.tenant.strip(), body.namespace.strip())
    bucket = _STORE.get(key, {})
    q = body.query.strip().lower()
    if not q:
        raise HTTPException(status_code=400, detail="empty query")
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for payload in bucket.values():
        t = _payload_text(payload)
        # Simple contains scoring
        if not t:
            continue
        if q in t or t in q:
            scored.append((1.0, dict(payload)))
    # Sort by timestamp desc then score desc
    scored.sort(key=lambda sp: (float(sp[1].get("timestamp", 0.0)), sp[0]), reverse=True)
    top = [p for _, p in scored[: max(1, int(body.top_k))]]
    return {"ok": True, "results": top, "items": top}


def main() -> None:  # pragma: no cover
    import uvicorn  # type: ignore

    uvicorn.run(app, host="0.0.0.0", port=9595)


if __name__ == "__main__":  # pragma: no cover
    main()
