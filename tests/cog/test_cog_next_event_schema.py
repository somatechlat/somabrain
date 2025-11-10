from __future__ import annotations

import importlib
import json
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "proto" / "cog" / "next_event.avsc"


def test_cog_next_event_schema_exists_and_fields():
    assert SCHEMA_PATH.exists(), "next_event schema missing"
    data = json.loads(SCHEMA_PATH.read_text())
    fields = {f["name"] for f in data.get("fields", [])}
    assert {"frame_id", "predicted_state", "confidence", "ts"}.issubset(fields)


@pytest.mark.skipif(
    importlib.util.find_spec("fastavro") is None, reason="fastavro not installed"
)
def test_cog_next_event_round_trip_fastavro():
    from fastavro import parse_schema, schemaless_reader, schemaless_writer  # type: ignore
    import io

    s = json.loads(SCHEMA_PATH.read_text())
    ps = parse_schema(s)
    rec = {
        "frame_id": "agent:2025-10-25T12:00:00Z",
        "predicted_state": "intent:purchase",
        "confidence": 0.85,
        "ts": "2025-10-25T12:00:00Z",
    }
    buf = io.BytesIO()
    schemaless_writer(buf, ps, rec)
    out = schemaless_reader(io.BytesIO(buf.getvalue()), ps)
    assert out["predicted_state"].startswith("intent:")
    assert pytest.approx(out["confidence"], rel=1e-6) == rec["confidence"]
