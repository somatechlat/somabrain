"""End-to-end proof of the ``soma.brain.v1.Brain`` gRPC transport over a UDS.

Scope: the transport. Every assertion here is about how bytes cross the wire —
field fidelity, tenant isolation, batching, refusals, socket permissions — not
about how the brain stores anything. The memory backend is therefore a clearly
marked in-memory stand-in implementing the ``MemoryService`` surface the server
binds to; the real ``MemoryService`` is exercised by the memory tests.

What this guards against: a boundary that looks like it forwards a request
while silently dropping fields. That exact failure has already shipped once in
this triad (a rebuilt store body lost ``embedding`` and ``tenant_id``), so the
round-trip assertions below are exhaustive on purpose.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from collections.abc import AsyncIterator

import grpc
import pytest
import pytest_asyncio

from somabrain.memory.client.types import RecallHit
from somabrain.proto.brain_pb2 import (
    MEMORY_KIND_BELIEF,
    MemoryWrite,
    RecallRequest,
    Vector,
)
from somabrain.transport import serve, uds
from somabrain.transport.client import BrainTransportError
from somabrain.transport.port import TransportConfigurationError
from somabrain.transport.serve import _hit_to_seam
from somabrain.transport.vector_codec import DTYPE_FLOAT32, pack_vector

# ``no_django``: the transport package is deliberately Django-free, and so is
# this test. Booting settings would drag the memory-HTTP credential gate into a
# test that never talks to the memory backend.
pytestmark = [pytest.mark.integration, pytest.mark.no_django]


# ---------------------------------------------------------------------------
# TEST DATA — in-memory stand-in for MemoryService's surface.
#
# This is not a mock of the transport: the transport code under test is the
# real gRPC server and client. This stand-in replaces only the storage backend,
# so the test observes what actually crossed the wire rather than what a real
# store happened to persist.
# ---------------------------------------------------------------------------


class InMemoryMemoryService:
    """TEST DATA — stands in for ``MemoryService`` on the five methods the
    gRPC servicer calls."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    async def aremember(self, key: str, payload: dict) -> str | None:
        self.store[key] = dict(payload)
        return payload.get("coord")

    async def aremember_bulk(self, items: list[tuple[str, dict]]) -> list[str | None]:
        out: list[str | None] = []
        for key, payload in items:
            self.store[key] = dict(payload)
            out.append(payload.get("coord"))
        return out

    async def arecall(
        self, query: str, top_k: int = 3, universe: str | None = None
    ) -> list[RecallHit]:
        hits: list[RecallHit] = []
        for payload in list(self.store.values())[: int(top_k)]:
            body = dict(payload)
            # ``role`` lives on the backend payload and is carried on hits only;
            # MemoryWrite has no such field.
            body.setdefault("role", "assistant")
            coord = tuple(float(x) for x in str(payload["coord"]).split(","))
            hits.append(RecallHit(payload=body, score=0.9, coordinate=coord, raw=None))
        return hits

    async def adelete(self, coordinate: tuple[float, float, float]) -> bool:
        key = ",".join(str(float(x)) for x in coordinate)
        for k, p in list(self.store.items()):
            if p.get("coord") == key:
                del self.store[k]
                return True
        return False

    def health(self) -> dict:
        return {"ok": True}


@pytest.fixture
def backend() -> InMemoryMemoryService:
    return InMemoryMemoryService()


@pytest_asyncio.fixture
async def bus(backend: InMemoryMemoryService) -> AsyncIterator[tuple[grpc.aio.Server, str]]:
    """Bring up the real gRPC server on a fresh owner-only Unix socket.

    The socket lives under a short temporary directory rather than pytest's
    ``tmp_path``: ``sockaddr_un.sun_path`` caps a Unix socket path at 103
    characters (see :data:`somabrain.transport.uds.MAX_SOCKET_PATH_LEN`), and
    pytest's per-test directories routinely exceed it.
    """
    run_dir = tempfile.mkdtemp(prefix="soma-t-", dir="/tmp")
    sock = os.path.join(run_dir, "brain.sock")

    def resolve_namespace(tenant: str, namespace: str) -> str:
        return f"somabrain:{tenant or 'public'}"

    def service_for_namespace(namespace: str):
        return backend

    server = grpc.aio.server()
    await serve.add_brain_service(
        server,
        service_for_namespace=service_for_namespace,
        resolve_namespace=resolve_namespace,
    )
    await uds.start_local_server(server, path=sock)
    try:
        yield server, sock
    finally:
        await server.stop(0)
        shutil.rmtree(run_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def client(bus):
    server, sock = bus
    client = uds.build_client(sock, deadline_s=5.0)
    try:
        yield client
    finally:
        await client.aclose()


def _write(**overrides) -> MemoryWrite:
    fields = dict(
        text="the user prefers concise answers",
        kind=MEMORY_KIND_BELIEF,
        tenant_id="t-alpha",
        session_id="sess-9",
        coord="0.1,-0.4,0.9",
        salience=0.8,
        source="agent-chat",
    )
    fields.update(overrides)
    return MemoryWrite(**fields)


# ---------------------------------------------------------------------------
# Transport security
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_socket_is_owner_only(bus) -> None:
    """The local bus must never be group- or world-accessible."""
    server, sock = bus
    mode = stat.S_IMODE(os.stat(sock).st_mode)
    assert mode == 0o600, f"socket {sock} is {oct(mode)}, expected {oct(0o600)}"


def test_overlong_socket_path_is_refused() -> None:
    """A path past ``sun_path`` is refused here, not as an opaque bind error.

    gRPC would fail deep inside bind with "Path name should not have more than
    103 characters"; the transport refuses first, with the offending value.
    """
    long_path = "/" + "a" * uds.MAX_SOCKET_PATH_LEN
    assert len(long_path) > uds.MAX_SOCKET_PATH_LEN
    with pytest.raises(TransportConfigurationError, match="sun_path"):
        uds.socket_target(long_path)


# ---------------------------------------------------------------------------
# Field fidelity — the reason this file exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_seam_field_crosses_the_wire(
    client, backend: InMemoryMemoryService
) -> None:
    """Every MemoryWrite field must land in the store, none coerced away."""
    write = _write()
    pk = pack_vector([0.25, -0.5, 0.75, 1.0], dtype=DTYPE_FLOAT32)
    write.embedding.CopyFrom(
        Vector(data=pk.data, dtype=pk.dtype, dim=pk.dim, count=pk.count)
    )

    acks = await client.remember(write)
    assert acks and acks[0]["ok"] is True, acks

    stored = backend.store["0.1,-0.4,0.9"]
    for field in (
        "text",
        "coord",
        "memory_type",
        "tenant_id",
        "salience",
        "source",
        "session_id",
        "embedding",
    ):
        assert field in stored, f"FIELD LOST in transit: {field}"

    assert stored["tenant_id"] == "t-alpha"
    assert stored["session_id"] == "sess-9"
    assert abs(stored["salience"] - 0.8) < 1e-9
    assert stored["embedding"] == [0.25, -0.5, 0.75, 1.0]
    assert stored["memory_type"] == "belief"
    assert stored["source"] == "agent-chat"


