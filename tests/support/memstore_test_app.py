import socket
import threading
import time
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Simple in-memory store
_STORE: Dict[str, Dict[str, Any]] = {}


class UpsertItem(BaseModel):
    id: str
    embedding: List[float]
    metadata: Dict[str, Any] = {}


class UpsertRequest(BaseModel):
    items: List[UpsertItem]


class SearchRequest(BaseModel):
    embedding: List[float]
    top_k: int = 10


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upsert")
async def upsert(req: UpsertRequest):
    for it in req.items:
        _STORE[it.id] = {
            "id": it.id,
            "embedding": it.embedding,
            "metadata": it.metadata,
        }
    return {"upserted": len(req.items)}


@app.post("/search")
async def search(req: SearchRequest):
    # naive similarity: dot product fallback
    emb = req.embedding
    results = []
    for v in _STORE.values():
        # compute simple score: negative euclidean distance
        d = sum((a - b) ** 2 for a, b in zip(emb, v.get("embedding", [0] * len(emb))))
        score = -d
        results.append(
            {
                "id": v["id"],
                "score": score,
                "metadata": v.get("metadata", {}),
                "embedding": v.get("embedding"),
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results[: req.top_k]}


@app.get("/items/{item_id}")
async def get_item(item_id: str):
    if item_id not in _STORE:
        raise HTTPException(status_code=404, detail="not found")
    return _STORE[item_id]


@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    if item_id not in _STORE:
        raise HTTPException(status_code=404, detail="not found")
    del _STORE[item_id]
    return {"deleted": True}


def _find_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr, port = s.getsockname()
    s.close()
    return port


def run_in_thread(port: int):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # give uvicorn a moment to start
    time.sleep(0.2)
    return thread


def start_test_server() -> (int, threading.Thread):
    port = _find_free_port()
    thread = run_in_thread(port)
    return port, thread
