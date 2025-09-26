from brain.adapters.memstore_adapter import MemstoreAdapter
from tests.support.memstore_test_app import start_test_server


def test_memstore_end_to_end():
    # Start in-process test memstore
    port, thread = start_test_server()
    base = f"http://127.0.0.1:{port}"
    m = MemstoreAdapter(base_url=base)

    # Health
    h = m.health()
    assert h["status"] == "ok"

    # Upsert
    items = [{"id": "a", "embedding": [0.1, 0.2, 0.3], "metadata": {"k": "v"}}]
    up = m.upsert(items)
    assert up.get("upserted", 0) == 1

    # Get
    got = m.get("a")
    assert got is not None and got["id"] == "a"

    # Search
    res = m.search([0.1, 0.2, 0.3], top_k=5)
    assert isinstance(res, list)
    assert any(r["id"] == "a" for r in res)

    # Delete
    assert m.delete("a") is True
    assert m.get("a") is None
