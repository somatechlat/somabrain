"""Real Integration Test for Task Registry.

Adheres to VIBE rules:
- No Mocks.
- Real Database (Postgres).
- Real HTTP Client (httpx against localhost).
- Real Auth (via Token).
"""

import time
import uuid
import pytest
import httpx
from sqlalchemy import text
from somabrain.storage import db
from common.config.settings import settings

# Skip if we can't connect to the real DB
def _db_available() -> bool:
    try:
        engine = db.get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# Check if the service is reachable on localhost (real network check)
def _service_available() -> bool:
    endpoint = getattr(settings, "api_url", "http://localhost:9696")
    try:
        with httpx.Client(base_url=endpoint, timeout=2.0) as client:
            resp = client.get("/health")
            return resp.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not _db_available(), reason="Real Postgres not available")
@pytest.mark.skipif(not _service_available(), reason="Real API service not reachable")
def test_task_registry_lifecycle_real_network():
    """
    Test the full lifecycle of a task registry entry using real network requests against a running server.

    1. Clean up potential conflicts (DELETE).
    2. Register a new task (POST).
    3. Retrieve the task (GET).
    4. List tasks (GET).
    5. Update the task (PATCH).
    6. Delete the task (DELETE).
    """

    # 1. Setup Client (Real HTTPX Client)
    base_url = getattr(settings, "api_url", "http://localhost:9696")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # Generate a unique task name to avoid collision
    task_name = f"integration-task-{uuid.uuid4().hex[:8]}"

    # Real Auth Headers
    headers = {}
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"

    try:
        # 2. Register (POST)
        payload = {
            "name": task_name,
            "description": "Integration Test Task",
            "schema": {"type": "object", "properties": {"foo": {"type": "string"}}},
            "version": "1.0.0"
        }

        resp = client.post("/tasks/register", json=payload, headers=headers)

        assert resp.status_code in (200, 201), f"Registration failed: {resp.text}"

        data = resp.json()
        task_id = data["id"]
        assert data["name"] == task_name

        # 3. Retrieve (GET)
        resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

        # 4. List (GET)
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert any(t["id"] == task_id for t in tasks)

        # 5. Update (PATCH)
        update_payload = {"description": "Updated Description"}
        resp = client.patch(f"/tasks/{task_id}", json=update_payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated Description"

        # 6. Delete (DELETE)
        resp = client.delete(f"/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200

        # Verify deletion
        resp = client.get(f"/tasks/{task_id}", headers=headers)
        assert resp.status_code == 404

    finally:
        client.close()
