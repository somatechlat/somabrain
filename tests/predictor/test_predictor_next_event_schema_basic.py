import json
from pathlib import Path


def test_next_event_schema_has_regret_and_tenant_unique_pred_suite():  # predictor-focused validation
    root = Path(__file__).resolve().parents[2]
    schema_path = root / "proto" / "cog" / "next_event.avsc"
    data = json.loads(schema_path.read_text())
    fields = {f["name"] for f in data.get("fields", [])}
    assert "tenant" in fields, "tenant field missing in next_event schema"
    assert "regret" in fields, "regret field missing in next_event schema"
