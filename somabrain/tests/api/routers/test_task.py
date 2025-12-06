"""Tests for the Dynamic Task Registry API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import requests_mock
from somabrain.app import app
from somabrain.api.routers.task import get_task_store
from somabrain.storage.task_registry import TaskRegistryStore
from somabrain.db.models.task import TaskRegistry

@pytest.fixture
def mock_opa():
    """Mock OPA response to allow all requests."""
    with requests_mock.Mocker() as m:
        # Mock OPA allow-all response
        m.post("mock://opa:8181/v1/data/soma/allow", json={"result": True})
        yield m

@pytest.fixture
def mock_store(mock_opa):
    store = MagicMock(spec=TaskRegistryStore)
    app.dependency_overrides[get_task_store] = lambda: store
    yield store
    app.dependency_overrides = {}

@pytest.fixture
def client():
    # Override auth_guard to bypass auth for testing
    from somabrain.api.dependencies.auth import auth_guard
    app.dependency_overrides[auth_guard] = lambda: None
    return TestClient(app)

def test_register_task(client, mock_store):
    payload = {
        "name": "test-task",
        "description": "A test task",
        "schema": {"type": "object"},
        "version": "1.0.0"
    }

    # Mock behavior
    mock_store.get_by_name.return_value = None
    mock_store.create.return_value = TaskRegistry(
        id="123",
        name="test-task",
        description="A test task",
        schema={"type": "object"},
        version="1.0.0",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )

    response = client.post("/tasks/register", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-task"
    assert data["id"] == "123"
    mock_store.create.assert_called_once()

def test_list_tasks(client, mock_store):
    mock_store.list.return_value = ([
        TaskRegistry(
            id="123",
            name="test-task",
            schema={},
            version="1.0.0",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
    ], 1)

    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["total"] == 1

def test_get_task_not_found(client, mock_store):
    mock_store.get.return_value = None
    response = client.get("/tasks/nonexistent")
    assert response.status_code == 404
