"""BrainClient — the working gRPC client for the ``soma.brain.v1.Brain`` service.

This is the implementation behind ``BrainPort``. It is the only client: the
Unix-socket and TCP bindings differ solely in how the channel is built
(:mod:`somabrain.transport.uds` and :mod:`somabrain.transport.net`), never in
how a call is made. One core, two adapters.

Every RPC is real. There is no fallback path, no in-process shortcut, and no
"return empty on failure" branch: an unreachable brain raises
:class:`BrainTransportError`, because an outage must not read as "you have no
memory" (``services/common/memory_contract.py`` — ``MemoryRecallUnavailable``,
R-05 / F-10).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence

import grpc

from somabrain.proto import brain_pb2_grpc
from somabrain.proto.brain_pb2 import (
    ForgetRequest,
    HealthRequest,
    MemoryWrite,
    RecallBatchRequest,
    RecallRequest,
    RememberBatchRequest,
    RememberRequest,
    StreamContextRequest,
)
from somabrain.transport import codec

logger = logging.getLogger("somabrain.transport.client")

# One deadline for every unary call. A brain that cannot answer within this
# window is treated as down rather than being waited on indefinitely while the
# caller's request deadline expires behind it.
DEFAULT_DEADLINE_S = 10.0


class BrainTransportError(RuntimeError):
    """Raised when the brain cannot be reached or refuses a call.

    Fail-closed: the caller sees the failure. Nothing here converts a transport
    error into an empty result set.
    """


class BrainClient:
    """A working client for the ``Brain`` service over any gRPC channel.

    Args:
        channel: A connected ``grpc.aio.Channel``, as built by
            :mod:`somabrain.transport.uds` or :mod:`somabrain.transport.net`.
        deadline_s: Per-call deadline in seconds.

    The client owns no channel lifecycle beyond closing the stub's calls; the
    caller closes the channel it built (or calls :meth:`aclose`, which does it
    if the channel exposes ``close``).
    """

    def __init__(
        self,
        channel: grpc.aio.Channel,
        *,
        metadata: tuple[tuple[str, str], ...] = (),
        deadline_s: float = DEFAULT_DEADLINE_S,
    ) -> None:
        self._channel = channel
        self._stub = brain_pb2_grpc.BrainStub(channel)
        self._metadata = tuple(metadata)
        self._deadline = float(deadline_s)

    # -- MemoryGateway surface ------------------------------------------------

    async def remember(self, write: MemoryWrite) -> list[dict]:
        """Store one memory; return one ack dict per store that accepted it."""
        req = RememberRequest(write=write)
        resp = await self._unary(self._stub.Remember, req)
        return [codec.decode_memory_ack(a) for a in resp.acks]

    async def remember_batch(self, writes: Sequence[MemoryWrite]) -> list[list[dict]]:
        """Store N memories in one round trip; results parallel ``writes``."""
        req = RememberBatchRequest(writes=list(writes))
        resp = await self._unary(self._stub.RememberBatch, req)
        return [
            [codec.decode_memory_ack(a) for a in r.acks] for r in resp.results
        ]

    async def recall(self, query: str, k: int, tenant_id: str) -> list[dict]:
        """Recall top-``k`` memories for one query, ranked by score."""
        req = RecallRequest(query=query, k=int(k), tenant_id=str(tenant_id))
        resp = await self._unary(self._stub.Recall, req)
        return [codec.decode_recall_hit(h) for h in resp.hits]

    async def recall_batch(
        self, queries: Sequence[RecallRequest]
    ) -> list[list[dict]]:
        """Run N recalls in one round trip; results parallel ``queries``."""
        req = RecallBatchRequest(queries=list(queries))
        resp = await self._unary(self._stub.RecallBatch, req)
        return [[codec.decode_recall_hit(h) for h in r.hits] for r in resp.results]

    async def forget(self, coord: str, tenant_id: str) -> bool:
        """Delete one memory by canonical coordinate.

        Returns:
            True only when the brain reported success. A transport failure
            raises; it never reports False, which would mean "already gone".
        """
        req = ForgetRequest(coord=str(coord), tenant_id=str(tenant_id))
        resp = await self._unary(self._stub.Forget, req)
        return bool(resp.ok)

    async def stream_context(
        self, query: str, k: int, tenant_id: str
    ) -> AsyncIterator[dict]:
        """Server-stream context events as each layer answers.

        Yields dicts shaped ``{"hit": {...}}``, ``{"done": {...}}`` or
        ``{"error": {...}}``. The stream is consumed lazily so a fast first hit
        reaches the caller before the slowest layer finishes.
        """
        req = StreamContextRequest(query=query, k=int(k), tenant_id=str(tenant_id))
        call = self._stub.StreamContext(req, metadata=self._metadata)
        try:
            async for event in call:
                which = event.WhichOneof("event")
                if which == "hit":
                    yield {"hit": codec.decode_recall_hit(event.hit)}
                elif which == "done":
                    yield {"done": {"total_hits": int(event.done.total_hits)}}
                elif which == "error":
                    yield {"error": {"message": event.error.message}}
                else:
                    raise BrainTransportError(
                        f"StreamContext returned an event with no payload ({which!r})"
                    )
        except grpc.aio.AioRpcError as exc:
            raise BrainTransportError(
                f"StreamContext failed: {exc.code()} {exc.details()}"
            ) from exc

    async def health(self) -> bool:
        """True when the brain answers its health RPC.

        Returns:
            False only for an explicit unhealthy reply. An unreachable brain
            raises — health must not collapse "down" into "not ok".
        """
        resp = await self._unary(self._stub.Health, HealthRequest())
        return bool(resp.ok)

    async def aclose(self) -> None:
        """Close the underlying channel. Idempotent."""
        close = getattr(self._channel, "close", None)
        if close is None:
            return
        try:
            result = close()
            if hasattr(result, "__await__"):
                await result
        except Exception:  # noqa: BLE001 - close must never mask the real error
            logger.debug("channel close raised during aclose", exc_info=True)

    # -- plumbing -------------------------------------------------------------

    async def _unary(self, method, request):
        try:
            return await method(
                request, timeout=self._deadline, metadata=self._metadata
            )
        except grpc.aio.AioRpcError as exc:
            code = exc.code()
            detail = exc.details()
            # UNAVAILABLE is the transport being gone. DEADLINE_EXCEEDED is it
            # being too slow. Both are outages and both must surface as one.
            raise BrainTransportError(
                f"brain call {getattr(method, '__name__', method)} failed: "
                f"{code} {detail}"
            ) from exc
