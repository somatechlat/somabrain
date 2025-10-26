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

try:  # kafka optional import
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

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


TOPIC = "cog.reward.events"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("reward_event"))  # type: ignore[arg-type]
    except Exception:
        return None


def _encode(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def _make_producer() -> Optional[KafkaProducer]:  # pragma: no cover - integration
    if KafkaProducer is None:
        return None
    return KafkaProducer(bootstrap_servers=_bootstrap(), acks="1", linger_ms=5)


app = FastAPI(title="Reward Producer")
_producer: Optional[KafkaProducer] = None
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
    global _producer, _serde_inst, _ready
    _producer = _make_producer()
    _serde_inst = _serde()
    _ready = _producer is not None


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": bool(_ready)}

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
        _producer.send(TOPIC, value=_encode(rec, _serde_inst))
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
        import threading
        import time as _time
        print("uvicorn not installed; reward_producer HTTP won't start.")
        while True:
            _time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    main()
