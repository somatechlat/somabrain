#!/usr/bin/env python3
"""Administrative helper for SomaBrain outbox endpoints.

Provides multiple subcommands:

    list   -> fetches /admin/outbox with optional filters
    replay -> POSTs /admin/outbox/replay with a set of event IDs
    tail   -> watch the outbox for new events
    check  -> fail when pending/failed counts exceed a threshold (for CI)

Authentication:
  Uses the same Bearer token as the main API. Either pass --token or set
  SOMABRAIN_API_TOKEN/SOMA_API_TOKEN in the environment.
"""

from __future__ import annotations

import argparse
import json
from django.conf import settings
from somabrain.infrastructure import get_api_base_url
import sys
from typing import Any, Dict, Iterable

import requests
import time
from collections import defaultdict


def _default_base_url() -> str:
    # Use the centralized helper to obtain the API base URL, falling back to the
    # historic default only if the helper returns ``None``.
    """Execute default base url."""

    from django.conf import settings

    return (
        get_api_base_url()
        or getattr(settings, "SOMABRAIN_API_URL", "http://localhost:9696")
    ).rstrip("/")


def _default_token() -> str | None:
    # Use centralized Settings for token retrieval.
    # Use the centralized Settings field for the outbox API token.
    """Execute default token."""

    return getattr(settings, "SOMABRAIN_OUTBOX_API_TOKEN", None)


def _auth_headers(token: str | None) -> dict[str, str]:
    """Execute auth headers.

    Args:
        token: The token.
    """

    if not token:
        raise SystemExit(
            "Admin token required. Pass --token or set SOMABRAIN_API_TOKEN."
        )
    return {"Authorization": f"Bearer {token}"}


def _fetch_page(
    base: str,
    token: str | None,
    *,
    status: str,
    tenant: str | None,
    limit: int,
    offset: int = 0,
) -> Dict[str, Any]:
    """Execute fetch page.

    Args:
        base: The base.
        token: The token.
    """

    params = {"status": status, "limit": limit, "offset": offset}
    if tenant:
        params["tenant"] = tenant
    resp = requests.get(
        f"{base}/admin/outbox",
        params=params,
        headers=_auth_headers(token),
        timeout=10,
    )
    if resp.status_code != 200:
        raise SystemExit(f"list failed: HTTP {resp.status_code} {resp.text}")
    return resp.json()


def _print_events(events: Iterable[Dict[str, Any]], as_json: bool) -> None:
    """Execute print events.

    Args:
        events: The events.
        as_json: The as_json.
    """

    if as_json:
        print(json.dumps(list(events), indent=2, sort_keys=True))
        return
    for ev in events:
        created = ev.get("created_at") or "-"
        tenant = ev.get("tenant_id") or "default"
        print(
            f"[{ev.get('id')}] {ev.get('status')} tenant={tenant} topic={ev.get('topic')} dedupe={ev.get('dedupe_key')} created={created}"
        )


def cmd_list(args: argparse.Namespace) -> None:
    """Execute cmd list.

    Args:
        args: The args.
    """

    data = _fetch_page(
        args.url,
        args.token,
        status=args.status,
        tenant=args.tenant,
        limit=args.limit,
        offset=args.offset,
    )
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        _print_events(data.get("events", []), as_json=False)
        print(f"count={data.get('count', 0)}")


def cmd_replay(args: argparse.Namespace) -> None:
    """Execute cmd replay.

    Args:
        args: The args.
    """

    base = args.url
    payload = {"event_ids": args.event_ids}
    resp = requests.post(
        f"{base}/admin/outbox/replay",
        json=payload,
        headers=_auth_headers(args.token),
        timeout=10,
    )
    if resp.status_code != 200:
        raise SystemExit(f"replay failed: HTTP {resp.status_code} {resp.text}")
    print(json.dumps(resp.json(), indent=2, sort_keys=True))


