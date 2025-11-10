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
from somabrain.common.infra import assert_ready

try:
    from confluent_kafka import Producer as CKProducer  # type: ignore
    from confluent_kafka import Consumer as CKConsumer  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        f"teach_feedback_processor: confluent-kafka required in strict mode: {e}"
    )

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        f"teach_feedback_processor: Avro libs unavailable in strict mode: {e}"
    )

try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


TOPIC_TEACH_FB = "cog.teach.feedback"
TOPIC_REWARD = "cog.reward.events"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _serde(name: str) -> AvroSerde:
    return AvroSerde(load_schema(name))  # type: ignore[arg-type]


def _enc(rec: Dict[str, Any], serde: AvroSerde) -> bytes:
    return serde.serialize(rec)


def _dec(
    payload: Optional[bytes], serde: AvroSerde
) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    try:
        return serde.deserialize(payload)  # type: ignore[arg-type]
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
        self._ck_producer: Optional[CKProducer] = None
        self._stop = threading.Event()
        # Basic dedup cache for recent frame_ids
        size = max(32, int(os.getenv("TEACH_DEDUP_CACHE_SIZE", "512")))
        self._seen_frames = deque(maxlen=size)
        self._seen_set = set()
        # Metrics
        self._mx_count = (
            metrics.get_counter(
                "somabrain_teach_feedback_total", "Teach feedback observed"
            )
            if metrics
            else None
        )
        self._mx_ruser = (
            metrics.get_histogram(
                "somabrain_teach_r_user", "Teach-derived r_user values"
            )
            if metrics
            else None
        )
        self._mx_reward_ok = (
            metrics.get_counter(
                "somabrain_reward_events_published_total",
                "Reward events successfully published",
            )
            if metrics
            else None
        )
        self._mx_reward_fail = (
            metrics.get_counter(
                "somabrain_reward_events_failed_total", "Reward events publish failures"
            )
            if metrics
            else None
        )

    def _ensure_clients(self) -> None:
        # confluent-kafka required; create producer
        if self._ck_producer is None and CKProducer is not None:
            try:
                import logging

                logging.info(
                    "teach_feedback_processor: creating ck-producer bootstrap=%s",
                    self._bootstrap,
                )
            except Exception:
                pass
            self._ck_producer = CKProducer(
                {
                    "bootstrap.servers": self._bootstrap,
                    "socket.timeout.ms": 5000,
                    "message.timeout.ms": 5000,
                    # Avoid requiring python-snappy in host tools; keep interop simple
                    "compression.type": "none",
                }
            )
        # No kafka-python fallback in strict mode

    def _emit_reward(self, frame_id: str, r_user: float) -> None:
        try:
            import logging

            logging.debug("teach_feedback_processor: _emit_reward called")
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
        # Use confluent-kafka producer only
        if self._ck_producer is not None:
            try:
                import logging

                logging.info("teach_feedback_processor: using confluent-kafka producer")
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
                        import logging

                        logging.info(
                            "teach_feedback_processor: emitted reward frame_id=%s r_user=%s",
                            frame_id,
                            r_user,
                        )
                    except Exception:
                        pass
                    if self._mx_reward_ok is not None:
                        try:
                            self._mx_reward_ok.inc()
                        except Exception:
                            pass
                else:
                    try:
                        import logging

                        logging.error(
                            "teach_feedback_processor: failed to emit via ck err=%s remaining=%s",
                            delivered.get("err"),
                            remaining,
                        )
                    except Exception:
                        pass
                    if self._mx_reward_fail is not None:
                        try:
                            self._mx_reward_fail.inc()
                        except Exception:
                            pass
            except Exception as e:
                try:
                    import logging

                    logging.error("teach_feedback_processor: ck-produce error: %s", e)
                except Exception:
                    pass
                if self._mx_reward_fail is not None:
                    try:
                        self._mx_reward_fail.inc()
                    except Exception:
                        pass
            return
        # Strict mode: if producer unavailable, treat as failure
        if self._mx_reward_fail is not None:
            try:
                self._mx_reward_fail.inc()
            except Exception:
                pass

    def run(self) -> None:  # pragma: no cover - integration loop
        self._ensure_clients()
        group_id = os.getenv("TEACH_PROC_GROUP", "teach-feedback-proc")
        # Use confluent-kafka consumer only (strict mode)
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
                            import logging

                            logging.error(
                                "teach_feedback_processor: consumer error (ck): %s", e
                            )
                        except Exception:
                            pass
                        time.sleep(0.25)
            finally:
                try:
                    c.close()
                except Exception:
                    pass
            return
        # If not available, raise hard error in strict mode
        raise RuntimeError("teach_feedback_processor: CKConsumer unavailable")

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
                import logging

                logging.debug(
                    "teach_feedback: frame_id=%s rating=%s -> r_user=%s",
                    frame_id,
                    rating,
                    r_user,
                )
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
    from somabrain.modes import feature_enabled
    if feature_enabled("teach_feedback"):
        # Require Kafka readiness before starting worker thread
        assert_ready(require_kafka=True, require_redis=False, require_postgres=False, require_opa=False)
        _thread = threading.Thread(target=_svc.run, daemon=True)
        _thread.start()


@app.get("/health")
async def health() -> Dict[str, Any]:
    from somabrain.modes import mode_config, feature_enabled
    return {"ok": True, "enabled": str(int(feature_enabled("teach_feedback"))), "mode": mode_config().name}


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
