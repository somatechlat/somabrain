from __future__ import annotations
import uuid
import asyncio
import time
import logging
from typing import Any, Tuple, Iterable, List
from django.conf import settings
from .serialization import _compat_enrich_payload, _stable_coord, _extract_memory_coord

logger = logging.getLogger(__name__)

class WriteMixin:
    """Handles memory persistence operations."""

    def remember(
        self, coord_key: str, payload: dict, request_id: str | None = None
    ) -> Tuple[float, float, float]:
        """Store a memory using a stable coordinate derived from coord_key."""
        enriched, universe, _hdr = _compat_enrich_payload(self.cfg, payload, coord_key)
        coord = _stable_coord(f"{universe}::{coord_key}")

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
                    parts = [p.strip().lower() for p in dval.replace(",", " ").split() if p.strip()]
                    payload["domains"] = parts or []
                elif isinstance(dval, (list, tuple)):
                    cleaned = []
                    for x in dval:
                        if isinstance(x, str) and x.strip():
                            cleaned.append(x.strip().lower())
                    payload["domains"] = cleaned
                else:
                    payload.pop("domains", None)
            if "reasoning_chain" in payload and isinstance(payload["reasoning_chain"], str):
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
    ) -> List[Tuple[float, float, float]]:
        records = list(items)
        if not records:
            return []

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for coord_key, payload in records:
            enriched, universe, _ = _compat_enrich_payload(self.cfg, payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
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
            returned: List[Any] = []
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
    ) -> Tuple[float, float, float]:
        p2: dict[str, Any] | None = None
        if self._http_async is not None:
            try:
                enriched, universe, compat_hdr = _compat_enrich_payload(
                    self.cfg, payload, coord_key
                )
                coord = _stable_coord(f"{universe}::{coord_key}")
                enriched = dict(enriched)
                enriched.setdefault("coordinate", coord)
                memory_type = str(
                    enriched.get("memory_type") or enriched.get("type") or "episodic"
                )
                body = {
                    "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                    "payload": enriched,
                    "memory_type": memory_type,
                    "type": memory_type,
                }

                rid = request_id or str(uuid.uuid4())
                rid_hdr = {"X-Request-ID": rid}
                rid_hdr.update(compat_hdr)
                ok, response_data = await self._store_http_async(body, rid_hdr)
                if ok and response_data is not None:
                    server_coord = _extract_memory_coord(
                        response_data, idempotency_key=rid
                    )
                    if server_coord:
                        try:
                            enriched["coordinate"] = server_coord
                        except Exception:
                            pass
                        if p2 is not None:
                            try:
                                p2["coordinate"] = server_coord
                            except Exception:
                                pass
                        # prefer server coords for links logic omitted for brevity/compatibility
                        return server_coord
                return coord
            except Exception:
                pass
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remember, coord_key, payload)

    async def aremember_bulk(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        request_id: str | None = None,
    ) -> List[Tuple[float, float, float]]:
        records = list(items)
        if not records:
            return []

        if self._http_async is None:
            return self.remember_bulk(records, request_id=request_id)

        prepared: List[dict[str, Any]] = []
        universes: List[str] = []
        coords: List[Tuple[float, float, float]] = []

        for coord_key, payload in records:
            enriched, universe, _ = _compat_enrich_payload(self.cfg, payload, coord_key)
            coord = _stable_coord(f"{universe}::{coord_key}")
            enriched_payload = dict(enriched)
            enriched_payload.setdefault("coordinate", coord)
            enriched_payload.setdefault("memory_type", "episodic")
            body = {
                "coord": f"{coord[0]},{coord[1]},{coord[2]}",
                "payload": enriched_payload,
                "type": enriched_payload.get("memory_type", "episodic"),
            }
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
            returned: List[Any] = []
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
    ) -> Tuple[float, float, float] | None:
        if self._http is None:
            raise RuntimeError("HTTP memory service required for persistence")

        enriched, uni, compat_hdr = _compat_enrich_payload(self.cfg, payload, coord_key)
        sc = _stable_coord(f"{uni}::{coord_key}")
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        body = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }

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
        server_coord: Tuple[float, float, float] | None = None
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
        sc = _stable_coord(f"{uni}::{coord_key}")
        coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
        memory_type = str(
            enriched.get("memory_type") or enriched.get("type") or "episodic"
        )
        body = {
            "coord": coord_str,
            "payload": enriched,
            "memory_type": memory_type,
            "type": memory_type,
        }

        try:
            await self._store_http_async(body, rid_hdr)
        except Exception:
            pass

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
