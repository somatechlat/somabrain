from __future__ import annotations

import importlib
import json
import pathlib
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = {
    "belief_update": ROOT / "proto" / "cog" / "belief_update.avsc",
    "global_frame": ROOT / "proto" / "cog" / "global_frame.avsc",
    "segment_boundary": ROOT / "proto" / "cog" / "segment_boundary.avsc",
}


def test_schemas_exist_and_parse() -> None:
    for name, path in SCHEMAS.items():
        assert path.exists(), f"missing schema: {name}"
        data = json.loads(path.read_text())
        assert isinstance(data, dict) and data.get("type") == "record"


@pytest.mark.skipif(
    importlib.util.find_spec("fastavro") is None, reason="fastavro not installed"
)
def test_avro_round_trip_fastavro() -> None:
    from fastavro import parse_schema, schemaless_reader, schemaless_writer  # type: ignore
    import io

    # BeliefUpdate sample
    s = json.loads(SCHEMAS["belief_update"].read_text())
    ps = parse_schema(s)
    record = {
        "domain": "state",
        "ts": "2025-10-25T12:00:00Z",
        "delta_error": 0.25,
        "confidence": 0.9,
        "evidence": {"source": "predictor"},
        "posterior": {"hyp": "shift"},
        "model_ver": "v1",
        "latency_ms": 12,
    }
    buf = io.BytesIO()
    schemaless_writer(buf, ps, record)
    out = schemaless_reader(io.BytesIO(buf.getvalue()), ps)
    assert out["domain"] == record["domain"]
    assert pytest.approx(out["delta_error"], rel=1e-6) == record["delta_error"]
