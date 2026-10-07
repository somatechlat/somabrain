from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from typing import Any

import numpy as np

from somabrain.math.contracts import (
    RECENCY_CAP,
    RECENCY_FLOOR,
    RECENCY_SCALE,
    RECENCY_SHARPNESS,
)
from somabrain.math.recency import recency_features as _shared_recency_features

from .serialization import _extract_memory_coord
from .types import RecallHit


def _hit_identity(hit: RecallHit) -> str:
    coord = hit.coordinate
    if coord is None:
        coord = _extract_memory_coord(hit.payload) or _extract_memory_coord(hit.raw)
    if coord:
        try:
            return f"coord:{coord[0]:.6f},{coord[1]:.6f},{coord[2]:.6f}"
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
            value = value.replace(tzinfo=UTC)
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


def _deduplicate_hits(hits: list[RecallHit]) -> list[RecallHit]:
    winners: dict[str, RecallHit] = {}
    order: list[str] = []
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


def lexical_bonus(payload: dict, query: str) -> float:
    """Lexical bonus for a payload against a query.

    Exact field match → 1.5, query substring of a field → 1.0, plus a token
    overlap term ``min(0.25 * token_matches, 1.0)``.
    """
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


def _recency_normalisation(cfg: Any) -> tuple[float, float]:
    scale = getattr(cfg, "SOMABRAIN_WM_RECENCY_TIME_SCALE", RECENCY_SCALE)
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        scale = RECENCY_SCALE
    cap = getattr(cfg, "SOMABRAIN_WM_RECENCY_MAX_STEPS", RECENCY_CAP)
    if not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
        cap = RECENCY_CAP
    return float(scale), float(cap)


def _recency_profile(cfg: Any) -> tuple[float, float, float, float]:
    scale, cap = _recency_normalisation(cfg)
    sharpness = getattr(cfg, "SOMABRAIN_RECENCY_SHARPNESS", RECENCY_SHARPNESS)
    try:
        sharpness = float(sharpness)
    except Exception:
        sharpness = RECENCY_SHARPNESS
    if not math.isfinite(sharpness) or sharpness <= 0:
        sharpness = 1.0
    floor = getattr(cfg, "SOMABRAIN_RECENCY_FLOOR", RECENCY_FLOOR)
    try:
        floor = float(floor)
    except Exception:
        floor = RECENCY_FLOOR
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
    return _shared_recency_features(
        age_seconds,
        scale=scale,
        sharpness=sharpness,
        floor=floor,
        cap=cap,
    )


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
    target = getattr(cfg, "SOMABRAIN_DENSITY_TARGET", 0.2)
    floor = getattr(cfg, "SOMABRAIN_DENSITY_FLOOR", 0.6)
    weight = getattr(cfg, "SOMABRAIN_DENSITY_WEIGHT", 0.35)
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
    floor = min(floor, 1.0)
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
                    txt_norm = txt.replace("Z", "+00:00") if txt.endswith("Z") else txt
                    dt = datetime.fromisoformat(txt_norm)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    else:
                        dt = dt.astimezone(UTC)
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


def _resolve_semantic_scorer(
    cfg: Any, scorer: Any, embedder: Any, *, require_embedder: bool = True
) -> tuple[Any, Any]:
    """Return (scorer, embedder) from runtime when not injected.

    Semantic ranking is mandatory — never fall back to lexical/keyword ranking.
    When ``require_embedder`` is False the caller already holds a precomputed
    query vector (INVARIANTS §2.1) so the embedder is optional.
    """
    if scorer is not None and (embedder is not None or not require_embedder):
        return scorer, embedder
    try:
        from somabrain.runtime.manager import get_embedder

        embedder = embedder or get_embedder()
    except Exception:
        embedder = embedder or None
    if scorer is None:
        try:
            from somabrain.bootstrap.singletons import make_unified_scorer

            scorer = make_unified_scorer(cfg)
        except Exception:
            scorer = None
    if scorer is None or (require_embedder and embedder is None):
        raise RuntimeError(
            "SomaBrain semantic scorer/embedder required for recall ranking"
        )
    return scorer, embedder


def _extract_stored_vector(hit: RecallHit) -> np.ndarray | None:
    """Return the vector stored with *hit*, or ``None``.

    Searches the normalized payload and the raw store row. Never synthesises a
    vector: a miss stays a miss so callers can fail closed instead of silently
    hash-embedding text into a foreign space (INVARIANTS §2.1).
    """
    sources: list[Any] = [hit.payload]
    raw = hit.raw
    if isinstance(raw, dict):
        sources.append(raw)
        mem = raw.get("memory")
        if isinstance(mem, dict):
            sources.append(mem)
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("embedding", "vector", "_embedding", "dense_vector"):
            value = source.get(key)
            if value is None:
                continue
            try:
                arr = np.asarray(value, dtype=np.float32).reshape(-1)
            except Exception:
                continue
            if arr.size > 0 and bool(np.all(np.isfinite(arr))):
                return arr
    return None


# Placeholder vectors for the scorer signature when only the store cosine
# exists. Their contents are irrelevant: the cosine term is supplied as a hint
# and the FD backend is not in play. They are NEVER embedded from text — a
# foreign embedder has no place on this path (INVARIANTS §2.1).
_NO_VECTOR = np.zeros(0, dtype=np.float32)


