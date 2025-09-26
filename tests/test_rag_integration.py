"""Integration test: RAG retrieval flow using in-process memstore test server."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.support.memstore_test_app import start_test_server

from somabrain.api.rag import router
from somabrain.api.dependencies.auth import set_auth_config
from somabrain.config import Config


def test_rag_flow_end_to_end():
    mem_port, _ = start_test_server()
    mem_base = f"http://127.0.0.1:{mem_port}"

    set_auth_config(Config())

    os.environ["SOMABRAIN_MEMSTORE_URL"] = mem_base

    app = FastAPI()
    from somabrain.api.dependencies.utility_guard import utility_guard
    from somabrain.api.dependencies.auth import auth_guard

    app.dependency_overrides[utility_guard] = lambda: None
    app.dependency_overrides[auth_guard] = lambda: None
    app.include_router(router)

    client = TestClient(app)

    import requests

    _ = requests.post(
        f"{mem_base}/upsert",
        json={
            "items": [
                {
                    "id": "m1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"text": "This is memory one."},
                }
            ]
        },
        timeout=5,
    )

    headers = {"X-Model-Confidence": "10", "X-Session-ID": "sess-1"}
    resp = client.post(
        "/rag", json={"text": "Tell me about memory one.", "top_k": 3}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query"] == "Tell me about memory one."
    assert "Context:" in body["prompt"]
    assert isinstance(body["memories"], list)
    assert isinstance(body["weights"], list)
    assert isinstance(body["working_memory"], list)
    assert body["working_memory"][0]["query"] == "Tell me about memory one."
    ids = [m["id"] for m in body["memories"]]
    assert "m1" in ids
    assert body["latency_seconds"] >= 0
