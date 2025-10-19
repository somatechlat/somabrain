#!/usr/bin/env python3
"""Migrate legacy journal events into the memory outbox."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from somabrain.config import Config
from somabrain.journal import iter_events, journal_path


def _load_namespaces(journal_dir: Path, explicit: Optional[List[str]]) -> List[str]:
    if explicit:
        return explicit
    namespaces: List[str] = []
    for file in journal_dir.glob("*.jsonl"):
        namespaces.append(file.stem)
    return namespaces


def _convert_event(event: dict) -> Optional[dict]:
    op = str(event.get("op") or event.get("type") or "").lower()
    payload = {}
    if op in {"mem", "remember", "store"}:
        payload = {
            "key": event.get("key"),
            "payload": event.get("payload") or {},
            "universe": event.get("universe"),
        }
        return {"op": "remember", "payload": payload}
    if op in {"remember_bulk", "mem_bulk", "bulk"}:
        payload = {
            "items": event.get("items") or [],
            "universe": event.get("universe"),
            "request_id": event.get("request_id"),
        }
        return {"op": "remember_bulk", "payload": payload}
    if op in {"link", "alink"}:
        payload = {
            "from_coord": event.get("from_coord") or event.get("from"),
            "to_coord": event.get("to_coord") or event.get("to"),
            "link_type": event.get("link_type", "related"),
            "weight": event.get("weight", 1.0),
        }
        return {"op": "link", "payload": payload}
    return None


def migrate_namespace(
    journal_dir: Path,
    namespace: str,
    outbox_path: Path,
    *,
    dry_run: bool = False,
    archive: bool = True,
) -> Tuple[int, int]:
    events = list(iter_events(str(journal_dir), namespace))
    converted: List[dict] = []
    for event in events:
        entry = _convert_event(event)
        if entry:
            converted.append(entry)
    if not dry_run and converted:
        outbox_path.parent.mkdir(parents=True, exist_ok=True)
        with outbox_path.open("a", encoding="utf-8") as handle:
            for entry in converted:
                json.dump(entry, handle)
                handle.write("\n")
    if not dry_run and archive:
        src = journal_path(str(journal_dir), namespace)
        if src.exists():
            backup = src.with_suffix(src.suffix + ".migrated")
            src.rename(backup)
    return len(events), len(converted)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert journal fallback entries into memory outbox."
    )
    parser.add_argument(
        "--journal-dir",
        default=None,
        help="Directory containing namespace journal files (defaults to config.journal_dir).",
    )
    parser.add_argument(
        "--outbox-path",
        default=None,
        help="Path to the memory outbox file (defaults to config.outbox_path).",
    )
    parser.add_argument(
        "--namespace",
        action="append",
        help="Namespace(s) to migrate. Defaults to all journals in the directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report without writing to the outbox or archiving journals.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Do not rename journal files after migration.",
    )
    args = parser.parse_args()

    cfg = Config()
    journal_dir = Path(args.journal_dir or cfg.journal_dir).expanduser()
    outbox_path = Path(args.outbox_path or cfg.outbox_path).expanduser()
    namespaces = _load_namespaces(journal_dir, args.namespace)

    if not namespaces:
        print("No journals found; nothing to migrate.", file=sys.stderr)
        return 0

    total_events = 0
    total_converted = 0
    for ns in namespaces:
        events, converted = migrate_namespace(
            journal_dir,
            ns,
            outbox_path,
            dry_run=args.dry_run,
            archive=not args.no_archive,
        )
        total_events += events
        total_converted += converted
        print(
            f"namespace={ns} events={events} converted={converted} dry_run={args.dry_run}",
            file=sys.stderr,
        )

    print(
        f"Completed migration: namespaces={len(namespaces)} events={total_events} converted={total_converted}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
