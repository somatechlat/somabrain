import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "proto" / "cog"


@pytest.mark.parametrize(
    "name,required_fields",
    [
        ("reward_event.avsc", {"frame_id", "r_task", "r_user", "r_latency", "r_safety", "r_cost", "total", "ts"}),
        ("next_event.avsc", {"frame_id", "predicted_state", "confidence", "ts"}),
        ("config_update.avsc", {"learning_rate", "exploration_temp", "ts"}),
    ],
)
def test_schema_has_expected_fields(name, required_fields):
    path = SCHEMA_DIR / name
    assert path.exists(), f"missing schema: {path}"
    data = json.loads(path.read_text())
    assert data.get("type") == "record"
    fields = {f["name"] for f in data.get("fields", [])}
    missing = required_fields - fields
    assert not missing, f"{name} missing fields: {missing}"
