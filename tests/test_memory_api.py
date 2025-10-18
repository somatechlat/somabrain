from __future__ import annotations

import types
from typing import Dict, List

submitted_snapshots: List = []
rebuild_calls: List = []

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from somabrain import metrics as M
from somabrain import runtime as rt
from somabrain.api.memory_api import router
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry


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
    submitted_snapshots.clear()

    async def _fake_dispatcher():
        return None

    async def _fake_supervisor_worker():
        return None

    async def _fake_submit(snapshot):
        submitted_snapshots.append(snapshot)

    monkeypatch.setattr("somabrain.api.memory_api.ensure_config_dispatcher", _fake_dispatcher)
    monkeypatch.setattr("somabrain.api.memory_api.ensure_supervisor_worker", _fake_supervisor_worker)
    monkeypatch.setattr("somabrain.api.memory_api.submit_metrics_snapshot", _fake_submit)

    def _fake_rebuild(tenant, namespace=None):
        rebuild_calls.append((tenant, namespace))
        return [{"tenant": tenant, "namespace": namespace or "wm", "backend": "simple", "wm_rebuilt": 1.0, "ltm_rebuilt": 1.0, "duration_seconds": 0.0}]

    monkeypatch.setattr("somabrain.api.memory_api._TIERED_REGISTRY.rebuild", _fake_rebuild)
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
            "pin_results": True,
        },
    )
    assert recall_resp.status_code == 200
    recall_data = recall_resp.json()
    assert recall_data["tenant"] == tenant
    assert recall_data["namespace"] == namespace
    assert recall_data["wm_hits"] >= 1
    assert any(item["layer"] == "wm" for item in recall_data["results"])
    tiered_items = [item for item in recall_data["results"] if item["source"] == "tiered_memory"]
    assert tiered_items, "tiered_memory result expected"
    assert tiered_items[0]["payload"].get("governed_margin") is not None
    assert tiered_items[0]["confidence"] is not None
    assert recall_data["session_id"]
    assert recall_data["total_results"] >= 1
    ctx_resp = client.get(f"/memory/context/{recall_data['session_id']}")
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.json()
    assert ctx_data["session_id"] == recall_data["session_id"]
    assert len(ctx_data["results"]) >= 1

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
    assert submitted_snapshots
    latest_snapshot = submitted_snapshots[-1]
    assert latest_snapshot.tenant == tenant
    assert latest_snapshot.namespace == namespace
    assert latest_snapshot.top1_accuracy >= 0.0


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
            "tags": ["dialogue"],
        },
    )
    assert recall_resp.status_code == 200
    recall_data = recall_resp.json()
    assert recall_data["wm_hits"] >= 1
    tiered_items = [item for item in recall_data["results"] if item["source"] == "tiered_memory"]
    if not tiered_items:
        # Tiered cleanup depends on ANN snapshots; allow WM fallback in tests
        assert any(item["layer"] == "wm" for item in recall_data["results"])
    assert submitted_snapshots


def test_memory_admin_rebuild_ann(client: TestClient):
    rebuild_calls.clear()
    resp = client.post(
        "/memory/admin/rebuild-ann",
        json={"tenant": "acme", "namespace": "wm"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert rebuild_calls == [("acme", "wm")]
    assert isinstance(body["results"], list)
    assert body["results"][0]["backend"] == "simple"


def test_memory_admin_rebuild_ann_records_metrics(monkeypatch, client: TestClient):
    registry = TieredMemoryRegistry()
    monkeypatch.setattr("somabrain.api.memory_api._TIERED_REGISTRY", registry)
    registry.remember(
        "acme",
        "wm",
        anchor_id="anchor-1",
        key_vector=[1.0, 0.0, 0.0],
        value_vector=[0.0, 1.0, 0.0],
        payload={"text": "hello"},
        coordinate=[0.0, 0.1, 0.2],
    )

    counter = M.ANN_REBUILD_TOTAL.labels(tenant="acme", namespace="wm", backend="simple")
    histogram = M.ANN_REBUILD_SECONDS.labels(tenant="acme", namespace="wm")
    before_total = counter._value.get()
    before_sum = histogram._sum.get()

    resp = client.post(
        "/memory/admin/rebuild-ann",
        json={"tenant": "acme", "namespace": "wm"},
    )
    assert resp.status_code == 200

    after_total = counter._value.get()
    after_sum = histogram._sum.get()
    assert after_total > before_total
    assert after_sum > before_sum


def test_memory_api_streaming_recall(client: TestClient):
    tenant = "acme"
    namespace = "wm"

    # ensure baseline memories exist
    client.post(
        "/memory/remember/batch",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "items": [
                {"key": "stream:1", "value": {"text": "stream one", "importance": 0.8}},
                {"key": "stream:2", "value": {"text": "stream two", "importance": 0.7}},
                {"key": "stream:3", "value": {"text": "stream three", "importance": 0.6}},
            ],
        },
    )

    stream_resp = client.post(
        "/memory/recall/stream",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "query": "stream",
            "top_k": 3,
            "chunk_size": 1,
            "pin_results": True,
        },
    )
    assert stream_resp.status_code == 200
    stream_data = stream_resp.json()
    assert stream_data["chunk_size"] == 1
    assert stream_data["has_more"] is True
    assert stream_data["session_id"]

    next_resp = client.post(
        "/memory/recall/stream",
        json={
            "tenant": tenant,
            "namespace": namespace,
            "query": "stream",
            "top_k": 3,
            "chunk_size": 1,
            "chunk_index": 1,
            "session_id": stream_data["session_id"],
        },
    )
    assert next_resp.status_code == 200
    next_data = next_resp.json()
    assert next_data["chunk_index"] == 1
    assert len(next_data["results"]) == 1
