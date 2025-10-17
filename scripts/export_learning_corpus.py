#!/usr/bin/env python3
"""Export a training corpus from memory JSONL records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from somabrain.learning.dataset import build_examples, iter_jsonl, export_examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SomaBrain training corpus")
    parser.add_argument("input", help="Path to JSONL file with memory records")
    parser.add_argument("output", help="Destination JSONL file")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of records processed",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"input file not found: {input_path}")

    records: List[dict] = []
    for idx, record in enumerate(iter_jsonl(str(input_path))):
        records.append(record)
        if args.limit is not None and idx + 1 >= args.limit:
            break

    examples = build_examples(records)
    export_examples(examples, args.output)
    print(json.dumps({"examples": len(examples)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
