from __future__ import annotations
import math
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, List, Iterable
from .types import RecallHit
from .serialization import _extract_memory_coord

def _hit_identity(hit: RecallHit) -> str:
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

def _hit_score(hit: RecallHit) -> float | None:
    score = hit.score
    if isinstance(score, (int, float)) and not math.isnan(score):
        return float(score)
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    if isinstance(payload, dict):
        alt = payload.get("_score")
        if isinstance(alt, (int, float)) and not math.isnan(alt):
            return float(alt)
    return None

def _coerce_timestamp_value(value: Any) -> float | None:
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
            # ISO8601 handling; account for trailing Z
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

def _hit_timestamp(hit: RecallHit) -> float | None:
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    candidate_keys = (
        "timestamp",
        "created_at",
        "updated_at",
        "ts",
        "time",
    )
    if isinstance(payload, dict):
        for key in candidate_keys:
            value = payload.get(key)
            ts = _coerce_timestamp_value(value)
            if ts is not None:
                return ts
    raw = hit.raw
    if isinstance(raw, dict):
        meta = raw.get("metadata")
        if isinstance(meta, dict):
            for key in candidate_keys:
                ts = _coerce_timestamp_value(meta.get(key))
                if ts is not None:
                    return ts
    return None

def _prefer_candidate_hit(current: RecallHit, candidate: RecallHit) -> bool:
    curr_score = _hit_score(current)
    cand_score = _hit_score(candidate)
    if cand_score is not None or curr_score is not None:
        curr_metric = curr_score if curr_score is not None else float("-inf")
        cand_metric = cand_score if cand_score is not None else float("-inf")
        if cand_metric > curr_metric + 1e-9:
            return True
        if cand_metric < curr_metric - 1e-9:
            return False
    curr_ts = _hit_timestamp(current)
    cand_ts = _hit_timestamp(candidate)
    if cand_ts is not None and curr_ts is not None:
        if cand_ts > curr_ts + 1e-6:
            return True
        if cand_ts < curr_ts - 1e-6:
            return False
    elif cand_ts is not None:
        return True
    return False

def _deduplicate_hits(hits: List[RecallHit]) -> List[RecallHit]:
    winners: dict[str, RecallHit] = {}
    order: List[str] = []
    for hit in hits:
        ident = _hit_identity(hit)
        existing = winners.get(ident)
        if existing is None:
            winners[ident] = hit
            order.append(ident)
            continue
        if _prefer_candidate_hit(existing, hit):
            winners[ident] = hit
    return [winners[idx] for idx in order]

def _lexical_bonus(payload: dict, query: str) -> float:
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
    if token_matches:
        bonus += min(0.25 * token_matches, 1.0)
    return bonus

def _rank_hits(hits: List[RecallHit], query: str) -> List[RecallHit]:
    ranked: List[tuple[float, float, float, int, RecallHit]] = []
    for idx, hit in enumerate(hits):
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        lex_bonus = _lexical_bonus(payload, query)
        base = 0.0
        if hit.score is not None:
            try:
                base = float(hit.score)
                if abs(base) > 1.0:
                    base = math.copysign(math.log1p(abs(base)), base)
            except Exception:
                base = 0.0
        weight = 1.0
        if isinstance(payload, dict):
            try:
                wf = payload.get("_weight_factor")
                if isinstance(wf, (int, float)):
                    weight = float(wf)
            except Exception:
                weight = 1.0
        final_score = (base * weight) + lex_bonus
        if hit.score is None and lex_bonus > 0:
            try:
                hit.score = lex_bonus
                payload.setdefault("_score", hit.score)
            except Exception:
                pass
        ranked.append((final_score, lex_bonus, weight, -idx, hit))
    ranked.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
    return [item[-1] for item in ranked]

def _filter_payloads_by_keyword(payloads: Iterable[Any], keyword: str) -> List[dict]:
    items: List[dict] = [p for p in payloads if isinstance(p, dict)]
    key = str(keyword or "").strip().lower()
    if not key:
        return items

    filtered: List[dict] = []
    fields = ("what", "headline", "text", "content", "who", "task", "session")
    for entry in items:
        for field in fields:
            value = entry.get(field)
            if isinstance(value, str) and key in value.lower():
                filtered.append(entry)
                break
    return filtered or items

