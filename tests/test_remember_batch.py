import os
import uuid

import requests


def test_remember_handles_batch_of_memories_live():
    base_url = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696")
    memory_url = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")

    # Basic health checks to fail fast if services are unreachable
    health = requests.get(f"{base_url}/health", timeout=5)
    assert health.status_code == 200, health.text

    # Ensure memory backend reachable before sending writes
    mem_health = requests.get(f"{memory_url}/health", timeout=5)
    assert mem_health.status_code in (200, 204, 404, 500), mem_health.text

    tasks = []
    namespace = health.json().get("namespace", "default")
    for idx in range(10):
        unique_suffix = uuid.uuid4().hex[:8]
        task = f"batch memory {idx}-{unique_suffix}"
        payload = {
            "task": task,
            "importance": 1,
            "memory_type": "episodic",
            "timestamp": f"2025-01-{idx+1:02d}T12:00:00Z",
            "namespace": namespace,
        }
        res = requests.post(
            f"{base_url}/remember",
            json={"coord": None, "payload": payload},
            timeout=10,
        )
        assert res.status_code == 200, res.text
        tasks.append(task)

    for task in tasks:
        recall_res = requests.post(
            f"{base_url}/recall",
            json={"query": task, "top_k": 5},
            timeout=10,
        )
        assert recall_res.status_code == 200, recall_res.text
        body = recall_res.json()
        assert isinstance(body, dict)
        memories = body.get("memory") or []
        assert any(
            m.get("task") == task for m in memories
        ), f"Missing memory for {task}"
