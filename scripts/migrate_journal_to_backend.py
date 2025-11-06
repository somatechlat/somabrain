"""Replay journal events into a memory client backend.

The helper is intentionally simple: tests import ``migrate_journal`` and call it
with a base directory, namespace, and a ``MemoryClient`` instance. The function
replays journalled memory/link events into the provided client and returns the
number of memories and links applied.
"""
"""Deprecated: journaling removed. Do not use.

This script has been removed. Use the real backends via `scripts/dev_up.sh`.
"""

import sys

raise SystemExit("scripts/migrate_journal_to_backend.py is removed; journaling is not supported.")
from __future__ import annotations

from typing import Tuple

import math

from somabrain.journal import iter_events


def migrate_journal(base_dir: str, namespace: str, client) -> Tuple[int, int]:
    """Replay journalled events for ``namespace`` into ``client``.

    Returns
    -------
    (memories_added, links_added)
    """

    mem_added = 0
    link_added = 0
    for event in iter_events(base_dir, namespace):
        etype = str(event.get("type") or "").lower()
        if etype == "mem":
            payload = dict(event.get("payload") or {})
            key = str(
                event.get("key")
                or event.get("task")
                or payload.get("task")
                or "payload"
            )

            # Idempotency: skip if an existing payload already matches this event.
            skip = False
            try:
                coord = client.coord_for_key(key)
                existing = client.payloads_for_coords([coord]) or []
                for current in existing:
                    if all(current.get(k) == v for k, v in payload.items()):
                        skip = True
                        break
            except Exception:
                skip = False

            if skip:
                continue

            client.remember(key, payload)
            mem_added += 1
        elif etype == "link":
            from_coord = event.get("from") or event.get("from_coord")
            to_coord = event.get("to") or event.get("to_coord")
            if (
                isinstance(from_coord, (list, tuple))
                and isinstance(to_coord, (list, tuple))
                and len(from_coord) >= 3
                and len(to_coord) >= 3
            ):
                link_type = str(
                    event.get("link_type") or event.get("type") or "related"
                )
                weight = float(event.get("weight") or 1.0)
                fcoord = (
                    float(from_coord[0]),
                    float(from_coord[1]),
                    float(from_coord[2]),
                )
                tcoord = (
                    float(to_coord[0]),
                    float(to_coord[1]),
                    float(to_coord[2]),
                )

                # Idempotency: check for an existing identical edge.
                skip_link = False
                try:
                    existing_edges = client.links_from(
                        fcoord, type_filter=link_type, limit=0
                    )
                    for edge in existing_edges:
                        eto = edge.get("to")
                        if isinstance(eto, (list, tuple)) and len(eto) >= 3:
                            eto_tuple = (
                                float(eto[0]),
                                float(eto[1]),
                                float(eto[2]),
                            )
                            if (
                                all(
                                    math.isclose(
                                        eto_tuple[i],
                                        tcoord[i],
                                        rel_tol=1e-6,
                                        abs_tol=1e-6,
                                    )
                                    for i in range(3)
                                )
                                and edge.get("type") == link_type
                                and math.isclose(
                                    float(edge.get("weight", 1.0)),
                                    float(weight),
                                    rel_tol=1e-6,
                                    abs_tol=1e-6,
                                )
                            ):
                                skip_link = True
                                break
                except Exception:
                    skip_link = False

                if skip_link:
                    continue

                client.link(
                    fcoord,
                    tcoord,
                    link_type=link_type,
                    weight=weight,
                )
                link_added += 1
    return mem_added, link_added


if __name__ == "__main__":
    import argparse
    import importlib
    import sys

    parser = argparse.ArgumentParser(description="Replay journal events into a backend")
    parser.add_argument("base_dir", help="Directory containing journal files")
    parser.add_argument("namespace", help="Namespace to replay")
    parser.add_argument(
        "client_factory",
        help="Python path to a callable returning a configured MemoryClient (e.g. somabrain.cli:get_memory_client)",
    )
    args = parser.parse_args()

    module_name, _, attr = args.client_factory.partition(":")
    if not module_name or not attr:
        parser.error("client_factory must be in module:callable format")

    module = importlib.import_module(module_name)
    factory = getattr(module, attr)
    client = factory()

    added_mem, added_links = migrate_journal(args.base_dir, args.namespace, client)
    print(f"Replayed {added_mem} memories and {added_links} links", file=sys.stderr)
