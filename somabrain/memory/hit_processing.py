"""Hit processing utilities for memory recall operations.

This module contains functions for processing, deduplicating, and ranking
recall hits from the memory service.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, List

from somabrain.memory.types import RecallHit
from somabrain.memory.normalization import _extract_memory_coord


def normalize_recall_hits(data: Any) -> List[RecallHit]:
    """Normalize raw recall response data into RecallHit objects."""
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
                        if k not in ("score", "coord", "coordinate", "distance", "vector")
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
                hits.append(RecallHit(payload=payload, score=score, coordinate=coord, raw=item))
            return hits
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            coord = _extract_memory_coord(item)
            if coord and "coordinate" not in payload:
                payload["coordinate"] = coord
            hits.append(RecallHit(payload=payload, score=None, coordinate=coord, raw=item))
    return hits


def hit_identity(hit: RecallHit) -> str:
    """Generate a unique identity string for a hit for deduplication."""
    coord = hit.coordinate
    if coord is None:
        coord = _extract_memory_coord(hit.payload) or _extract_memory_coord(hit.raw)
    if coord:
        try:
            return "coord:{:.6f},{:.6f},{:.6f}".format(coord[0], coord[1], coord[2])
        except Exception:
            pass
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    if isinstance(payload, dict):
        for key in ("id", "memory_id", "key", "coord_key"):
            identifier = payload.get(key)
            if identifier:
                return f"id:{identifier}"
        for field in ("task", "text", "content", "what", "fact", "headline"):
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                return f"text:{value.strip().lower()}"
    try:
        raw = hit.raw or hit.payload
        serial = json.dumps(raw, sort_keys=True, default=str)
        digest = hashlib.blake2s(serial.encode("utf-8"), digest_size=16).hexdigest()
        return f"hash:{digest}"
    except Exception:
        return f"obj:{id(hit)}"


def hit_score(hit: RecallHit) -> float | None:
    """Extract the score from a hit."""
    score = hit.score
    if isinstance(score, (int, float)) and not math.isnan(score):
        return float(score)
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    if isinstance(payload, dict):
        alt = payload.get("_score")
        if isinstance(alt, (int, float)) and not math.isnan(alt):
            return float(alt)
    return None


def coerce_timestamp_value(value: Any) -> float | None:
    """Coerce a value to a timestamp float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)):
                return None
        except Exception:
            return None
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                dt = datetime.fromisoformat(text[:-1] + "+00:00")
            else:
                dt = datetime.fromisoformat(text)
            return dt.timestamp()
        except Exception:
            try:
                return float(text)
            except Exception:
                return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return None


def hit_timestamp(hit: RecallHit) -> float | None:
    """Extract the timestamp from a hit."""
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    candidate_keys = ("timestamp", "created_at", "updated_at", "ts", "time")
    if isinstance(payload, dict):
        for key in candidate_keys:
            value = payload.get(key)
            ts = coerce_timestamp_value(value)
            if ts is not None:
                return ts
    raw = hit.raw
    if isinstance(raw, dict):
        meta = raw.get("metadata")
        if isinstance(meta, dict):
            for key in candidate_keys:
                ts = coerce_timestamp_value(meta.get(key))
                if ts is not None:
                    return ts
    return None


def prefer_candidate_hit(current: RecallHit, candidate: RecallHit) -> bool:
    """Determine if candidate hit should replace current hit."""
    curr_score = hit_score(current)
    cand_score = hit_score(candidate)
    if cand_score is not None or curr_score is not None:
        curr_metric = curr_score if curr_score is not None else float("-inf")
        cand_metric = cand_score if cand_score is not None else float("-inf")
        if cand_metric > curr_metric + 1e-9:
            return True
        if cand_metric < curr_metric - 1e-9:
            return False
    curr_ts = hit_timestamp(current)
    cand_ts = hit_timestamp(candidate)
    if cand_ts is not None and curr_ts is not None:
        if cand_ts > curr_ts + 1e-6:
            return True
        if cand_ts < curr_ts - 1e-6:
            return False
    elif cand_ts is not None:
        return True
    return False


def deduplicate_hits(hits: List[RecallHit]) -> List[RecallHit]:
    """Deduplicate hits by identity, keeping the best version of each."""
    winners: dict[str, RecallHit] = {}
    order: List[str] = []
    for hit in hits:
        ident = hit_identity(hit)
        existing = winners.get(ident)
        if existing is None:
            winners[ident] = hit
            order.append(ident)
            continue
        if prefer_candidate_hit(existing, hit):
            winners[ident] = hit
    return [winners[idx] for idx in order]


def lexical_bonus(payload: dict, query: str) -> float:
    """Calculate lexical bonus for a payload based on query match."""
    q = str(query or "").strip()
    if not q or not isinstance(payload, dict):
        return 0.0
    ql = q.lower()
    bonus = 0.0
    fields = ("task", "text", "content", "what", "fact", "headline", "summary")
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value:
            vl = value.lower()
            if vl == ql:
                bonus = max(bonus, 1.5)
            elif ql in vl:
                bonus = max(bonus, 1.0)
    token_matches = 0
    for token in re.split(r"[\s,;:/-]+", q):
        token = token.strip().lower()
        if len(token) < 3:
            continue
        for field in fields:
            value = payload.get(field)
            if isinstance(value, str) and token in value.lower():
                token_matches += 1
                break
    if token_matches > 0:
        bonus = max(bonus, 0.3 + 0.1 * min(token_matches, 5))
    return bonus
