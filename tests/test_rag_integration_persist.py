from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import somabrain.app as app_module
from somabrain import runtime as rt_module

app = app_module.app


def _parse_coord_str(s: str):
    parts = [float(x.strip()) for x in s.split(",")]
    return (parts[0], parts[1], parts[2])

    # This test must run in its own process to guarantee backend state is not
    # reset by other tests
    # pytest -p pytest_forked is required for this marker to work
    # If not available, use pytest.mark.isolated or similar
    # See: https://docs.pytest.org/en/stable/how-to/xunit_setup.html#process-isolation


@pytest.mark.forked
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
    print(f"rt_module.mt_memory id: {id(rt_module.mt_memory)}")
    print(f"app_module.mt_memory id: {id(app_module.mt_memory)}")
    assert (
        rt_module.mt_memory is app_module.mt_memory
    ), "mt_memory instances are not the same!"
    backend = rt_module.mt_memory or app_module.mt_memory
    assert backend is not None
    print("backend id", id(backend))
    print("pool keys before call", list(backend._pool.keys()))
    mem = backend.for_namespace(ns)
    payloads = mem.payloads_for_coords([sc])
    print(f"payloads for {sc}: {payloads}")
    assert len(payloads) == 1
    # Links from session should be non-empty
    edges = mem.links_from(sc, limit=10)
    print(f"edges from {sc}: {edges}")
    assert isinstance(edges, list)
    assert len(edges) >= 1