def _filter_hits_by_keyword(hits: List[RecallHit], keyword: str) -> List[RecallHit]:
    if not hits:
        return []
    payloads = [h.payload for h in hits if isinstance(h.payload, dict)]
    filtered = _filter_payloads_by_keyword(payloads, keyword)
    if filtered and len(filtered) <= len(payloads):
        allowed_ids = {id(p) for p in filtered}
        narrowed = [h for h in hits if id(h.payload) in allowed_ids]
        if narrowed:
            return narrowed
    return hits

def _recency_normalisation(cfg: Any) -> tuple[float, float]:
    scale = getattr(cfg, "recall_recency_time_scale", 60.0)
    if (
        not isinstance(scale, (int, float))
        or not math.isfinite(scale)
        or scale <= 0
    ):
        scale = 60.0
    cap = getattr(cfg, "recall_recency_max_steps", 4096.0)
    if not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
        cap = 4096.0
    return float(scale), float(cap)

def _recency_profile(cfg: Any) -> tuple[float, float, float, float]:
    scale, cap = _recency_normalisation(cfg)
    sharpness = getattr(cfg, "recall_recency_sharpness", 1.2)
    try:
        sharpness = float(sharpness)
    except Exception:
        sharpness = 1.2
    if not math.isfinite(sharpness) or sharpness <= 0:
        sharpness = 1.0
    floor = getattr(cfg, "recall_recency_floor", 0.05)
    try:
        floor = float(floor)
    except Exception:
        floor = 0.05
    if not math.isfinite(floor) or floor < 0:
        floor = 0.0
    if floor >= 1.0:
        floor = 0.99
    return scale, cap, sharpness, floor

def _recency_features(
    cfg: Any, ts_epoch: float | None, now_ts: float
) -> tuple[float | None, float]:
    if ts_epoch is None:
        return None, 1.0
    scale, cap, sharpness, floor = _recency_profile(cfg)
    age_seconds = max(0.0, now_ts - ts_epoch)
    if age_seconds <= 0:
        return 0.0, 1.0
    normalised = age_seconds / max(scale, 1e-6)
    damp_steps = math.log1p(normalised) * sharpness
    recency_steps = min(damp_steps, cap)
    try:
        damp = math.exp(-(normalised**sharpness))
    except Exception:
        damp = 0.0
    boost = max(floor, min(1.0, damp))
    return recency_steps, boost

def _extract_cleanup_margin(hit: RecallHit) -> float | None:
    payload = hit.payload if isinstance(hit.payload, dict) else {}
    margin = None
    if isinstance(payload, dict):
        margin = payload.get("_cleanup_margin")
        if margin is None:
            margin = payload.get("cleanup_margin")
    if margin is None and isinstance(hit.raw, dict):
        metadata = hit.raw.get("metadata")
        if isinstance(metadata, dict):
            margin = metadata.get("cleanup_margin")

    if margin is None:
        return None
    try:
        numeric = float(margin)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric

def _density_factor(cfg: Any, margin: float | None) -> float:
    if margin is None:
        return 1.0
    target = getattr(cfg, "recall_density_margin_target", 0.2)
    floor = getattr(cfg, "recall_density_margin_floor", 0.6)
    weight = getattr(cfg, "recall_density_margin_weight", 0.35)
    try:
        target = float(target)
    except Exception:
        target = 0.2
    if not math.isfinite(target) or target <= 0:
        target = 0.2
    try:
        floor = float(floor)
    except Exception:
        floor = 0.6
    if not math.isfinite(floor) or floor < 0:
        floor = 0.0
    if floor > 1.0:
        floor = 1.0
    try:
        weight = float(weight)
    except Exception:
        weight = 0.35
    if not math.isfinite(weight) or weight < 0:
        weight = 0.0
    if margin >= target:
        return 1.0
    deficit = (target - margin) / target
    penalty = 1.0 - (weight * deficit)
    return max(floor, min(1.0, penalty))

