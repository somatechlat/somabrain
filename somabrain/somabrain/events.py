from __future__ import annotations

import re
from typing import Dict


def extract_event_fields(text: str) -> Dict[str, str]:
    """Heuristic extraction of simple event fields from a short sentence.

    Returns optional keys among: who, did, what, where, when, why.
    This is deliberately lightweight and best-effort.
    """
    out: Dict[str, str] = {}
    t = (text or "").strip()
    if not t:
        return out
    # where: " at X" or " in X"
    m = re.search(r"\b(?:at|in)\s+([A-Za-z0-9_\-]+)", t)
    if m:
        out["where"] = m.group(1)
    # why: "because Y" or "so that Y"
    m = re.search(r"\b(?:because|so that)\s+(.+)$", t)
    if m:
        out["why"] = m.group(1).strip()
    # when: "on <date>" or "at <time>" (simple token after preposition)
    m = re.search(r"\b(?:on|at)\s+([0-9]{1,2}[:/][0-9]{1,2}(?:[:/][0-9]{2})?)", t)
    if m and "where" not in out:
        out["when"] = m.group(1)
    # who/did/what: naive split "<who> <verb> <what>"
    toks = re.findall(r"[A-Za-z0-9_\-]+", t)
    if len(toks) >= 3:
        out.setdefault("who", toks[0])
        out.setdefault("did", toks[1])
        out.setdefault("what", toks[2])
    return out