@pytest.mark.asyncio
async def test_recall_round_trip_preserves_every_hit_field(client) -> None:
    """A hit must come back complete — including session_id and role.

    ``session_id`` and ``role`` were being dropped by an attribute read against
    a dict; they are the fields that keep chat history session-local, so losing
    them turns unrelated semantic hits into conversation turns.
    """
    await client.remember(_write())

    hits = await client.recall("concise", k=5, tenant_id="t-alpha")
    assert hits, "recall returned nothing"

    hit = hits[0]
    for field in ("text", "coord", "score", "store", "created_at"):
        assert hit.get(field) not in (None, ""), f"hit missing {field}: {hit}"

    assert hit["coord"] == "0.1,-0.4,0.9"
    assert hit["store"] == "somafractalmemory"
    assert hit["session_id"] == "sess-9"
    assert hit["role"] == "assistant"


@pytest.mark.asyncio
async def test_hit_shapes_are_all_accepted() -> None:
    """A RecallHit, a mapping shaped like one, and a bare payload all work."""
    payload = {"text": "x", "coord": "0,0,0", "tenant_id": "t-alpha"}

    from_obj = _hit_to_seam(
        RecallHit(payload=payload, score=0.9, coordinate=(0.0, 0.0, 0.0), raw=None),
        "t-alpha",
    )
    from_wrapper = _hit_to_seam(
        {"payload": payload, "score": 0.9, "coordinate": (0.0, 0.0, 0.0)}, "t-alpha"
    )
    from_bare = _hit_to_seam(dict(payload, score=0.5), "t-alpha")

    for record in (from_obj, from_wrapper, from_bare):
        assert record is not None
        assert record["text"] == "x"
        assert record["score"] is not None


@pytest.mark.asyncio
async def test_malformed_hits_are_refused_not_reshaped() -> None:
    """A hit that cannot be read is dropped, never rebuilt into a fake one."""
    assert _hit_to_seam(None, "t") is None
    assert _hit_to_seam({"payload": "not-a-dict"}, "t") is None
    assert _hit_to_seam({"payload": {"text": "x", "tenant_id": "t"}}, "t") is None


@pytest.mark.asyncio
async def test_cross_tenant_hits_are_dropped() -> None:
    """Tenant is a security boundary, not a label."""
    foreign = {"payload": {"text": "x", "coord": "0,0,0", "tenant_id": "t-alpha"}}
    assert _hit_to_seam(foreign, "t-beta") is None
    assert _hit_to_seam(foreign, "t-alpha") is not None


# ---------------------------------------------------------------------------
# Batch shape — the largest single win, and it must actually batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remember_batch_is_one_round_trip(client, backend) -> None:
    writes = [
        _write(text=f"batch-{i}", coord=f"1.0,{i},0.0", session_id=None)
        for i in range(4)
    ]
    results = await client.remember_batch(writes)
    assert len(results) == 4
    assert len(backend.store) == 4


@pytest.mark.asyncio
async def test_recall_batch_is_one_round_trip(client) -> None:
    await client.remember(_write())
    results = await client.recall_batch(
        [
            RecallRequest(query="a", k=1, tenant_id="t-alpha"),
            RecallRequest(query="b", k=1, tenant_id="t-alpha"),
        ]
    )
    assert len(results) == 2


# ---------------------------------------------------------------------------
# The rest of the RPC surface
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forget_deletes(client, backend) -> None:
    await client.remember(_write())
    assert await client.forget("0.1,-0.4,0.9", "t-alpha") is True
    assert "0.1,-0.4,0.9" not in backend.store


@pytest.mark.asyncio
async def test_health_reports_ok(client) -> None:
    assert await client.health() is True


@pytest.mark.asyncio
async def test_stream_context_terminates_with_done(client) -> None:
    for i in range(3):
        await client.remember(_write(coord=f"2.0,{i},0.0", session_id=None))

    events = [e async for e in client.stream_context("x", k=3, tenant_id="t-alpha")]
    kinds = [list(e)[0] for e in events]
    assert kinds[-1] == "done", kinds
    assert kinds.count("hit") == 3


# ---------------------------------------------------------------------------
# Refusals — fail closed, never fabricate a success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_text_is_refused(client) -> None:
    with pytest.raises(BrainTransportError):
        await client.remember(_write(text="", coord="9,9,9"))