def cmd_tail(args: argparse.Namespace) -> None:
    """Execute cmd tail.

    Args:
        args: The args.
    """

    seen: set[int] = set()
    try:
        while True:
            data = _fetch_page(
                args.url,
                args.token,
                status=args.status,
                tenant=args.tenant,
                limit=args.limit,
            )
            events = data.get("events", [])
            new_events = [ev for ev in events if ev.get("id") not in seen]
            if new_events:
                _print_events(new_events, as_json=args.json)
                for ev in new_events:
                    ev_id = ev.get("id")
                    if isinstance(ev_id, int):
                        seen.add(ev_id)
                if len(seen) > 5000:
                    seen = set(list(sorted(seen))[-2000:])
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return


def _iter_events(
    base: str,
    token: str | None,
    *,
    status: str,
    tenant: str | None,
    page_size: int,
):
    """Execute iter events.

    Args:
        base: The base.
        token: The token.
    """

    offset = 0
    while True:
        data = _fetch_page(
            base,
            token,
            status=status,
            tenant=tenant,
            limit=page_size,
            offset=offset,
        )
        events = data.get("events", [])
        if not events:
            break
        for ev in events:
            yield ev
        if len(events) < page_size:
            break
        offset += page_size


def cmd_check(args: argparse.Namespace) -> None:
    """Execute cmd check.

    Args:
        args: The args.
    """

    max_pending = args.max_pending
    counts: dict[str, int] = defaultdict(int)
    for ev in _iter_events(
        args.url,
        args.token,
        status=args.status,
        tenant=args.tenant,
        page_size=args.page_size,
    ):
        tenant_id = ev.get("tenant_id") or "default"
        counts[tenant_id] += 1
        if counts[tenant_id] > max_pending:
            raise SystemExit(
                f"tenant {tenant_id} has {counts[tenant_id]} {args.status} events (max {max_pending})"
            )
    print(
        f"OK: max {args.status} events per tenant = {max(counts.values(), default=0)} (threshold {max_pending})"
    )


def build_parser() -> argparse.ArgumentParser:
    """Execute build parser."""

    ap = argparse.ArgumentParser(description="SomaBrain outbox admin helper")
    ap.add_argument("--url", default=_default_base_url())
    ap.add_argument("--token", default=_default_token())
    sub = ap.add_subparsers(dest="command", required=True)

    ap_list = sub.add_parser("list", help="List outbox events")
    ap_list.add_argument(
        "--status", default="pending", choices=["pending", "failed", "sent"]
    )
    ap_list.add_argument("--tenant", default=None)
    ap_list.add_argument("--limit", type=int, default=50)
    ap_list.add_argument("--offset", type=int, default=0)
    ap_list.add_argument("--json", action="store_true")
    ap_list.set_defaults(func=cmd_list)

    ap_replay = sub.add_parser("replay", help="Replay specific event IDs")
    ap_replay.add_argument("event_ids", nargs="+", type=int)
    ap_replay.set_defaults(func=cmd_replay)

    ap_tail = sub.add_parser("tail", help="Watch outbox events in real time")
    ap_tail.add_argument(
        "--status", default="pending", choices=["pending", "failed", "sent"]
    )
    ap_tail.add_argument("--tenant", default=None)
    ap_tail.add_argument("--limit", type=int, default=50)
    ap_tail.add_argument("--interval", type=float, default=2.0)
    ap_tail.add_argument("--json", action="store_true")
    ap_tail.set_defaults(func=cmd_tail)

    ap_check = sub.add_parser("check", help="Fail if pending exceeds threshold")
    ap_check.add_argument(
        "--status", default="pending", choices=["pending", "failed", "sent"]
    )
    ap_check.add_argument("--tenant", default=None)
    ap_check.add_argument("--max-pending", type=int, default=100)
    ap_check.add_argument("--page-size", type=int, default=500)
    ap_check.set_defaults(func=cmd_check)

    return ap


def main(argv: list[str] | None = None) -> int:
    """Execute main.

    Args:
        argv: The argv.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except requests.RequestException as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
