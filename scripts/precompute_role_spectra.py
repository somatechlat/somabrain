#!/usr/bin/env python3
"""Precompute and persist unitary role spectra for tokens found in journals.

Usage examples:
  # dry-run: list tokens that would be processed
  python scripts/precompute_role_spectra.py --journal-dir ./data --dry-run

  # actually compute and persist missing entries
  python scripts/precompute_role_spectra.py --journal-dir ./data

  # read tokens from a file (one token per line)
  python scripts/precompute_role_spectra.py --tokens-file tokens.txt

The script is idempotent by default: existing cached entries are skipped unless
--force is provided.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Set


def iter_tokens_from_journal_dir(base_dir: Path) -> Iterable[str]:
    if not base_dir.exists():
        return []
    for p in sorted(base_dir.glob("*.jsonl")):
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    # heuristic extraction of token-like fields
                    for key in ("key", "task", "token", "anchor_id", "id", "name"):
                        v = ev.get(key)
                        if isinstance(v, str) and v:
                            yield v
                    # also check nested payloads
                    payload = ev.get("payload") or ev.get("data")
                    if isinstance(payload, dict):
                        for key in ("token", "id", "name", "anchor_id"):
                            v = payload.get(key)
                            if isinstance(v, str) and v:
                                yield v
        except Exception:
            continue


def tokens_from_file(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t:
                yield t


def main() -> int:
    p = argparse.ArgumentParser(prog="precompute_role_spectra")
    p.add_argument(
        "--journal-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing namespace JSONL journals",
    )
    p.add_argument(
        "--tokens-file", type=Path, default=None, help="File with one token per line"
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Recompute and overwrite existing cache entries",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report tokens that would be processed",
    )
    p.add_argument(
        "--dim",
        type=int,
        default=2048,
        help="HRR dimensionality for role generation (default 2048)",
    )
    p.add_argument("--dtype", choices=("float32", "float64"), default="float32")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    tokens: Set[str] = set()
    if args.tokens_file is not None:
        if not args.tokens_file.exists():
            print(f"Tokens file {args.tokens_file} not found")
            return 2
        for t in tokens_from_file(args.tokens_file):
            tokens.add(t)
    else:
        for t in iter_tokens_from_journal_dir(args.journal_dir):
            tokens.add(t)

    if not tokens:
        print(
            "No tokens found to process (journal dir may be empty). Use --tokens-file or point --journal-dir to your journal location."
        )
        return 0

    # Lazy import heavy modules only when needed
    from somabrain.quantum import HRRConfig, QuantumLayer
    from somabrain.spectral_cache import get_role, set_role

    q = QuantumLayer(HRRConfig(dim=args.dim, dtype=args.dtype, seed=int(args.seed)))

    processed = 0
    skipped = 0
    for token in sorted(tokens):
        cached = None
        try:
            cached = get_role(token)
        except Exception:
            cached = None
        if cached is not None and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"Would process token: {token}")
            processed += 1
            continue
        # generate role (this will also persist via QuantumLayer.make_unitary_role + spectral_cache.set_role)
        try:
            _ = q.make_unitary_role(token)
            # ensure persisted (best-effort): set_role will overwrite if present
            try:
                role_pair = q._role_cache.get(token), q._role_fft_cache.get(token)
                if role_pair[0] is not None and role_pair[1] is not None:
                    set_role(token, role_pair[0], role_pair[1])
            except Exception:
                pass
            processed += 1
            print(f"Processed token: {token}")
        except Exception as e:
            print(f"Failed token {token}: {e}")

    print(f"Done. processed={processed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
