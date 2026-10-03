from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Iterable
from typing import Any

from django.conf import settings

from .serialization import (
    _compat_enrich_payload,
    _explicit_coord,
    _extract_memory_coord,
    _stable_coord,
)

logger = logging.getLogger(__name__)


def _resolve_coord(
    coord_key: str, payload: dict, universe: str
) -> tuple[float, float, float]:
    """Resolve the storage identity for a write.

    A caller-supplied ``coord`` / ``coordinate`` wins so the seam's
    ``make_coord()`` value is the single coordinate writer. Without one the
    deterministic ``_stable_coord(universe::coord_key)`` is used.
    """
    explicit = _explicit_coord(payload)
    if explicit is not None:
        return explicit
    return _stable_coord(f"{universe}::{coord_key}")


def _seam_store_fields(cfg: Any, enriched: dict, payload: dict) -> dict[str, Any]:
    """Return the first-class ``MemoryStoreRequest`` fields for a store body.

    ARCHITECTURE-INVARIANTS §5: ``embedding`` and ``tenant_id`` are first-class
    top-level fields on ``MemoryStoreRequest`` — never only inside ``payload``.
    Every write path must add these to its body, not just the single-write one.

    Regression guard: earlier versions of the *bulk* paths built their body as
    ``{coord, payload, memory_type}`` and silently stripped both fields, so
    every batch write fell back to hash vectors and lost tenant isolation. One
    helper, used by every path, so the two cannot drift apart again.
    """
    from somabrain.memory.remember import _get_tenant_namespace

    tenant, _ns = _get_tenant_namespace(cfg, payload)
    embedding = enriched.get("embedding")
    if embedding is None:
        embedding = payload.get("embedding")

    fields: dict[str, Any] = {"tenant_id": tenant or None}
    if embedding is not None:
        fields["embedding"] = embedding
    return fields


