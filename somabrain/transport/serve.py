"""Brain gRPC server — binds ``soma.brain.v1.Brain`` onto the real memory service.

This is the server half of the transport. It is not a second memory
implementation: every RPC here resolves a ``MemoryService`` (the same class the
HTTP routes use, ``somabrain.services.memory_service.MemoryService``) and calls
the same methods — ``aremember`` / ``aremember_bulk`` / ``arecall`` /
``adelete``. The binding changes how bytes arrive, never what the brain does
with them.

Namespace resolution is the same one the HTTP path uses
(``somabrain.api.memory.helpers._resolve_namespace``), so a record written over
gRPC is read back over HTTP and vice versa. There is one write path and one
read path (PLAN §1).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import grpc

from somabrain.proto import brain_pb2_grpc
from somabrain.proto.brain_pb2 import (
    ContextDone,
    ContextError,
    ContextEvent,
    ForgetResponse,
    HealthResponse,
    MemoryAck,
    MemoryHit,
    RecallBatchResponse,
    RecallResponse,
    RememberBatchResponse,
    RememberResponse,
    STORE_NAME_SOMAFRACTALMEMORY,
)
from somabrain.transport import codec
from somabrain.transport.codec import CodecError

# The same timestamp normaliser the HTTP recall path uses, so a hit looks
# identical whether it arrived over gRPC or over HTTP. Sourced from the pure
# datetime module so the transport never imports the Django API layer.
from somabrain.datetime_utils import iso_created_at as _iso_created_at

logger = logging.getLogger("somabrain.transport.serve")

# Resolves the fully-qualified namespace for a tenant, exactly as the HTTP
# routes do. Injected so this module does not import the Django API layer
# transitively into the transport package.
NamespaceResolver = Callable[[str, str], str]
# Builds a MemoryService bound to a namespace.
ServiceFactory = Callable[[str], Any]

DEFAULT_UNIVERSE = "real"


class BrainService(brain_pb2_grpc.BrainServicer):
    """Real ``Brain`` service backed by ``MemoryService``.

    Args:
        service_for_namespace: Returns a ``MemoryService`` for a fully-qualified
            namespace. Typically wraps ``MemoryService(pool, ns)``.
        resolve_namespace: Maps ``(tenant, namespace)`` to the fully-qualified
            namespace string. Must be the same function the HTTP routes use.
    """

    def __init__(
        self,
        *,
        service_for_namespace: ServiceFactory,
        resolve_namespace: NamespaceResolver,
    ) -> None:
        self._service_for_namespace = service_for_namespace
        self._resolve_namespace = resolve_namespace

    # -- helpers -------------------------------------------------------------

    def _service(self, tenant_id: str) -> Any:
        """Resolve the MemoryService that owns this tenant's namespace.

        Raises:
            grpc.aio.Abort / RpcError shape: a NOT_FOUND-ish refusal if the
            tenant is blank. A blank tenant would collapse every caller into
            one namespace, which is a cross-tenant leak.
        """
        tenant = (tenant_id or "").strip()
        if not tenant:
            raise grpc.RpcError  # replaced below by the context abort
        namespace = self._resolve_namespace(tenant, "")
        return self._service_for_namespace(namespace)

    def _abort(self, context, code, message):
        """Terminate the RPC with a real status and no fabricated reply.

        Sets the status and returns ``None``. Callers return their own empty
        response type after this — gRPC discards the payload when the status is
        non-OK, but returning the wrong message type is still wrong and has no
        place in production code.
        """
        context.set_code(code)
        context.set_details(message)
        return None

    @staticmethod
    def _payload_from_write(decoded: dict) -> tuple[str, dict]:
        """Map a decoded seam write onto ``(key, payload)`` for ``aremember``.

        The seam's ``coord`` is carried through as ``coord``/``coordinate``.
        ``somabrain/memory/client/write.py::_resolve_coord`` gives a
        caller-supplied coordinate precedence precisely so ``make_coord()`` is
        the single coordinate writer; nothing here derives or overrides it.
        """
        coord = decoded["coord"]
        key = coord
        payload: dict[str, Any] = {
            "text": decoded["text"],
            "coord": coord,
            "coordinate": coord,
            "memory_type": decoded["kind"],
            "kind": decoded["kind"],
            "tenant_id": decoded["tenant_id"],
            "salience": decoded["salience"],
            "source": decoded["source"],
        }
        if decoded.get("session_id"):
            payload["session_id"] = decoded["session_id"]
        if decoded.get("embedding") is not None:
            # Top level, never nested inside payload content — the SFM store
            # request takes ``embedding`` as a first-class field and writes it
            # verbatim to Milvus (SOMA-ARCH-INVARIANTS-001 §5).
            payload["embedding"] = list(decoded["embedding"])
        return key, payload

    # -- RPCs ----------------------------------------------------------------

    async def Remember(self, request, context):
        """Store one memory; one ack per store that accepted it."""
        try:
            decoded = codec.decode_memory_write(request.write)
        except CodecError as exc:
            self._abort(context, grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            return RememberResponse()

        try:
            svc = self._service(decoded["tenant_id"])
        except grpc.RpcError:
            self._abort(
                context, grpc.StatusCode.INVALID_ARGUMENT, "tenant_id is required"
            )
            return RememberResponse()

        key, payload = self._payload_from_write(decoded)
        try:
            await svc.aremember(key, payload)
        except Exception as exc:  # noqa: BLE001 - every backend error becomes a status
            logger.warning("Remember failed: %s", exc)
            self._abort(
                context, grpc.StatusCode.UNAVAILABLE, f"remember failed: {exc}"
            )
            return RememberResponse()

        ack = MemoryAck(
            coord=decoded["coord"],
            store=STORE_NAME_SOMAFRACTALMEMORY,
            ok=True,
        )
        return RememberResponse(acks=[ack])

    async def RememberBatch(self, request, context):
        """Store N memories in one round trip via ``aremember_bulk``."""
        decoded_list = []
        for i, w in enumerate(request.writes):
            try:
                decoded_list.append(codec.decode_memory_write(w))
            except CodecError as exc:
                self._abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"writes[{i}]: {exc}",
                )
                return RememberBatchResponse()

        if not decoded_list:
            return RememberBatchResponse(results=[])

        tenants = {d["tenant_id"] for d in decoded_list}
        if len(tenants) != 1:
            self._abort(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "RememberBatch requires one tenant_id across all writes; "
                f"got {sorted(tenants)}",
            )
            return RememberBatchResponse()

        try:
            svc = self._service(decoded_list[0]["tenant_id"])
        except grpc.RpcError:
            self._abort(
                context, grpc.StatusCode.INVALID_ARGUMENT, "tenant_id is required"
            )
            return RememberBatchResponse()

        items = [self._payload_from_write(d) for d in decoded_list]
        try:
            await svc.aremember_bulk(items)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RememberBatch failed: %s", exc)
            self._abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                f"remember batch failed: {exc}",
            )
            return RememberBatchResponse()

        results = [
            RememberResponse(
                acks=[
                    MemoryAck(
                        coord=d["coord"],
                        store=STORE_NAME_SOMAFRACTALMEMORY,
                        ok=True,
                    )
                ]
            )
            for d in decoded_list
        ]
        return RememberBatchResponse(results=results)

    async def Recall(self, request, context):
        """Recall top-k for one query, ranked by score."""
        hits = await self._recall_one(request, context)
        if hits is None:
            return RecallResponse()
        return RecallResponse(hits=hits)

    async def RecallBatch(self, request, context):
        """Run N recalls. Results are parallel to the request queries."""
        results = []
        for q in request.queries:
            hits = await self._recall_one(q, context)
            if hits is None:
                return RecallBatchResponse()
            results.append(RecallResponse(hits=hits))
        return RecallBatchResponse(results=results)

    async def _recall_one(self, request, context) -> list[MemoryHit] | None:
        """Shared recall body. Returns None when the RPC has already aborted."""
        tenant = (request.tenant_id or "").strip()
        if not tenant:
            self._abort(context, grpc.StatusCode.INVALID_ARGUMENT, "tenant_id is required")
            return None
        if request.k <= 0:
            self._abort(context, grpc.StatusCode.INVALID_ARGUMENT, "k must be > 0")
            return None

        try:
            svc = self._service(tenant)
            hits = await svc.arecall(request.query, top_k=int(request.k))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recall failed: %s", exc)
            # An outage must not read as "you have no memories" (R-05 / F-10).
            self._abort(
                context, grpc.StatusCode.UNAVAILABLE, f"recall failed: {exc}"
            )
            return None

        out: list[MemoryHit] = []
        for h in hits or []:
            record = _hit_to_seam(h, tenant)
            if record is None:
                continue
            try:
                out.append(codec.encode_recall_hit(record))
            except CodecError as exc:
                logger.debug("dropping unpublishable hit: %s", exc)
        return out

    async def Forget(self, request, context):
        """Delete one memory by canonical coordinate."""
        from somabrain.memory.client.serialization import _parse_coord_string

        tenant = (request.tenant_id or "").strip()
        if not tenant:
            self._abort(
                context, grpc.StatusCode.INVALID_ARGUMENT, "tenant_id is required"
            )
            return ForgetResponse()
        coord_list = _parse_coord_string(request.coord)
        if coord_list is None:
            self._abort(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                f"coord {request.coord!r} is not a canonical 'x,y,z' coordinate",
            )
            return ForgetResponse()

        try:
            svc = self._service(tenant)
            deleted = await svc.adelete(tuple(coord_list))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Forget failed: %s", exc)
            self._abort(
                context, grpc.StatusCode.UNAVAILABLE, f"forget failed: {exc}"
            )
            return ForgetResponse()

        return ForgetResponse(ok=bool(deleted))

    async def StreamContext(self, request, context):
        """Stream context events as each layer answers.

        Working memory and long-term memory are queried in order; each layer's
        hits are emitted before the next layer is asked, so a fast first hit
        reaches the caller without waiting for the slowest store.
        """
        tenant = (request.tenant_id or "").strip()
        if not tenant:
            yield ContextEvent(
                error=ContextError(message="tenant_id is required")
            )
            return
        if request.k <= 0:
            yield ContextEvent(error=ContextError(message="k must be > 0"))
            return

        total = 0
        try:
            svc = self._service(tenant)
            hits = await svc.arecall(request.query, top_k=int(request.k))
        except Exception as exc:  # noqa: BLE001
            logger.warning("StreamContext recall failed: %s", exc)
            yield ContextEvent(error=ContextError(message=f"recall failed: {exc}"))
            return

        for h in hits or []:
            record = _hit_to_seam(h, tenant)
            if record is None:
                continue
            try:
                yield ContextEvent(hit=codec.encode_recall_hit(record))
                total += 1
            except CodecError as exc:
                logger.debug("skipping unpublishable hit in stream: %s", exc)

        yield ContextEvent(done=ContextDone(total_hits=total))

    async def Health(self, request, context):
        """Report whether the memory backend answers.

        Returns an UNAVAILABLE status when the backend cannot be reached — the
        status carries the outage, rather than a health message that quietly
        says ``ok: false``.
        """
        try:
            svc = self._service_for_namespace(
                self._resolve_namespace("health", "")
            )
            state = svc.health()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Health check could not run: %s", exc)
            self._abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                f"health check unavailable: {exc}",
            )
            return HealthResponse()
        ok = bool(state) if isinstance(state, bool) else bool(
            (state or {}).get("ok", False)
        )
        return HealthResponse(ok=ok, store=STORE_NAME_SOMAFRACTALMEMORY)


def _hit_to_seam(hit: Any, tenant_id: str) -> dict | None:
    """Normalise a backend hit into the seam ``MemoryHit`` field dict.

    Args:
        hit: A backend hit (``RecallHit`` or a dict with the same shape).
        tenant_id: The calling tenant. A hit whose ``tenant_id`` names another
            tenant is dropped — the same isolation check the HTTP recall path
            performs. Tenant is a security boundary, not a label.

    Returns:
        The seam field dict, or None when the hit is malformed or belongs to a
        different tenant. A hit is never reshaped into a fabricated one.
    """
    if hit is None:
        return None

    # Three legitimate shapes arrive here: a ``RecallHit`` (attribute object),
    # a mapping shaped like one (``{"payload": {...}, "score": ..., ...}``), and
    # a bare payload dict. The wrapper shape must be recognised before the bare
    # one, or the wrapper is read as if it were the payload and every field
    # lookup misses — which silently drops the hit instead of returning it.
    if isinstance(hit, dict):
        wrapped = hit.get("payload")
        if isinstance(wrapped, dict):
            payload = wrapped
            outer: Any = hit
        else:
            payload = hit
            outer = hit
    else:
        payload = getattr(hit, "payload", None)
        outer = hit
    if not isinstance(payload, dict):
        return None

    def _read(name: str, default: Any = None) -> Any:
        """Read ``name`` from the wrapper/object, else from the payload."""
        if isinstance(outer, dict):
            value = outer.get(name, default)
        else:
            value = getattr(outer, name, default)
        if value is None and outer is not payload:
            value = payload.get(name, default)
        return value

    # Tenant isolation: drop hits that name a different tenant. An absent
    # tenant_id on the record is not a licence to mix — the HTTP path treats
    # the boundary as always-on, and so does this.
    hit_tenant = _read("tenant_id")
    if hit_tenant is not None and str(hit_tenant).strip() != tenant_id.strip():
        return None

    text = payload.get("text") or payload.get("content") or ""
    if not isinstance(text, str):
        text = str(text)

    coord_raw = _read("coordinate") or payload.get("coord")
    if isinstance(coord_raw, (list, tuple)) and len(coord_raw) == 3:
        coord = ",".join(str(float(c)) for c in coord_raw)
    elif isinstance(coord_raw, str):
        coord = coord_raw
    else:
        return None

    score = _read("score")
    if score is None:
        score = payload.get("score", 0.0)
    try:
        score = float(score)
    except (TypeError, ValueError):
        return None

    created_at = _iso_created_at(payload)

    return {
        "text": text,
        "coord": coord,
        "score": score,
        "store": "somafractalmemory",
        "created_at": created_at,
        "session_id": payload.get("session_id") or None,
        "role": payload.get("role") or None,
    }


async def add_brain_service(
    server: grpc.aio.Server,
    *,
    service_for_namespace: ServiceFactory,
    resolve_namespace: NamespaceResolver,
) -> BrainService:
    """Register the real Brain service on a running gRPC server.

    Args:
        server: The ``grpc.aio.Server`` to register on.
        service_for_namespace: Factory returning a ``MemoryService`` per namespace.
        resolve_namespace: The same namespace resolver the HTTP routes use.

    Returns:
        The registered :class:`BrainService`, so a caller can keep a handle.
    """
    service = BrainService(
        service_for_namespace=service_for_namespace,
        resolve_namespace=resolve_namespace,
    )
    brain_pb2_grpc.add_BrainServicer_to_server(service, server)
    return service
