"""Scoring and recency utilities for SomaBrain Memory.

This module provides functions for scoring, ranking, and applying recency
adjustments to memory recall hits.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, List, Tuple

from django.conf import settings

from somabrain.memory.types import RecallHit
from somabrain.memory.hit_processing import lexical_bonus


def coerce_float(value: Any) -> float | None:
    """Coerce a value to float, returning None if invalid.

    Args:
        value: Any value to convert to float.

    Returns:
        The float value or None if conversion fails or value is not finite.
    """
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def parse_payload_timestamp(raw: Any) -> float | None:
    """Parse a timestamp from various formats.

    Handles:
    - Numeric epoch timestamps (seconds or milliseconds)
    - ISO 8601 datetime strings
    - String representations of numbers

    Args:
        raw: The raw timestamp value to parse.

    Returns:
        Unix timestamp as float, or None if parsing fails.
    """
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


def get_recency_normalisation(cfg: Any) -> Tuple[float, float]:
    """Get recency normalization parameters from config.

    Args:
        cfg: Configuration object with recall_recency_* attributes.

    Returns:
        Tuple of (time_scale, max_steps).
    """
    scale = getattr(cfg, "SOMABRAIN_RECENCY_HALF_LIFE", 60.0)
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        scale = 60.0
    cap = getattr(cfg, "SOMABRAIN_WM_RECENCY_MAX_STEPS", 1000.0)
    if not isinstance(cap, (int, float)) or not math.isfinite(cap) or cap <= 0:
        cap = 1000.0
    return float(scale), float(cap)


def get_recency_profile(cfg: Any) -> Tuple[float, float, float, float]:
    """Get full recency profile parameters from config.

    Args:
        cfg: Configuration object with recall_recency_* attributes.

    Returns:
        Tuple of (time_scale, max_steps, sharpness, floor).
    """
    scale, cap = get_recency_normalisation(cfg)
    sharpness = getattr(cfg, "SOMABRAIN_RECENCY_SHARPNESS", 1.2)
    try:
        sharpness = float(sharpness)
    except Exception:
        sharpness = 1.2
    if not math.isfinite(sharpness) or sharpness <= 0:
        sharpness = 1.0
    floor = getattr(cfg, "SOMABRAIN_RECENCY_FLOOR", 0.05)
    try:
        floor = float(floor)
    except Exception:
        floor = 0.05
    if not math.isfinite(floor) or floor < 0:
        floor = 0.0
    if floor >= 1.0:
        floor = 0.99
    return scale, cap, sharpness, floor


def compute_recency_features(
    ts_epoch: float | None, now_ts: float, cfg: Any
) -> Tuple[float | None, float]:
    """Compute recency features for a timestamp.

    Args:
        ts_epoch: The timestamp to evaluate (Unix epoch).
        now_ts: Current timestamp for comparison.
        cfg: Configuration object with recency parameters.

    Returns:
        Tuple of (recency_steps, recency_boost).
    """
    if ts_epoch is None:
        return None, 1.0
    scale, cap, sharpness, floor = get_recency_profile(cfg)
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


def compute_density_factor(margin: float | None, cfg: Any) -> float:
    """Compute density factor based on cleanup margin.

    Args:
        margin: The cleanup margin value (0-1).
        cfg: Configuration object with density parameters.

    Returns:
        Density factor multiplier (0-1).
    """
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


def extract_cleanup_margin(hit: RecallHit) -> float | None:
    """Extract cleanup margin from a recall hit.

    Args:
        hit: The RecallHit to extract margin from.

    Returns:
        The cleanup margin value or None if not found.
    """
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
    return coerce_float(margin)


def rank_hits(hits: List[RecallHit], query: str) -> List[RecallHit]:
    """Rank hits by score and lexical bonus.

    Args:
        hits: List of RecallHit objects to rank.
        query: The query string for lexical matching.

    Returns:
        Sorted list of RecallHit objects (highest score first).
    """
    ranked: List[Tuple[float, float, float, int, RecallHit]] = []
    for idx, hit in enumerate(hits):
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        lex_bonus = lexical_bonus(payload, query)
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


def apply_weighting_to_hits(hits: List[RecallHit]) -> None:
    """Apply phase and quality weighting to hits in-place.

    This function modifies hits by adding _weight_factor to their payloads
    based on phase priors and quality scores when weighting is enabled.

    Args:
        hits: List of RecallHit objects to apply weighting to.
    """
    if not hits:
        return
    weighting_enabled = False
    priors_env = ""
    quality_exp = 1.0
    if settings is not None:
        try:
            weighting_enabled = bool(
                getattr(settings, "SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)
            )
            priors_env = getattr(settings, "SOMABRAIN_MEMORY_PHASE_PRIORS", "") or ""
            quality_exp = float(getattr(settings, "SOMABRAIN_MEMORY_QUALITY_EXP", 1.0) or 1.0)
        except Exception:
            weighting_enabled = False
    else:
        # Fallback to unified settings when legacy runtime is unavailable
        try:
            from django.conf import settings as _settings

            weighting_enabled = bool(
                getattr(_settings, "SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)
            )
            priors_env = getattr(_settings, "SOMABRAIN_MEMORY_PHASE_PRIORS", "") or ""
            quality_exp = float(getattr(_settings, "SOMABRAIN_MEMORY_QUALITY_EXP", 1.0) or 1.0)
        except Exception:
            weighting_enabled = False
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


def rescore_and_rank_hits(
    hits: List[RecallHit],
    query: str,
    cfg: Any,
    scorer: Any | None = None,
    embedder: Any | None = None,
) -> List[RecallHit]:
    """Rescore and rank hits using scorer/embedder or fallback logic.

    Args:
        hits: List of RecallHit objects to rescore.
        query: The query string for scoring.
        cfg: Configuration object with recency/density parameters.
        scorer: Optional scorer object with score() method.
        embedder: Optional embedder object with embed() method.

    Returns:
        Sorted list of RecallHit objects (highest score first).
    """
    if not scorer or not embedder:
        # Use alternative logic if scorer is not available
        apply_weighting_to_hits(hits)
        return rank_hits(hits, query)

    query_vec = embedder.embed(query)
    now_ts = datetime.now(timezone.utc).timestamp()

    def _text_of(p: dict) -> str:
        """Execute text of.

            Args:
                p: The p.
            """

        return str(p.get("task") or p.get("fact") or p.get("content") or "").strip()

    scored_hits = []
    for hit in hits:
        payload = hit.payload or {}
        text = _text_of(payload)
        if not text:
            # Cannot score without text to embed, assign a low score
            new_score = 0.0
        else:
            candidate_vec = embedder.embed(text)

            # Calculate recency_steps from timestamp
            recency_steps: float | None = None
            recency_boost = 1.0
            ts_epoch = None
            for key in ("timestamp", "ts", "created_at"):
                if key in payload:
                    ts_epoch = parse_payload_timestamp(payload.get(key))
                    if ts_epoch is not None:
                        break
            if ts_epoch is not None:
                recency_steps, recency_boost = compute_recency_features(
                    ts_epoch, now_ts, cfg
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

        margin = extract_cleanup_margin(hit)
        density_factor = compute_density_factor(margin, cfg)
        new_score *= density_factor
        if density_factor != 1.0:
            try:
                payload.setdefault("_density_factor", density_factor)
            except Exception:
                pass
        new_score = max(0.0, min(1.0, float(new_score)))

        hit.score = new_score
        scored_hits.append(hit)

    # Sort by the new score in descending order
    scored_hits.sort(key=lambda h: h.score or 0.0, reverse=True)
    return scored_hits