class WriteMixin:
    """Handles memory persistence operations."""

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> tuple[float, float, float]:
        """Store a memory using a stable coordinate derived from coord_key."""
        enriched, universe, _hdr = _compat_enrich_payload(self.cfg, payload, coord_key)
        coord = _resolve_coord(coord_key, payload, universe)

        # ensure we don't mutate caller's dict; copy and normalize metadata
        payload = dict(enriched)
        payload.setdefault("memory_type", "episodic")
        payload.setdefault("timestamp", time.time())
        payload.setdefault("universe", universe)

        # Light-touch metadata normalization (phase, quality, domains)
        try:
            if "phase" in payload and isinstance(payload["phase"], str):
                payload["phase"] = payload["phase"].strip().lower() or None
            if "quality_score" in payload:
                try:
                    qs = float(payload["quality_score"])
                    payload["quality_score"] = max(0.0, min(1.0, qs))
                except Exception:
                    payload.pop("quality_score", None)
            if "domains" in payload:
                dval = payload["domains"]
                if isinstance(dval, str):
                    parts = [
                        p.strip().lower()
                        for p in dval.replace(",", " ").split()
                        if p.strip()
                    ]
                    payload["domains"] = parts or []
                elif isinstance(dval, (list, tuple)):
                    cleaned = []
                    for x in dval:
                        if isinstance(x, str) and x.strip():
                            cleaned.append(x.strip().lower())
                    payload["domains"] = cleaned
                else:
                    payload.pop("domains", None)
            if "reasoning_chain" in payload and isinstance(
                payload["reasoning_chain"], str
            ):
                rc = payload["reasoning_chain"].strip()
                if rc:
                    payload["reasoning_chain"] = [rc]
                else:
                    payload.pop("reasoning_chain", None)
        except Exception:
            pass

        try:
            loop = asyncio.get_running_loop()
            in_async = True
        except Exception:
            in_async = False

        try:
            payload.setdefault("coordinate", coord)
        except Exception:
            pass

        rid = request_id or str(uuid.uuid4())

        if in_async:
            try:
                loop = asyncio.get_running_loop()
                if self._http_async is not None:
                    try:
                        loop.create_task(
                            self._aremember_background(coord_key, payload, rid)
                        )
                    except Exception as e:
                        logger.debug("_aremember_background scheduling failed: %r", e)
                        loop.run_in_executor(
                            None, self._remember_sync_persist, coord_key, payload, rid
                        )
                else:
                    loop.run_in_executor(
                        None, self._remember_sync_persist, coord_key, payload, rid
                    )
            except Exception:
                try:
                    self._remember_sync_persist(coord_key, payload, rid)
                except Exception:
                    pass
            return coord

        # Sync callers with fast_ack (optional)
        fast_ack = False
        if settings is not None:
            try:
                fast_ack = bool(getattr(settings, "memory_fast_ack", False))
            except Exception:
                pass

        if fast_ack:
            try:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(
                    None, self._remember_sync_persist, coord_key, payload, rid
                )
            except Exception:
                try:
                    self._remember_sync_persist(coord_key, payload, rid)
                except Exception:
                    pass
            return coord

        server_coord = self._remember_sync_persist(coord_key, payload, rid)
        if server_coord:
            coord = server_coord
            try:
                payload["coordinate"] = server_coord
            except Exception:
                pass
        return coord

    def remember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> list[tuple[float, float, float]]:
        records = list(items)
        if not records:
            return []

        prepared: list[dict[str, Any]] = []
        universes: list[str] = []
        coords: list[tuple[float, float, float]] = []

        for coord_key, payload in records:
            enriched, universe, _ = _compat_enrich_payload(self.cfg, payload, coord_key)
            coord = _resolve_coord(coord_key, payload, universe)
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            memory_type = str(
                enriched_payload.get("memory_type")
                or enriched_payload.get("type")
                or "episodic"
            )
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "memory_type": memory_type,
                "type": memory_type,
            }
            # First-class seam fields — the bulk path must not strip them.
            body.update(_seam_store_fields(self.cfg, enriched, payload))
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED: HTTP memory backend not available (bulk remember)."
            )

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        unique_universes = {u for u in universes if u}
        if len(unique_universes) == 1:
            headers["X-Universe"] = unique_universes.pop()

        success, status, response = self._store_bulk_http_sync(
            [entry["body"] for entry in prepared], headers
        )
        if success and response is not None:
            returned: list[Any] = []
            if isinstance(response, dict):
                for key in ("items", "results", "memories", "entries"):
                    seq = response.get(key)
                    if isinstance(seq, list):
                        returned = seq
                        break
            elif isinstance(response, list):
                returned = response
            for idx, entry in enumerate(returned[: len(prepared)]):
                server_coord = _extract_memory_coord(
                    entry, idempotency_key=f"{rid}:{idx}"
                )
                if server_coord:
                    coords[idx] = server_coord
                    try:
                        prepared[idx]["body"]["payload"]["coordinate"] = server_coord
                    except Exception:
                        pass
            return coords

        if status in (404, 405):
            for idx, entry in enumerate(prepared):
                single_headers = dict(headers)
                single_headers["X-Request-ID"] = f"{rid}:{idx}"
                ok, resp = self._store_http_sync(entry["body"], single_headers)
                if ok and resp is not None:
                    server_coord = _extract_memory_coord(
                        resp, idempotency_key=single_headers["X-Request-ID"]
                    )
                    if server_coord:
                        coords[idx] = server_coord
            return coords

        raise RuntimeError("Memory service unavailable (bulk remember failed)")

    async def aremember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> tuple[float, float, float]:
        """Store a memory asynchronously, waiting for real backend confirmation.

        Awaits persistence and propagates failures — never silent success.
        """
        if self._http_async is not None:
            try:
                enriched, universe, compat_hdr = _compat_enrich_payload(
                    self.cfg, payload, coord_key
                )
                coord = _resolve_coord(coord_key, payload, universe)
                enriched = dict(enriched)
                enriched.setdefault("coordinate", coord)
                memory_type = str(
                    enriched.get("memory_type") or enriched.get("type") or "episodic"
                )
                body: dict[str, Any] = {
                    "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                    "payload": enriched,
                    "memory_type": memory_type,
                    "type": memory_type,
                }
                # First-class seam fields — every write path, not just the sync one.
                body.update(_seam_store_fields(self.cfg, enriched, payload))

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                rid_hdr.update(compat_hdr)
                ok, response_data = await self._store_http_async(body, rid_hdr)
                if ok:
                    server_coord = None
                    if response_data is not None:
                        try:
                            server_coord = _extract_memory_coord(
                                response_data, idempotency_key=rid
                            )
                        except Exception:
                            server_coord = None
                    return server_coord or coord
                logger.warning(
                    "aremember backend rejected write key=%s ok=%s resp=%r",
                    coord_key,
                    ok,
                    response_data,
                )
                raise RuntimeError(
                    f"Memory service unavailable (remember persist failed): {response_data!r}"
                )
            except RuntimeError:
                raise
            except Exception as exc:
                logger.warning("aremember async path failed key=%s: %s", coord_key, exc)

        # Fall back to the synchronous persistence helper and *await* the result.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._remember_sync_persist, coord_key, payload, request_id
        )

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> list[tuple[float, float, float]]:
        records = list(items)
        if not records:
            return []

        if self._http_async is None:
            return self.remember_bulk(records, request_id=request_id)

        prepared: list[dict[str, Any]] = []
        universes: list[str] = []
        coords: list[tuple[float, float, float]] = []

        for coord_key, payload in records:
            enriched, universe, _ = _compat_enrich_payload(self.cfg, payload, coord_key)
            coord = _resolve_coord(coord_key, payload, universe)
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "type": enriched_payload.get("memory_type", "episodic"),
            }
            # First-class seam fields — the bulk path must not strip them.
            body.update(_seam_store_fields(self.cfg, enriched, payload))
            universes.append(universe)
            coords.append(coord)
            prepared.append(
                {
                    "coord_key": coord_key,
                    "body": body,
                    "universe": universe,
                }
            )

        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        unique_universes = {u for u in universes if u}
        if len(unique_universes) == 1:
            headers["X-Universe"] = unique_universes.pop()

        success, status, response = await self._store_bulk_http_async(
            [entry["body"] for entry in prepared], headers
        )
        if success and response is not None:
            returned: list[Any] = []
            if isinstance(response, dict):
                for key in ("items", "results", "memories", "entries"):
                    seq = response.get(key)
                    if isinstance(seq, list):
                        returned = seq
                        break
            elif isinstance(response, list):
                returned = response
            for idx, entry in enumerate(returned[: len(prepared)]):
                server_coord = _extract_memory_coord(
                    entry, idempotency_key=f"{rid}:{idx}"
                )
                if server_coord:
                    coords[idx] = server_coord
                    try:
                        prepared[idx]["body"]["payload"]["coordinate"] = server_coord
                    except Exception:
                        pass
            return coords

        if status in (404, 405):
            for idx, entry in enumerate(prepared):
                single_headers = dict(headers)
                single_headers["X-Request-ID"] = f"{rid}:{idx}"
                ok, resp = await self._store_http_async(entry["body"], single_headers)
                if ok and resp is not None:
                    server_coord = _extract_memory_coord(
                        resp, idempotency_key=single_headers["X-Request-ID"]
                    )
                    if server_coord:
                        coords[idx] = server_coord
            return coords

        raise RuntimeError("Memory service unavailable (async bulk remember failed)")

    def _remember_sync_persist(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> tuple[float, float, float] | None:
        if self._http is None:
            raise RuntimeError("HTTP memory service required for persistence")

        enriched, uni, compat_hdr = _compat_enrich_payload(self.cfg, payload, coord_key)
        sc = _resolve_coord(coord_key, payload, uni)
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        # ARCHITECTURE-INVARIANTS §5: embedding and tenant_id are FIRST-CLASS
        # top-level fields on MemoryStoreRequest — never only inside payload.
        body: dict[str, Any] = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }
        body.update(_seam_store_fields(self.cfg, enriched, payload))

        rid = request_id or str(uuid.uuid4())
        rid_hdr = {"X-Request-ID": rid}
        rid_hdr.update(compat_hdr)
        stored = False
        response_payload: Any = None
        if self._http is not None:
            try:
                stored, response_payload = self._store_http_sync(body, rid_hdr)
            except Exception:
                stored = False
        server_coord: tuple[float, float, float] | None = None
        if stored and response_payload is not None:
            try:
                server_coord = _extract_memory_coord(
                    response_payload, idempotency_key=rid
                )
            except Exception:
                server_coord = None

        if not stored:
            raise RuntimeError("Memory service unavailable (remember persist failed)")
        return server_coord

    async def _aremember_background(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> None:
        if self._http_async is None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._remember_sync_persist, coord_key, payload, request_id
            )
            return

        rid = request_id
        rid_hdr = {"X-Request-ID": rid} if rid else {}
        enriched, uni, compat_hdr = _compat_enrich_payload(self.cfg, payload, coord_key)
        rid_hdr.update(compat_hdr)
        sc = _resolve_coord(coord_key, payload, uni)
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        body: dict[str, Any] = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }
        # First-class seam fields — the background path must not strip them.
        body.update(_seam_store_fields(self.cfg, enriched, payload))

        try:
            await self._store_http_async(body, rid_hdr)
        except Exception as exc:
            logger.warning("LTM background persist failed key=%s: %s", coord_key, exc)
            raise

    def store_from_payload(self, payload: dict, request_id: str | None = None) -> bool:
        """Compatibility helper: store a payload dict into the memory backend."""
        try:
            coord = payload.get("coordinate")
            if coord is not None:
                try:
                    c = (
                        float(coord[0]),
                        float(coord[1]),
                        float(coord[2]),
                    )
                except Exception:
                    return False
                rid = request_id or str(uuid.uuid4())
                headers = {"X-Request-ID": rid}
                body = {
                    "coord": f"{c[0]},{c[1]},{c[2]}",
                    "payload": dict(payload),
                    "memory_type": str(
                        payload.get("memory_type") or payload.get("type") or "episodic"
                    ),
                }
                # First-class seam fields — this path must not strip them either.
                body.update(_seam_store_fields(self.cfg, payload, payload))
                success, _ = self._store_http_sync(body, headers)
                if success:
                    return True
                return False

            key = (
                payload.get("task")
                or payload.get("headline")
                or payload.get("id")
                or f"autokey:{uuid.uuid4()}"
            )
            self.remember(str(key), payload, request_id=request_id)
            return True
        except Exception:
            return False
