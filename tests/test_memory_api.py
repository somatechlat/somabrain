from __future__ import annotations

import types
from typing import Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from somabrain import runtime as rt
from somabrain.api.memory_api import router


class DummyEmbedder:
    def embed(self, text: str) -> List[float]:
        return [float(len(text) or 1), 1.0, 0.0]


class DummyWM:
    def __init__(self) -> None:
        self._records: Dict[str, List[dict]] = {}

    def admit(self, tenant_id: str, vec, payload: dict, cleanup_overlap=None) -> None:
        self._records.setdefault(tenant_id, []).append(payload)

    def recall(self, tenant_id: str, vec, top_k: int = 3):
        hits = [(1.0, payload) for payload in self._records.get(tenant_id, [])]
        return hits[:top_k]

    def items(self, tenant_id: str, limit: int | None = None) -> List[dict]:
        items = list(self._records.get(tenant_id, []))
        if limit is not None and limit > 0:
            return items[-limit:]
        return items


class DummyHit:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.score = 0.42
        self.coordinate = (1.0, 2.0, 3.0)


class DummyMemoryClient:
    def __init__(self) -> None:
        self._store: Dict[str, List[dict]] = {}
        self._outbox_path = ""

    async def aremember(self, coord_key: str, payload: dict, request_id: str | None = None):
        self._store.setdefault(coord_key, []).append(payload)
        return (1.0, 2.0, 3.0)

    async def aremember_bulk(
        self, items: List[tuple[str, dict]], request_id: str | None = None
    ) -> List[tuple[float, float, float]]:
        coords: List[tuple[float, float, float]] = []
        for idx, (coord_key, payload) in enumerate(items):
            self._store.setdefault(coord_key, []).append(payload)
            coords.append((1.0 + idx, 2.0 + idx, 3.0 + idx))
        return coords

    async def arecall(self, query: str, top_k: int = 3, universe: str | None = None, request_id: str | None = None):
        hits = [DummyHit(payload) for payload in self._store.get(query, [])]
        return hits[:top_k]


class DummyMultiTenantMemory:
    def __init__(self) -> None:
        self._client = DummyMemoryClient()

    def for_namespace(self, namespace: str) -> DummyMemoryClient:
        return self._client


@pytest.fixture(autouse=True)
def patch_runtime(monkeypatch):
    monkeypatch.setattr(rt, "embedder", DummyEmbedder(), raising=False)
    monkeypatch.setattr(rt, "mt_wm", DummyWM(), raising=False)
    monkeypatch.setattr(rt, "mt_memory", DummyMultiTenantMemory(), raising=False)
    monkeypatch.setattr(rt, "cfg", types.SimpleNamespace(namespace="base_ns"), raising=False)
    yield


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_memory_api_roundtrip(client: TestClient):
    tenant = "acme"
    namespace = "wm"
    key = "doc:1"
    value = {"text": "SomaBrain memo", "importance": 1}

    remember_resp = client.post(
        "/memory/remember",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "key": key,
            "value": value,
            "meta": {"source": "test"},
        },
    )
    assert remember_resp.status_code == 200
    remember_data = remember_resp.json()
    assert remember_data["ok"] is True
    coord = remember_data.get("coordinate")
    if coord is not None:
        assert len(coord) == 3
    assert remember_data["persisted_to_ltm"] is True
    assert remember_data["promoted_to_wm"] is True
    assert remember_data["signals"]["persisted_to_ltm"] is True
    assert remember_data["signals"]["promoted_to_wm"] is True
    assert isinstance(remember_data["warnings"], list)
    assert remember_data["request_id"]

    recall_resp = client.post(
        "/memory/recall",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "query": key,
            "top_k": 3,
        },
    )
    assert recall_resp.status_code == 200
    recall_data = recall_resp.json()
    assert recall_data["tenant"] == tenant
    assert recall_data["namespace"] == namespace
    assert recall_data["wm_hits"] >= 1
    assert any(item["layer"] == "wm" for item in recall_data["results"])

    metrics_resp = client.get(
        "/memory/metrics",
        params={"tenant": tenant, "namespace": namespace},
    )
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert metrics_data["tenant"] == tenant
    assert metrics_data["namespace"] == namespace
    assert metrics_data["wm_items"] >= 1
    assert "circuit_open" in metrics_data
    assert "outbox_pending" in metrics_data


def test_memory_api_batch_remember(client: TestClient):
    tenant = "acme"
    namespace = "wm"
    items = [
        {
            "key": "episode:1",
            "value": {"text": "episode one", "importance": 0.9},
            "tags": ["dialogue"],
            "signals": {"importance": 0.9, "ttl_seconds": 60},
        },
        {
            "key": "episode:2",
            "value": {"text": "episode two", "importance": 0.5},
            "meta": {"source": "unit-test"},
            "links": [{"rel": "follows", "target": "episode:1"}],
            "signals": {"novelty": 0.4},
        },
    ]

    resp = client.post(
        "/memory/remember/batch",
        json={"tenant": tenant, "namespace": namespace, "items": items},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["results"]) == 2
    for idx, result in enumerate(data["results"]):
        assert result["signals"]["persisted_to_ltm"] is True
        assert result["signals"]["promoted_to_wm"] in {True, False}
        assert isinstance(result["warnings"], list)
        assert result["request_id"].endswith(f":{idx}")

    recall_resp = client.post(
        "/memory/recall",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "query": "episode:1",
            "top_k": 2,
        },
    )
    assert recall_resp.status_code == 200
    recall_data = recall_resp.json()
    assert recall_data["wm_hits"] >= 1
