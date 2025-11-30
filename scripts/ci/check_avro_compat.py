import json
import sys
from pathlib import Path
from common.logging import logger

#!/usr/bin/env python3

# Minimal compatibility check:
    pass
# - New schemas must be valid JSON
# - If there is an older schema with the same (aliased) name, any NEW fields must have defaults
# This is a conservative approximation; a registry-based check is recommended.


def load_schema(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def index_fields(schema: dict) -> dict:
    return {f["name"]: f for f in schema.get("fields", [])}


def check_backward_compatible(old: dict, new: dict) -> list[str]:
    problems: list[str] = []
    oldf = index_fields(old)
    newf = index_fields(new)

    # Removed fields (present in old, absent in new) are breaking
    removed = [k for k in oldf.keys() if k not in newf]
    if removed:
        problems.append(f"Removed fields: {removed}")

    # New fields without defaults are breaking for backward
    for k, f in newf.items():
        if k not in oldf:
            if "default" not in f:
                problems.append(f"New field '{k}' lacks a default")
    return problems


def main():
    repo = Path(__file__).resolve().parents[2]
    new_dir = repo / "proto" / "cog" / "avro"
    old_dir = repo / "proto" / "cog"

    # Validate new schemas parse
    new_schemas = list(new_dir.glob("*.avsc"))
    if not new_schemas:
        print("No new Avro schemas found in proto/cog/avro", file=sys.stderr)
        sys.exit(1)

    for p in new_schemas:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            _ = load_schema(p)
        except Exception as e:
            logger.exception("Exception caught: %s", e)
            raise

    old_reward = old_dir / "reward_event.avsc"
    new_reward = new_dir / "RewardEvent.avsc"
    if old_reward.exists() and new_reward.exists():
        old = load_schema(old_reward)
        new = load_schema(new_reward)
        problems = check_backward_compatible(old, new)
        if problems:
            print(
                "RewardEvent compatibility issues:\n  - " + "\n  - ".join(problems),
                file=sys.stderr, )
            sys.exit(2)

    print("Avro schema checks passed.")


if __name__ == "__main__":
    main()
