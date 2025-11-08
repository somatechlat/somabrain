"""
Reward Producer Service

FastAPI service that accepts reward signals and publishes RewardEvent records
to Kafka topic "cog.reward.events" using Avro (fastavro schemaless) when
available, falling back to JSON payloads otherwise.

Environment:
- SOMABRAIN_KAFKA_URL: bootstrap servers (default localhost:30001)
- REWARD_PRODUCER_PORT: HTTP port (default 8083)
- SOMABRAIN_DEFAULT_TENANT: optional tenant label

Metrics:
- soma_reward_total (counter)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException

try:  # preferred kafka client (confluent-kafka / librdkafka)
    from confluent_kafka import Producer as CProducer  # type: ignore
    from confluent_kafka import Consumer as CConsumer  # type: ignore
    from confluent_kafka.admin import AdminClient as CAdminClient, NewTopic  # type: ignore
except Exception:  # pragma: no cover
    CProducer = None  # type: ignore
    CConsumer = None  # type: ignore
    CAdminClient = None  # type: ignore
    NewTopic = None  # type: ignore

try:  # avro optional import
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore

try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


TOPIC = os.getenv("SOMABRAIN_TOPIC_REWARD_EVENTS", "cog.reward.events")


def _bootstrap() -> str:
    url = os.getenv("SOMA_KAFKA_BOOTSTRAP") or os.getenv("SOMABRAIN_KAFKA_URL") or "somabrain_kafka:9092"
    return url.replace("kafka://", "")


def _serde() -> AvroSerde:
    # Require Avro serde in production — no JSON fallback allowed
    if load_schema is None or AvroSerde is None:
        raise RuntimeError("Avro serde is required for RewardProducer; install libs.kafka_cog.avro_schemas and serde")
    return AvroSerde(load_schema("reward_event"))  # type: ignore[arg-type]


def _encode(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def _make_producer():  # pragma: no cover - integration
    # Use confluent-kafka only; fail fast if unavailable
    if CProducer is None:
        raise RuntimeError("confluent-kafka (librdkafka) is required for RewardProducer")
    return ("ck", CProducer({"bootstrap.servers": _bootstrap(), "message.timeout.ms": 10000}))


app = FastAPI(title="Reward Producer")
_producer: Any = None  # KafkaProducer | CProducer | None
_producer_kind: Optional[str] = None  # "ck" for confluent, "kp" for kafka-python
_serde_inst: Optional[AvroSerde] = None
_ready: bool = False
_tenant = os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
_REWARD_COUNT = metrics.get_counter("soma_reward_total", "Reward events posted") if metrics else None
_REWARD_VALUE = metrics.get_histogram(
    "somabrain_reward_value",
    "Observed total reward values",
) if metrics else None


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    # Feature flag gating (default off unless explicitly enabled or composite threads flag)
    ff = os.getenv("SOMABRAIN_FF_REWARD_INGEST", "0").strip().lower() in {"1","true","yes","on"}
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in {"1","true","yes","on"}
    if not (ff or composite):
        # Leave _ready False; health will show disabled
        return
    global _producer, _producer_kind, _serde_inst, _ready
    prod = _make_producer()
    if isinstance(prod, tuple):
        _producer_kind, _producer = prod
    else:
        _producer_kind, _producer = None, None
    _serde_inst = _serde()
    _ready = _producer is not None


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": bool(_ready), "enabled": os.getenv("SOMABRAIN_FF_REWARD_INGEST", "0")}

@app.get("/metrics")
async def metrics_ep():  # type: ignore
    if not metrics:
        # minimal fallback
        return {"status": "metrics not available"}
    return await metrics.metrics_endpoint()


@app.post("/reward/{frame_id}")
async def post_reward(frame_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _producer is None:
        raise HTTPException(status_code=503, detail="Kafka unavailable")
    try:
        r_task = float(payload.get("r_task", 0.0))
        r_user = float(payload.get("r_user", 0.0))
        r_latency = float(payload.get("r_latency", 0.0))
        r_safety = float(payload.get("r_safety", 0.0))
        r_cost = float(payload.get("r_cost", 0.0))
        total = float(payload.get("total", r_task + r_user + r_safety - r_latency - r_cost))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid payload: {e}")
    rec: Dict[str, Any] = {
        "frame_id": str(frame_id),
        "r_task": r_task,
        "r_user": r_user,
        "r_latency": r_latency,
        "r_safety": r_safety,
        "r_cost": r_cost,
        "total": total,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        if _producer_kind == "ck":
            _producer.produce(TOPIC, value=_encode(rec, _serde_inst))  # type: ignore[call-arg]
            # Flush briefly to make smoke tests deterministic
            try:
                _producer.flush(2)  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            _producer.send(TOPIC, value=_encode(rec, _serde_inst))  # type: ignore[attr-defined]
        if _REWARD_COUNT is not None:
            try:
                _REWARD_COUNT.inc()
            except Exception:
                pass
        if _REWARD_VALUE is not None:
            try:
                _REWARD_VALUE.observe(total)
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"produce failed: {e}")
    return {"status": "ok"}


def main() -> None:  # pragma: no cover
    # Run uvicorn only when explicitly invoked; in K8s use command to run module
    port = int(os.getenv("REWARD_PRODUCER_PORT", "8083"))
    try:
        import uvicorn  # type: ignore

        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception:
        # Fallback to a simple loopless run if uvicorn not available
        import time as _time
        import logging
        logging.error("reward_producer: uvicorn not installed; HTTP endpoint not started")
        while True:
            _time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    main()
