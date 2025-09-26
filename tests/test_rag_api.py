from __future__ import annotations

from fastapi.testclient import TestClient

from somabrain.app import app


def test_rag_api_endpoint_smoke():
    client = TestClient(app)
    r = client.post("/rag/retrieve", json={"query": "test", "top_k": 3})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "candidates" in data
    assert isinstance(data["candidates"], list)
    assert len(data["candidates"]) == 3
    # fields present
    c0 = data["candidates"][0]
    assert "score" in c0 and "retriever" in c0 and "payload" in c0
