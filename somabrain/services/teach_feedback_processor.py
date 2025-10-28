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
from collections import deque

from fastapi import FastAPI

try:
    from kafka import KafkaConsumer, KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore
    KafkaProducer = None  # type: ignore

try:
    from confluent_kafka import Producer as CKProducer  # type: ignore
    from confluent_kafka import Consumer as CKConsumer  # type: ignore
except Exception:  # pragma: no cover
    CKProducer = None  # type: ignore
    CKConsumer = None  # type: ignore

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
        self._ck_producer: Optional[CKProducer] = None
        self._stop = threading.Event()
        # Basic dedup cache for recent frame_ids
        size = max(32, int(os.getenv("TEACH_DEDUP_CACHE_SIZE", "512")))
        self._seen_frames = deque(maxlen=size)
        self._seen_set = set()
        # Metrics
        self._mx_count = metrics.get_counter("somabrain_teach_feedback_total", "Teach feedback observed") if metrics else None
        self._mx_ruser = metrics.get_histogram("somabrain_teach_r_user", "Teach-derived r_user values") if metrics else None
        self._mx_reward_ok = metrics.get_counter("somabrain_reward_events_published_total", "Reward events successfully published") if metrics else None
        self._mx_reward_fail = metrics.get_counter("somabrain_reward_events_failed_total", "Reward events publish failures") if metrics else None

    def _ensure_clients(self) -> None:
        if KafkaConsumer is None:
            raise RuntimeError("Kafka client not available")
        # Prefer confluent-kafka for production reliability
        if self._ck_producer is None and CKProducer is not None:
            try:
                print(f"teach_proc: creating ck-producer bootstrap={self._bootstrap}", flush=True)
            except Exception:
                pass
            self._ck_producer = CKProducer({
                "bootstrap.servers": self._bootstrap,
                "socket.timeout.ms": 5000,
                "message.timeout.ms": 5000,
                # Avoid requiring python-snappy in host tools; keep interop simple
                "compression.type": "none",
            })
        if self._producer is None and (KafkaProducer is not None):
            try:
                print(f"teach_proc: creating producer bootstrap={self._bootstrap}", flush=True)
            except Exception:
                pass
            self._producer = KafkaProducer(bootstrap_servers=self._bootstrap, acks="1", linger_ms=5, compression_type="gzip")

    def _emit_reward(self, frame_id: str, r_user: float) -> None:
        try:
            print("teach_proc: _emit_reward called", flush=True)
        except Exception:
            pass
        # Build reward record (legacy reward_event schema fields); compatible with Avro serde fallback
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
        # If confluent producer exists, use it
        if self._ck_producer is not None:
            try:
                print("teach_proc: using ck-producer", flush=True)
            except Exception:
                pass
            payload = _enc(rec, self._serde_reward)
            delivered = {"ok": False, "err": None}

            def _cb(err, _msg):  # type: ignore
                delivered["ok"] = err is None
                delivered["err"] = err

            try:
                self._ck_producer.produce(TOPIC_REWARD, value=payload, on_delivery=_cb)
                remaining = self._ck_producer.flush(5)
                if delivered["ok"] and remaining == 0:
                    try:
                        print(f"teach_proc: emitted reward for frame_id={frame_id} r_user={r_user}", flush=True)
                    except Exception:
                        pass
                    if self._mx_reward_ok is not None:
                        try:
                            self._mx_reward_ok.inc()
                        except Exception:
                            pass
                else:
                    try:
                        print(f"teach_proc: failed to emit reward via ck: err={delivered['err']} remaining={remaining}", flush=True)
                    except Exception:
                        pass
                    if self._mx_reward_fail is not None:
                        try:
                            self._mx_reward_fail.inc()
                        except Exception:
                            pass
            except Exception as e:
                try:
                    print(f"teach_proc: ck-produce error: {e}", flush=True)
                except Exception:
                    pass
                if self._mx_reward_fail is not None:
                    try:
                        self._mx_reward_fail.inc()
                    except Exception:
                        pass
            return
        if self._producer is None:
            return
        try:
            print("teach_proc: using kafka-python producer", flush=True)
        except Exception:
            pass
        try:
            fut = self._producer.send(TOPIC_REWARD, value=_enc(rec, self._serde_reward))
            try:
                # Ensure timely delivery in small dev setups
                fut.get(timeout=5)
                try:
                    print(f"teach_proc: emitted reward for frame_id={frame_id} r_user={r_user}", flush=True)
                except Exception:
                    pass
                if self._mx_reward_ok is not None:
                    try:
                        self._mx_reward_ok.inc()
                    except Exception:
                        pass
            except Exception:
                try:
                    self._producer.flush(timeout=2)
                except Exception:
                    pass
                if self._mx_reward_fail is not None:
                    try:
                        self._mx_reward_fail.inc()
                    except Exception:
                        pass
        except Exception:
            try:
                print("teach_proc: failed to emit reward", flush=True)
            except Exception:
                pass
            if self._mx_reward_fail is not None:
                try:
                    self._mx_reward_fail.inc()
                except Exception:
                    pass

    def run(self) -> None:  # pragma: no cover - integration loop
        self._ensure_clients()
        group_id = os.getenv("TEACH_PROC_GROUP", "teach-feedback-proc")
        # Prefer confluent-kafka consumer if available
        if CKConsumer is not None:
            conf = {
                "bootstrap.servers": self._bootstrap,
                "group.id": group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
            c = CKConsumer(conf)
            c.subscribe([TOPIC_TEACH_FB])
            try:
                while not self._stop.is_set():
                    try:
                        msg = c.poll(0.5)
                        if msg is None or msg.error():
                            continue
                        payload = msg.value()
                        if payload:
                            self._handle_payload(payload)
                    except Exception as e:
                        try:
                            print(f"teach_proc: consumer error (ck): {e}", flush=True)
                        except Exception:
                            pass
                        time.sleep(0.25)
            finally:
                try:
                    c.close()
                except Exception:
                    pass
            return
        # Fallback to kafka-python consumer
        consumer = KafkaConsumer(
            TOPIC_TEACH_FB,
            bootstrap_servers=self._bootstrap,
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=group_id,
            consumer_timeout_ms=1000,
        )
        try:
            while not self._stop.is_set():
                try:
                    msg = consumer.poll(timeout_ms=500)
                    if msg is None:
                        continue
                    if isinstance(msg, dict):
                        for _, records in msg.items():
                            for rec in records:
                                self._handle_record(rec)
                    else:
                        self._handle_record(msg)
                except Exception as e:
                    try:
                        print(f"teach_proc: consumer error (kp): {e}", flush=True)
                    except Exception:
                        pass
                    time.sleep(0.25)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    def _handle_payload(self, payload: Optional[bytes]) -> None:
        ev = _dec(payload, self._serde_fb)
        if not isinstance(ev, dict):
            return
        try:
            frame_id = str(ev.get("frame_id") or "").strip()
            rating = int(ev.get("rating", 0))
            r_user = max(-1.0, min(1.0, _r_user_from_rating(rating)))
            # Minimal observability for smoke
            try:
                print(f"teach_feedback: frame_id={frame_id} rating={rating} -> r_user={r_user}", flush=True)
            except Exception:
                pass
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
                # Deduplicate recent frame_ids
                if frame_id in self._seen_set:
                    return
                self._seen_set.add(frame_id)
                self._seen_frames.append(frame_id)
                if len(self._seen_set) > self._seen_frames.maxlen:
                    self._seen_set = set(self._seen_frames)
                self._emit_reward(frame_id, r_user)
        except Exception:
            # Best-effort processor
            pass

    def _handle_record(self, msg: Any) -> None:
        payload = getattr(msg, "value", None)
        self._handle_payload(payload)

    def stop(self) -> None:
        self._stop.set()


app = FastAPI(title="Teach Feedback Processor")
_svc = TeachFeedbackService()
_thread: Optional[threading.Thread] = None


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    global _thread
    enabled = str(os.getenv("SOMABRAIN_ENABLE_TEACH_FEEDBACK", "0")).lower() in {"1", "true", "yes", "on"}
    if enabled:
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
