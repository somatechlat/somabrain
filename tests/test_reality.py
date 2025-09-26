import sys
from importlib import import_module

from fastapi.testclient import TestClient


def main():
    for m in list(sys.modules.keys()):
        if m.startswith("somabrain"):
            sys.modules.pop(m, None)
    app_mod = import_module("somabrain.app")
    app = app_mod.app
    client = TestClient(app)

    # Recall with empty store -> reality ok may be False
    r = client.post("/recall", json={"query": "q", "top_k": 2})
    assert r.status_code == 200
    data = r.json()
    assert "reality" in data

    # After a remember, stub recall returns recent -> reality ok True
    client.post(
        "/remember",
        json={
            "coord": None,
            "payload": {"task": "seed", "importance": 1, "memory_type": "episodic"},
        },
    )
    r = client.post(
        "/recall", json={"query": "q2", "top_k": 2}, headers={"X-Min-Sources": "1"}
    )
    assert r.status_code == 200
    data2 = r.json()
    assert data2.get("reality", {}).get("ok") is True
    print("Reality test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
