#!/usr/bin/env python3
"""Export a training corpus from memory JSONL records with run metadata."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dataclasses import asdict

# Unified configuration – use the central Settings instance
from common.config.settings import settings
from somabrain.learning.dataset import build_examples, iter_jsonl, export_examples


def _git_metadata() -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if commit:
            meta["commit"] = commit
    except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")

    try:
        status = subprocess.run(
            ["git", "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status:
            meta["dirty"] = True
            meta["status"] = status.splitlines()
        elif meta:
            meta["dirty"] = False
    except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")
    return meta


def _config_snapshot() -> Dict[str, Any]:
    cfg = settings
    snapshot: Dict[str, Any] = {}
    try:
        cfg_dict = asdict(cfg)
        snapshot["learning_loop_enabled"] = cfg_dict.get("learning_loop_enabled")
        snapshot["namespace"] = cfg_dict.get("namespace")
        if isinstance(cfg_dict.get("http"), dict):
            snapshot["http_endpoint"] = cfg_dict["http"].get("endpoint")
        snapshot["wm_size"] = cfg_dict.get("wm_size")
        snapshot["embed_provider"] = cfg_dict.get("embed_provider")
        snapshot["targets"] = cfg_dict.get("targets")
        # Generate deterministic digest for the full config to aid audits
        snapshot["digest"] = _digest_dict(cfg_dict)
    except Exception:
        snapshot["error"] = "failed_to_serialize_config"
    return snapshot


def _digest_dict(payload: Dict[str, Any]) -> Optional[str]:
    try:
        blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        return None
    import hashlib

    return hashlib.sha256(blob).hexdigest()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export SomaBrain training corpus")
    parser.add_argument("input", help="Path to JSONL file with memory records")
    parser.add_argument("output", help="Destination JSONL file")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of records processed",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass learning_loop_enabled guard",
    )
    parser.add_argument(
        "--metadata-out",
        help="Optional path to store run metadata as JSON",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"input file not found: {input_path}")

    cfg = settings
    if not getattr(cfg, "learning_loop_enabled", False) and not args.force:
        parser.error(
            "learning_loop_enabled flag is false. Enable it in config or rerun with --force."
        )

    records: List[dict] = []
    for idx, record in enumerate(iter_jsonl(str(input_path))):
        records.append(record)
        if args.limit is not None and idx + 1 >= args.limit:
            break

    examples = build_examples(records)
    export_examples(examples, args.output)

    metadata: Dict[str, Any] = {
        "generated_at": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "input": str(input_path),
        "output": str(Path(args.output)),
        "examples": len(examples),
        "limit": args.limit,
        "git": _git_metadata(),
        "config": _config_snapshot(),
    }

    print(json.dumps(metadata, indent=2))

    if args.metadata_out:
        meta_path = Path(args.metadata_out)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
