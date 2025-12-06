"""Real Integration Test for Task Registry.

Adheres to VIBE rules:
- No Mocks.
- Real Database (Postgres).
- Real HTTP Client.
- Real Auth (via Token).
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from somabrain.app import app
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

@pytest.mark.skipif(not _db_available(), reason="Real Postgres not available")
def test_task_registry_lifecycle():
    """
    Test the full lifecycle of a task registry entry using real infrastructure.

    1. Clean up potential conflicts (DELETE).
    2. Register a new task (POST).
    3. Retrieve the task (GET).
    4. List tasks (GET).
    5. Update the task (PATCH).
    6. Delete the task (DELETE).
    """

    # 1. Setup Client
    client = TestClient(app)

    # Generate a unique task name to avoid collision
    task_name = f"integration-task-{uuid.uuid4().hex[:8]}"

    # Create a valid token (or use a bypass if configured for dev, but we prefer real headers)
    # Since we can't easily generate a signed JWT without the secret, and we are in Vibe Rules mode,
    # we should check if the environment allows us to use the configured API token.
    # settings.api_token is used for simple auth.
    headers = {}
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"

    # 2. Register (POST)
    payload = {
        "name": task_name,
        "description": "Integration Test Task",
        "schema": {"type": "object", "properties": {"foo": {"type": "string"}}},
        "version": "1.0.0"
    }

    # We expect this to fail if Auth is strictly required and we don't have a valid token.
    # However, for this test to pass in "Real Code" mode, we assume the environment is set up with
    # a known token or we are running in a mode where we can authenticate.

    resp = client.post("/tasks/register", json=payload, headers=headers)

    # If auth fails, we can't proceed. Assert 200 or 401 to fail fast with clarity.
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
