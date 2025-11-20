#!/usr/bin/env python3
"""Sign a constitution JSON file and record the signature in storage."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# Use the centralized Settings singleton for defaults
from common.config.settings import settings as shared_settings

from somabrain.constitution import ConstitutionEngine
from somabrain.storage import db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "constitution", type=Path, help="Path to constitution JSON file"
    )
    parser.add_argument(
        "--private-key",
        dest="private_key",
        default=shared_settings.constitution_privkey_path,
        help="PEM private key used for signing (defaults to SOMABRAIN_CONSTITUTION_PRIVKEY_PATH)",
    )
    parser.add_argument(
        "--signer-id",
        dest="signer_id",
        default=shared_settings.constitution_signer_id,
        help="Signer identifier recorded alongside the signature",
    )
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=shared_settings.postgres_dsn,
        help="Override database URL (defaults to SOMABRAIN_POSTGRES_DSN)",
    )
    parser.add_argument(
        "--redis-url",
        dest="redis_url",
        default=shared_settings.redis_url,
        help="Override Redis URL (defaults to SOMA_REDIS_URL)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.private_key:
        raise SystemExit(
            "--private-key or SOMABRAIN_CONSTITUTION_PRIVKEY_PATH must be provided"
        )
    if args.db_url:
        db.reset_engine(args.db_url)
        os.environ["SOMABRAIN_POSTGRES_DSN"] = args.db_url
    document = json.loads(args.constitution.read_text(encoding="utf-8"))
    engine = ConstitutionEngine(db_url=args.db_url, redis_url=args.redis_url)
    engine.save(document)
    os.environ["SOMABRAIN_CONSTITUTION_SIGNER_ID"] = args.signer_id
    signature = engine.sign(args.private_key)
    if not signature:
        raise SystemExit("Failed to sign constitution")
    print(f"checksum={engine.get_checksum()} signature={signature}")


if __name__ == "__main__":
    main()
