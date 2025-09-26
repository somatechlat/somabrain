from fastapi.testclient import TestClient

from somabrain.app import app


def main():
    client = TestClient(app)

    # Health
    r = client.get("/health")
    assert r.status_code == 200, r.text

    # Recall before any memory write
    r = client.post("/recall", json={"query": "hello world", "top_k": 2})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "wm" in data and "memory" in data

    # Remember an episodic memory
    payload = {"task": "write docs", "importance": 2, "memory_type": "episodic"}
    r = client.post("/remember", json={"coord": None, "payload": payload})
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    # Recall again; memory backend should return something (best-effort)
    r = client.post("/recall", json={"query": "write documentation", "top_k": 3})
    assert r.status_code == 200, r.text
    data2 = r.json()
    assert "wm" in data2 and "memory" in data2

    # Act loop
    r = client.post("/act", json={"task": "summarize notes", "top_k": 2})
    assert r.status_code == 200, r.text
    act = r.json()
    assert act.get("task") == "summarize notes"
    assert isinstance(act.get("results"), list) and len(act["results"]) >= 1

    # Metrics
    r = client.get("/metrics")
    assert r.status_code == 200

    print("Smoke tests passed.")


if __name__ == "__main__":
    main()
