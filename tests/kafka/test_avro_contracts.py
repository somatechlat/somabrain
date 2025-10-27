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
    "reward_event": ROOT / "proto" / "cog" / "reward_event.avsc",
    "next_event": ROOT / "proto" / "cog" / "next_event.avsc",
    "config_update": ROOT / "proto" / "cog" / "config_update.avsc",
}


def test_schemas_exist_and_parse() -> None:
    for name, path in SCHEMAS.items():
        assert path.exists(), f"missing schema: {name}"
        data = json.loads(path.read_text())
        assert isinstance(data, dict) and data.get("type") == "record"


# Compatibility alias for external test selectors
def test_can_load_avro_schemas() -> None:
    """Alias to satisfy node IDs used in external scripts."""
    test_schemas_exist_and_parse()


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

    # ConfigUpdate sample
    s2 = json.loads(SCHEMAS["config_update"].read_text())
    ps2 = parse_schema(s2)
    rec2 = {"learning_rate": 0.1, "exploration_temp": 0.7, "ts": "2025-10-25T12:00:00Z"}
    buf2 = io.BytesIO()
    schemaless_writer(buf2, ps2, rec2)
    out2 = schemaless_reader(io.BytesIO(buf2.getvalue()), ps2)
    assert pytest.approx(out2["exploration_temp"], rel=1e-6) == rec2["exploration_temp"]
