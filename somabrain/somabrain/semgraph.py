from __future__ import annotations

from enum import Enum


class RelationType(str, Enum):
    related = "related"
    causes = "causes"
    contrasts = "contrasts"
    part_of = "part_of"
    depends_on = "depends_on"
    motivates = "motivates"
    summary_of = "summary_of"
    co_replay = "co_replay"


def normalize_relation(t: str | None) -> str:
    if not t:
        return RelationType.related.value
    try:
        return RelationType(t).value
    except Exception:
        # fallback to generic
        return RelationType.related.value

