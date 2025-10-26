from __future__ import annotations

import time

import pytest


def test_belief_update_soma_serde_roundtrip():
    from libs.kafka_cog.avro_schemas import load_schema
    from libs.kafka_cog.serde import AvroSerde

    schema = load_schema("belief_update_soma")
    serde = AvroSerde(schema)
    record = {
        "stream": "STATE",
        "timestamp": int(time.time() * 1000),
        "delta_error": 0.25,
        "info_gain": None,
        "metadata": {"tenant": "public", "source": "test"},
    }
    payload = serde.serialize(record)
    out = serde.deserialize(payload)
    assert out["stream"] == "STATE"
    assert out["delta_error"] == pytest.approx(0.25, rel=1e-6)


def test_integrator_decode_update_soma_mapping():
    from libs.kafka_cog.avro_schemas import load_schema
    from libs.kafka_cog.serde import AvroSerde
    from somabrain.services.integrator_hub import IntegratorHub

    schema = load_schema("belief_update_soma")
    serde = AvroSerde(schema)
    ts_ms = int(time.time() * 1000)
    soma_rec = {
        "stream": "ACTION",
        "timestamp": ts_ms,
        "delta_error": 0.7,
        "info_gain": None,
        "metadata": {"tenant": "acme"},
    }
    payload = serde.serialize(soma_rec)
    hub = IntegratorHub()
    # Inject serde for soma
    hub._avro_bu_soma = serde  # type: ignore[attr-defined]
    mapped = hub._decode_update_soma(payload)  # type: ignore[attr-defined]
    assert isinstance(mapped, dict)
    assert mapped["domain"] == "action"
    assert mapped["evidence"]["tenant"] == "acme"
    # confidence = exp(-delta_error)
    import math

    assert mapped["confidence"] == pytest.approx(math.exp(-0.7), rel=1e-6)


def test_integrator_context_schema_roundtrip():
    from libs.kafka_cog.avro_schemas import load_schema
    from libs.kafka_cog.serde import AvroSerde

    schema = load_schema("integrator_context")
    serde = AvroSerde(schema)
    # Prepare a minimal global_frame bytes
    gf_bytes = b"{\"ts\":\"now\",\"leader\":\"state\"}"
    rec = {
        "leader_stream": "state",
        "leader_score": 0.9,
        "global_frame": gf_bytes,
        "timestamp": int(time.time() * 1000),
        "policy_decision": True,
    }
    payload = serde.serialize(rec)
    out = serde.deserialize(payload)
    assert out["leader_stream"] == "state"
    assert out["leader_score"] == pytest.approx(0.9, rel=1e-6)
    assert isinstance(out["global_frame"], (bytes, bytearray))
