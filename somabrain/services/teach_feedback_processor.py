"""
Teach Feedback Processor

Consumes TeachFeedback events and converts them to RewardEvent records
on cog.reward.events by mapping user ratings to r_user.

Topics:
- Consumes:  cog.teach.feedback (TeachFeedback)
- Produces:  cog.reward.events (RewardEvent)

Rating to r_user mapping:
- 1 -> -1.0, 2 -> -0.5, 3 -> 0.0, 4 -> 0.5, 5 -> 1.0

Environment:
- SOMABRAIN_KAFKA_URL (default localhost:30001)
- TEACH_PROC_GROUP (default teach-feedback-proc)

Metrics:
- somabrain_teach_feedback_total (counter)
- somabrain_teach_r_user (histogram)
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI

try:
    from kafka import KafkaConsumer, KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore
    KafkaProducer = None  # type: ignore

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore

try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


TOPIC_TEACH_FB = "cog.teach.feedback"
TOPIC_REWARD = "cog.reward.events"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _serde(name: str) -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema(name))  # type: ignore[arg-type]
    except Exception:
        return None


def _enc(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def _dec(payload: Optional[bytes], serde: Optional[AvroSerde]) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    if serde is not None:
        try:
            return serde.deserialize(payload)  # type: ignore[arg-type]
        except Exception:
            pass
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def _r_user_from_rating(rating: int) -> float:
    # Map {1,2,3,4,5} -> {-1.0,-0.5,0.0,0.5,1.0}
    try:
        r = int(rating)
    except Exception:
        r = 3
    mapping = {1: -1.0, 2: -0.5, 3: 0.0, 4: 0.5, 5: 1.0}
    return float(mapping.get(r, 0.0))


class TeachFeedbackService:
    def __init__(self) -> None:
        self._bootstrap = _bootstrap()
        self._serde_fb = _serde("teach_feedback")
        self._serde_reward = _serde("reward_event")
        self._producer: Optional[KafkaProducer] = None
        self._stop = threading.Event()
        # Metrics
        self._mx_count = metrics.get_counter("somabrain_teach_feedback_total", "Teach feedback observed") if metrics else None
        self._mx_ruser = metrics.get_histogram("somabrain_teach_r_user", "Teach-derived r_user values") if metrics else None

    def _ensure_clients(self) -> None:
        if KafkaConsumer is None or KafkaProducer is None:
            raise RuntimeError("Kafka client not available")
        if self._producer is None:
            self._producer = KafkaProducer(bootstrap_servers=self._bootstrap, acks="1", linger_ms=5)

    def _emit_reward(self, frame_id: str, r_user: float) -> None:
        if self._producer is None:
            return
        rec = {
            "frame_id": frame_id,
            "r_task": 0.0,
            "r_user": float(r_user),
            "r_latency": 0.0,
            "r_safety": 0.0,
            "r_cost": 0.0,
            "total": float(r_user),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            self._producer.send(TOPIC_REWARD, value=_enc(rec, self._serde_reward))
        except Exception:
            pass

    def run(self) -> None:  # pragma: no cover - integration loop
        self._ensure_clients()
        consumer = KafkaConsumer(
            TOPIC_TEACH_FB,
            bootstrap_servers=self._bootstrap,
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=os.getenv("TEACH_PROC_GROUP", "teach-feedback-proc"),
            consumer_timeout_ms=1000,
        )
        try:
            while not self._stop.is_set():
                msg = consumer.poll(timeout_ms=500)
                if msg is None:
                    continue
                if isinstance(msg, dict):
                    for _, records in msg.items():
                        for rec in records:
                            self._handle_record(rec)
                else:
                    self._handle_record(msg)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    def _handle_record(self, msg: Any) -> None:
        payload = getattr(msg, "value", None)
        ev = _dec(payload, self._serde_fb)
        if not isinstance(ev, dict):
            return
        try:
            frame_id = str(ev.get("frame_id") or "").strip()
            rating = int(ev.get("rating", 0))
            r_user = _r_user_from_rating(rating)
            if self._mx_count is not None:
                try:
                    self._mx_count.inc()
                except Exception:
                    pass
            if self._mx_ruser is not None:
                try:
                    self._mx_ruser.observe(r_user)
                except Exception:
                    pass
            if frame_id:
                self._emit_reward(frame_id, r_user)
        except Exception:
            # Best-effort processor
            pass

    def stop(self) -> None:
        self._stop.set()


app = FastAPI(title="Teach Feedback Processor")
_svc = TeachFeedbackService()
_thread: Optional[threading.Thread] = None


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    global _thread
    _thread = threading.Thread(target=_svc.run, daemon=True)
    _thread.start()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/metrics")
async def metrics_ep():  # type: ignore
    try:
        from somabrain import metrics as _m  # type: ignore
        return await _m.metrics_endpoint()
    except Exception:
        return {"status": "metrics not available"}


def main() -> None:  # pragma: no cover
    port = int(os.getenv("TEACH_FEEDBACK_PROC_PORT", "8086"))
    try:
        import uvicorn  # type: ignore

        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception:
        while True:
            time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    main()
