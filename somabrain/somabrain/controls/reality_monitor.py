from __future__ import annotations

from typing import List, Dict, Any

from .metrics import REALITY_OK, REALITY_LOW


def assess_reality(mem_payloads: List[Dict[str, Any]], min_sources: int = 1) -> Dict[str, Any]:
    """Simple truthfulness check: count sources and emit a confidence heuristic.

    - ok: True if len(mem_payloads) >= min_sources
    - sources: number of memory payloads considered
    - confidence: min(1, sources / max(1, min_sources*2))
    """
    sources = len(mem_payloads or [])
    ok = bool(sources >= max(0, int(min_sources)))
    conf = min(1.0, float(sources) / float(max(1, min_sources * 2)))
    try:
        (REALITY_OK if ok else REALITY_LOW).inc()
    except Exception:
        pass
    return {"ok": ok, "sources": sources, "confidence": conf}

