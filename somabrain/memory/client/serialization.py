from __future__ import annotations
import hashlib
from typing import Any, Tuple, Optional, List
from .types import RecallHit

def _stable_coord(key: str) -> Tuple[float, float, float]:
    """Derive a deterministic 3D coordinate in [-1,1]^3 from a string key."""
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=12).digest()
    a = int.from_bytes(h[0:4], "big") / 2**32
    b = int.from_bytes(h[4:8], "big") / 2**32
    c = int.from_bytes(h[8:12], "big") / 2**32
    # spread over [-1, 1]
    return (2 * a - 1, 2 * b - 1, 2 * c - 1)

def _parse_coord_string(s: str) -> Tuple[float, float, float] | None:
    try:
        parts = [float(x.strip()) for x in str(s).split(",")]
        if len(parts) >= 3:
            return (parts[0], parts[1], parts[2])
    except Exception:
        return None
    return None

def _extract_memory_coord(
    resp: Any,
    idempotency_key: str | None = None,
) -> Tuple[float, float, float] | None:
    """Try to derive a coordinate tuple from the memory-service response."""

    if not resp:
        return None

    data = resp
    json_attr = getattr(resp, "json", None)
    if callable(json_attr):
        try:
            data = json_attr()
        except (ValueError, TypeError):
            data = resp

    data_dict = data if isinstance(data, dict) else None

    if data_dict is not None:
        for key in ("coord", "coordinate"):
            value = data_dict.get(key)
            parsed: Optional[Tuple[float, float, float]] = None
            if isinstance(value, str):
                parsed = _parse_coord_string(value)
            elif isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    parsed = (float(value[0]), float(value[1]), float(value[2]))
                except (TypeError, ValueError):
                    parsed = None
            if parsed:
                return parsed

        mem_section = data_dict.get("memory")
        if isinstance(mem_section, dict):
            for key in ("coordinate", "coord", "location"):
                value = mem_section.get(key)
                parsed = None
                if isinstance(value, str):
                    parsed = _parse_coord_string(value)
                elif isinstance(value, (list, tuple)) and len(value) >= 3:
                    try:
                        parsed = (float(value[0]), float(value[1]), float(value[2]))
                    except (TypeError, ValueError):
                        parsed = None
                if parsed:
                    return parsed

            mid = mem_section.get("id") or mem_section.get("memory_id")
            if mid is not None:
                try:
                    return _stable_coord(str(mid))
                except (TypeError, ValueError):
                    pass

        mid = data_dict.get("id") or data_dict.get("memory_id")
        if mid is not None:
            try:
                return _stable_coord(str(mid))
            except (TypeError, ValueError):
                pass

    if idempotency_key:
        try:
            return _stable_coord(f"idempotency:{idempotency_key}")
        except (TypeError, ValueError):
            return None
    return None

def _normalize_recall_hits(data: Any) -> List[RecallHit]:
    hits: List[RecallHit] = []
    if isinstance(data, dict):
        items = None
        for key in ("matches", "results", "items", "memories", "entries", "hits"):
            seq = data.get(key)
            if isinstance(seq, list):
                items = seq
                break
        if items is None and isinstance(data.get("data"), list):
            items = data.get("data")
        if items is not None:
            for item in items:
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload")
                if not isinstance(payload, dict):
                    mem = item.get("memory")
                    if isinstance(mem, dict):
                        payload = mem.get("payload") or mem
                if not isinstance(payload, dict):
                    payload = {
                        k: v
                        for k, v in item.items()
                        if k
                        not in (
                            "score",
                            "coord",
                            "coordinate",
                            "distance",
                            "vector",
                        )
                    }
                payload = dict(payload or {})
                score = None
                try:
                    score_val = item.get("score")
                    if score_val is None:
                        score_val = item.get("similarity")
                    if score_val is None and isinstance(item.get("metadata"), dict):
                        score_val = item["metadata"].get("score")
                    if score_val is not None:
                        score = float(score_val)
                        payload.setdefault("_score", score)
                except Exception:
                    score = None
                coord = _extract_memory_coord(item)
                if coord and "coordinate" not in payload:
                    payload["coordinate"] = coord
                hits.append(
                    RecallHit(
                        payload=payload,
                        score=score,
                        coordinate=coord,
                        raw=item,
                    )
                )
            return hits
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            coord = _extract_memory_coord(item)
            if coord and "coordinate" not in payload:
                payload["coordinate"] = coord
            hits.append(
                RecallHit(
                    payload=payload,
                    score=None,
                    coordinate=coord,
                    raw=item,
                )
            )
    return hits

def _compat_enrich_payload(
    cfg: Any, payload: dict, coord_key: str
) -> Tuple[dict, str, dict]:
    """Return an enriched (payload_copy, universe, extra_headers)."""
    p = dict(payload or {})
    # Universe scoping
    universe = str(p.get("universe") or "real")
    # Choose canonical text for indexing
    text = None
    for k in ("task", "text", "content", "what", "fact", "headline", "description"):
        v = p.get(k)
        if isinstance(v, str) and v.strip():
            text = v.strip()
            break
    if not text:
        text = str(coord_key)
    p.setdefault("text", text)
    p.setdefault("content", text)
    p.setdefault("id", p.get("memory_id") or p.get("key") or coord_key)
    import time
    p.setdefault("timestamp", time.time())
    p.setdefault("universe", universe)
    try:
        ns = getattr(cfg, "namespace", None)
        if ns and not p.get("namespace"):
            p["namespace"] = ns
    except Exception:
        pass
    headers = {"X-Universe": universe}
    return p, universe, headers

def _response_json(resp: Any) -> Any:
    """Helper to safely extract JSON from response obj."""
    try:
        if hasattr(resp, "json") and callable(resp.json):
            return resp.json()
    except Exception:
        pass
    return None

def _parse_coord_string(coord_str: str) -> Tuple[float, float, float] | None:
    """Parse 'x,y,z' string into tuple."""
    if not coord_str or not isinstance(coord_str, str):
        return None
    parts = coord_str.split(",")
    if len(parts) >= 3:
        try:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError:
            pass
    return None