def _rescore_and_rank_hits(
    cfg: Any,
    scorer: Any,
    embedder: Any,
    hits: list[RecallHit],
    query: str,
    query_vec: list[float] | np.ndarray | None = None,
) -> list[RecallHit]:
    """Rescore hits in ONE embedding space. Never re-embeds hit text.

    INVARIANTS §2.1: when ``query_vec`` is present it is the authoritative
    query vector. This function never calls ``embedder.embed`` — a third or
    fourth embedder (TinyDeterministicEmbedder) is not comparable to the
    store's vectors and mixing it into the answer is exactly the defect.

    Per-hit rules, in order:

    1. ``query_vec`` + stored vector → scorer on those two vectors (same space).
       Recency is applied once inside ``scorer.score(age_seconds=...)``, and the
       FD term is computed from those same two vectors — never from text.
    2. store cosine only (``hit.score``) → that cosine is the semantic term.
       The scorer is still invoked so recency (``w_recency``) is applied once;
       it is given empty vectors and the cosine as a hint, so nothing is ever
       embedded and the FD term is zero rather than a fake self-similarity.
    3. neither → fail closed. With a precomputed query vector this raises:
       the hit cannot be scored in that space and inventing 0.0 would be a
       fabricated judgment the ranker sorts on. Text-only callers get the hit
       left unscored (``None``). Text is never hash-embedded into a foreign
       vector space.
    """
    query_arr: np.ndarray | None = None
    if query_vec is not None:
        query_arr = np.asarray(query_vec, dtype=np.float32).reshape(-1)
        if query_arr.size == 0 or not bool(np.all(np.isfinite(query_arr))):
            raise ValueError("query_vec must be a non-empty finite vector")
        if scorer is None:
            scorer, _ = _resolve_semantic_scorer(
                cfg, scorer, embedder, require_embedder=False
            )
    else:
        # Text-only caller. Do NOT embed the query here — the only query
        # vector allowed on this path is the precomputed one. Recency (when
        # applied) goes through the scorer with a cosine hint, never a
        # foreign-space embedding.
        if scorer is not None:
            pass
        else:
            scorer, _ = _resolve_semantic_scorer(
                cfg, scorer, embedder, require_embedder=False
            )

    now_ts = datetime.now(UTC).timestamp()

    scored_hits = []
    for hit in hits:
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        stored_vec = _extract_stored_vector(hit)
        cosine_hint = _hit_score(hit)

        recency_steps: float | None = None
        recency_boost = 1.0
        age_seconds: float | None = None
        ts_epoch = None
        for key in ("timestamp", "ts", "created_at"):
            if key in payload:
                ts_epoch = _parse_payload_timestamp(payload.get(key))
                if ts_epoch is not None:
                    break
        if ts_epoch is not None:
            age_seconds = max(0.0, now_ts - ts_epoch)
            recency_steps, recency_boost = _recency_features(cfg, ts_epoch, now_ts)

        new_score: float | None
        if query_arr is not None and stored_vec is not None:
            if stored_vec.size != query_arr.size:
                raise RuntimeError(
                    "stored vector dim "
                    f"{stored_vec.size} != query vector dim {query_arr.size} — "
                    "refusing to score across embedding spaces (INVARIANTS §2.1)"
                )
            # Same space, both vectors present: let the scorer compute cosine.
            # The store hint is not passed — it would override the real cosine.
            # Recency is applied once, here inside scorer.score(age_seconds=...).
            new_score = scorer.score(
                query_arr,
                stored_vec,
                age_seconds=age_seconds,
                cosine=None,
            )
        elif cosine_hint is not None:
            # No stored vector: the store's similarity is the only vector-space
            # signal. Never embed text to invent a candidate. Recency (w_recency
            # inside UnifiedScorer) is still applied once, so the scorer is
            # given the cosine as a hint and empty vectors — it cannot embed.
            if scorer is None:
                raise RuntimeError(
                    "SomaBrain semantic scorer required for recall ranking"
                )
            new_score = scorer.score(
                _NO_VECTOR,
                _NO_VECTOR,
                age_seconds=age_seconds,
                cosine=cosine_hint,
            )
        else:
            # Neither stored vector nor store score. Never fake 0.0 — a correct
            # Milvus hit reported as score 0 is a lie the ranker sorts on.
            # With a precomputed query vector this is a failure (we were asked
            # to score and cannot). Text-only callers leave the hit unscored.
            if query_arr is not None:
                raise RuntimeError(
                    "recall hit has no stored vector and no store score — cannot "
                    "score with the precomputed query vector. Refusing to invent 0.0."
                )
            new_score = None

        try:
            payload.setdefault("_recency_steps", recency_steps)
            payload.setdefault("_recency_boost", recency_boost)
        except Exception:
            pass

        if new_score is not None:
            margin = _extract_cleanup_margin(hit)
            density_factor = _density_factor(cfg, margin)
            new_score *= density_factor
            if density_factor != 1.0:
                try:
                    payload.setdefault("_density_factor", density_factor)
                except Exception:
                    pass
            new_score = float(new_score)
            # NaN score is broken input — fail closed to 0.0, never 1.0.
            new_score = 0.0 if not math.isfinite(new_score) else max(0.0, min(1.0, new_score))
            hit.score = new_score
        scored_hits.append(hit)

    scored_hits.sort(key=lambda h: h.score if h.score is not None else float("-inf"), reverse=True)
    return scored_hits
