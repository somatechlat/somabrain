from __future__ import annotations

from fastapi.testclient import TestClient

from somabrain import runtime as rt
from somabrain.app import app


def _parse_coord_str(s: str):
    parts = [float(x.strip()) for x in s.split(",")]
    return (parts[0], parts[1], parts[2])


def test_rag_persist_and_links_local_backend():
    client = TestClient(app)
    # Use explicit tenant for namespace isolation
    headers = {"X-Tenant-ID": "ragtest"}
    body = {
        "query": "build solar panel",
        "top_k": 4,
        "retrievers": ["vector", "wm", "graph"],
        "persist": True,
    }
    r = client.post("/rag/retrieve", headers=headers, json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    # Expect a session coordinate present
    sess = data.get("session_coord")
    assert isinstance(sess, str) and "," in sess
    sc = _parse_coord_str(sess)
    # Probe memory directly: session payload present and links exist
    ns = data.get("namespace")
    assert isinstance(ns, str) and ns.endswith(":ragtest")
    assert rt.mt_memory is not None
    mem = rt.mt_memory.for_namespace(ns)
    payloads = mem.payloads_for_coords([sc])
    assert len(payloads) == 1
    # Links from session should be non-empty
    edges = mem.links_from(sc, limit=10)
    assert isinstance(edges, list)
    assert len(edges) >= 1
