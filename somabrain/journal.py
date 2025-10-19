"""
Journal Module for SomaBrain

This module provides persistent event journaling capabilities for the SomaBrain system.
It implements thread-safe append-only logging of memory operations, API calls, and
system events to JSON Lines (.jsonl) files for durability and replay functionality.

Key Features:
- Thread-safe event logging with file locking
- Namespace-isolated journals for multi-tenancy
- Automatic directory creation and file management
- Event replay for memory reconstruction
- Timestamped event storage with metadata
- Integration with Prometheus metrics

Event Types:
- Memory operations (store, recall, link)
- API requests and responses
- System health and performance metrics
- Consolidation and replay events
- Error and exception logging

Classes:
    None (utility functions only)

Functions:
    append_event: Append an event to a namespace journal
    iter_events: Iterate through events in a namespace journal
    journal_path: Get the file path for a namespace journal
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

_lock = threading.RLock()


def _ensure_dir(path: str | Path) -> None:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)


def journal_path(base_dir: str, namespace: str) -> Path:
    safe_ns = namespace.replace(os.sep, "_")
    return Path(base_dir) / f"{safe_ns}.jsonl"


def append_event(base_dir: str, namespace: str, event: Dict[str, Any]) -> None:
    _ensure_dir(base_dir)
    event = dict(event)
    event.setdefault("ts", time.time())
    path = journal_path(base_dir, namespace)
    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    try:
        from . import metrics as _mx

        _mx.JOURNAL_APPEND.inc()
    except Exception:
        pass


def iter_events(base_dir: str, namespace: str) -> Iterable[Dict[str, Any]]:
    path = journal_path(base_dir, namespace)
    if not path.exists():
        return []

    def _read():
        with _lock:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        try:
                            from . import metrics as _mx

                            _mx.JOURNAL_REPLAY.inc()
                        except Exception:
                            pass
                        yield ev
                    except Exception:
                        try:
                            from . import metrics as _mx

                            _mx.JOURNAL_SKIP.inc()
                        except Exception:
                            pass
                        continue

    return _read()


def rotate_journal(
    base_dir: str, namespace: str, max_bytes: int = 10_000_000, keep: int = 3
) -> Optional[Path]:
    """Rotate the namespace journal if it exceeds max_bytes.

    Returns the path of the rotated file if rotation happened, else None.
    """
    path = journal_path(base_dir, namespace)
    if not path.exists():
        return None
    try:
        size = path.stat().st_size
        if size <= int(max_bytes):
            return None
        # perform rotation with numeric suffixes .1, .2, ... up to keep-1
        with _lock:
            # shift older: .(i) -> .(i+1)
            for i in range(keep - 1, 0, -1):
                src = path.with_name(f"{path.name}.{i}")
                dst = path.with_name(f"{path.name}.{i + 1}")
                if src.exists():
                    try:
                        if dst.exists():
                            dst.unlink()
                    except Exception:
                        pass
                    try:
                        src.rename(dst)
                    except Exception:
                        pass
            # rotate base -> .1 and truncate new base
            rot = path.with_name(f"{path.name}.1")
            try:
                if rot.exists():
                    rot.unlink()
            except Exception:
                pass
            try:
                path.rename(rot)
                path.touch()
            except Exception:
                return None
        try:
            from . import metrics as _mx

            _mx.JOURNAL_ROTATE.inc()
        except Exception:
            pass
        return rot
    except Exception:
        return None


def compact_journal(base_dir: str, namespace: str) -> bool:
    """Compact a namespace journal by eliminating redundant events.

    Strategy:
    - For 'mem' events with the same key, keep only the latest.
    - For 'link' events with the same (from,to,link_type), sum weights (last wins on other fields).
    Writes a new file atomically and replaces the old file.
    Returns True on success, False otherwise.
    """
    path = journal_path(base_dir, namespace)
    if not path.exists():
        return True
    try:
        mem_latest: Dict[str, Dict[str, Any]] = {}
        link_accum: Dict[tuple, Dict[str, Any]] = {}
        for ev in iter_events(base_dir, namespace):
            et = str(ev.get("type") or "")
            if et == "mem":
                # Ensure we use a string key for mem_latest to avoid tuple-vs-str
                # type mismatches when earlier code used composite keys.
                k = ev.get("key") or ev.get("task") or "payload"
                k_str = str(k)
                mem_latest[k_str] = dict(ev)
            elif et == "link":
                fc = ev.get("from") or ev.get("from_coord")
                tc = ev.get("to") or ev.get("to_coord")
                ltype = str(ev.get("link_type") or ev.get("type") or "related")
                if (
                    isinstance(fc, (list, tuple))
                    and isinstance(tc, (list, tuple))
                    and len(fc) == 3
                    and len(tc) == 3
                ):
                    link_key = (tuple(fc), tuple(tc), ltype)
                    cur = link_accum.get(link_key)
                    if cur is None:
                        # first-seen: copy event and coerce weight
                        try:
                            link_accum[link_key] = dict(ev)
                            link_accum[link_key]["weight"] = float(
                                ev.get("weight") or 1.0
                            )
                        except Exception:
                            link_accum[link_key] = dict(ev)
                            link_accum[link_key]["weight"] = 1.0
                    else:
                        # accumulate weight, but avoid overwriting by last-write-wins
                        try:
                            new_w = float(cur.get("weight") or 0.0) + float(
                                ev.get("weight") or 0.0
                            )
                        except Exception:
                            new_w = float(cur.get("weight") or 0.0)
                        # last-write-wins for other fields except weight
                        for kk, vv in ev.items():
                            if kk == "weight":
                                continue
                            cur[kk] = vv
                        cur["weight"] = new_w
        # write compacted stream atomically
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with _lock:
            with tmp_path.open("w", encoding="utf-8") as f:
                for mem_key, mev in mem_latest.items():
                    f.write(json.dumps(mev, ensure_ascii=False) + "\n")
                for link_key, lev in link_accum.items():
                    f.write(json.dumps(lev, ensure_ascii=False) + "\n")
            try:
                tmp_path.replace(path)
            except Exception:
                return False
        return True
    except Exception:
        return False