def _parse_payload_timestamp(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        if isinstance(raw, (int, float)):
            value = float(raw)
        elif isinstance(raw, str):
            txt = raw.strip()
            if not txt:
                return None
            try:
                value = float(txt)
            except ValueError:
                try:
                    txt_norm = (
                        txt.replace("Z", "+00:00") if txt.endswith("Z") else txt
                    )
                    dt = datetime.fromisoformat(txt_norm)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    return float(dt.timestamp())
                except Exception:
                    return None
        else:
            return None
    except Exception:
        return None
    if not math.isfinite(value):
        return None
    # Accept millisecond epoch values transparently
    if value > 1e12:
        value /= 1000.0
    return value

def _rescore_and_rank_hits(
    cfg: Any, scorer: Any, embedder: Any, hits: List[RecallHit], query: str
) -> List[RecallHit]:
    if not scorer or not embedder:
        _apply_weighting_to_hits(cfg, hits)
        return _rank_hits(hits, query)

    query_vec = embedder.embed(query)
    now_ts = datetime.now(timezone.utc).timestamp()

    def _text_of(p: dict) -> str:
        return str(p.get("task") or p.get("fact") or p.get("content") or "").strip()

    scored_hits = []
    for hit in hits:
        payload = hit.payload or {}
        text = _text_of(payload)
        if not text:
            new_score = 0.0
        else:
            candidate_vec = embedder.embed(text)
            recency_steps: float | None = None
            recency_boost = 1.0
            ts_epoch = None
            for key in ("timestamp", "ts", "created_at"):
                if key in payload:
                    ts_epoch = _parse_payload_timestamp(payload.get(key))
                    if ts_epoch is not None:
                        break
            if ts_epoch is not None:
                recency_steps, recency_boost = _recency_features(
                    cfg, ts_epoch, now_ts
                )

            new_score = scorer.score(
                query_vec,
                candidate_vec,
                recency_steps=recency_steps,
                cosine=hit.score,  # Pass original score as cosine hint
            )
            new_score *= recency_boost
            try:
                payload.setdefault("_recency_steps", recency_steps)
                payload.setdefault("_recency_boost", recency_boost)
            except Exception:
                pass

        margin = _extract_cleanup_margin(hit)
        density_factor = _density_factor(cfg, margin)
        new_score *= density_factor
        if density_factor != 1.0:
            try:
                payload.setdefault("_density_factor", density_factor)
            except Exception:
                pass
        new_score = max(0.0, min(1.0, float(new_score)))

        hit.score = new_score
        scored_hits.append(hit)

    scored_hits.sort(key=lambda h: h.score or 0.0, reverse=True)
    return scored_hits

def _apply_weighting_to_hits(cfg: Any, hits: List[RecallHit]) -> None:
    if not hits:
        return
    weighting_enabled = False
    priors_env = ""
    quality_exp = 1.0

    # Logic to fetch settings... defaulting to passed config or system settings
    # For now assume cfg is the settings object or similar
    try:
        weighting_enabled = bool(getattr(cfg, "memory_enable_weighting", False))
        priors_env = getattr(cfg, "memory_phase_priors", "") or ""
        quality_exp = float(getattr(cfg, "memory_quality_exp", 1.0) or 1.0)
    except Exception:
        pass

    if not weighting_enabled:
        return

    try:
        priors: dict[str, float] = {}
        if priors_env:
            for part in priors_env.split(","):
                if not part.strip() or ":" not in part:
                    continue
                k, v = part.split(":", 1)
                try:
                    priors[k.strip().lower()] = float(v)
                except Exception:
                    pass
        for hit in hits:
            payload = hit.payload
            phase_factor = 1.0
            quality_factor = 1.0
            try:
                phase = payload.get("phase") if isinstance(payload, dict) else None
                if phase and priors:
                    phase_factor = float(priors.get(str(phase).lower(), 1.0))
            except Exception:
                phase_factor = 1.0
            try:
                if isinstance(payload, dict) and "quality_score" in payload:
                    qs = float(payload.get("quality_score") or 0.0)
                    if qs < 0:
                        qs = 0.0
                    if qs > 1:
                        qs = 1.0
                    quality_factor = (qs**quality_exp) if qs > 0 else 0.0
            except Exception:
                quality_factor = 1.0
            try:
                payload.setdefault("_weight_factor", phase_factor * quality_factor)
            except Exception:
                pass
    except Exception:
        return
