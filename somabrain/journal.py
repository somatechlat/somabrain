"""Journal subsystem removed.

All previous local durability / fallback mechanics have been hard-deleted.
Imports of `somabrain.journal` must be eliminated; any residual usage will
raise immediately so dead paths surface during tests or runtime.

Fail-fast architecture: real backends only (remote memory, Kafka). No disk
journaling, rotation, or compaction remains.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, Optional

__all__: list[str] = []


def _fail(*args, **kwargs):  # pragma: no cover - removal guard
    raise RuntimeError("Journal subsystem removed; use real backends.")


def journal_path(*a, **k):  # legacy symbol retained to surface misuse
    _fail()


def append_event(*a, **k):
    _fail()


def iter_events(*a, **k) -> Generator[Dict[str, Any], None, None]:
    _fail()
    if False:
        yield {}


def rotate_journal(*a, **k):
    _fail()


def compact_journal(*a, **k):
    _fail()
