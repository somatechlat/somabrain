"""
Learner Online Service (minimal real implementation)

Consumes:
- cog.global.frame (context proxy)
- cog.reward.events (RewardEvent)
- cog.next.events (optional; not strictly required)

Produces:
- cog.config.updates (ConfigUpdate with exploration_temp, learning_rate)

Algorithm (conservative initial policy):
- Maintain an exponential moving average of reward.total per tenant.
- Map EMA to temperature: tau = clamp(0.1, 1.0, 0.8 - 0.5*(ema-0.5)).
- Emit ConfigUpdate on reward updates or every N seconds.

Environment:
- SOMABRAIN_KAFKA_URL
- LEARNER_EMA_ALPHA (default 0.2)
- LEARNER_EMIT_PERIOD (seconds, default 30)

Metrics:
- soma_exploration_ratio (gauge) approximated by normalized tau
- soma_policy_regret_estimate (gauge) = max(0, 1 - ema)
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


TOPIC_GF = "cog.global.frame"
TOPIC_REWARD = "cog.reward.events"
TOPIC_NEXT = "cog.next.events"
TOPIC_CFG = "cog.config.updates"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _serde(schema_name: str) -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema(schema_name))  # type: ignore[arg-type]
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


class _EMA:
    def __init__(self, alpha: float) -> None:
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.v: Optional[float] = None

    def update(self, x: float) -> float:
        if self.v is None:
            self.v = float(x)
        else:
            self.v = self.alpha * float(x) + (1 - self.alpha) * self.v
        return self.v

    def get(self) -> Optional[float]:
        return self.v


class LearnerService:
    def __init__(self) -> None:
        self._bootstrap = _bootstrap()
        self._serde_cfg = _serde("config_update")
        self._serde_reward = _serde("reward_event")
        self._ema_alpha = float(os.getenv("LEARNER_EMA_ALPHA", "0.2"))
        self._emit_period = float(os.getenv("LEARNER_EMIT_PERIOD", "30"))
        self._ema_by_tenant: Dict[str, _EMA] = {}
        self._producer: Optional[KafkaProducer] = None
        self._stop = threading.Event()
        # Metrics
        self._g_explore = metrics.get_gauge("soma_exploration_ratio", "Exploration ratio") if metrics else None
        self._g_regret = metrics.get_gauge("soma_policy_regret_estimate", "Estimated policy regret") if metrics else None

    def _ensure_clients(self) -> None:
        if KafkaConsumer is None or KafkaProducer is None:
            raise RuntimeError("Kafka client not available")
        if self._producer is None:
            self._producer = KafkaProducer(bootstrap_servers=self._bootstrap, acks="1", linger_ms=5)

    def _emit_cfg(self, tenant: str, tau: float, lr: float = 0.05) -> None:
        if self._producer is None:
            return
        rec = {
            "learning_rate": float(lr),
            "exploration_temp": float(tau),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            self._producer.send(TOPIC_CFG, value=_enc(rec, self._serde_cfg))
        except Exception:
            pass

    @staticmethod
    def _tau_from_reward(ema: float) -> float:
        # Map reward EMA in [0,1] to tau in [0.1,1.0]; higher reward -> lower exploration
        try:
            r = max(0.0, min(1.0, float(ema)))
        except Exception:
            r = 0.5
        tau = 0.8 - 0.5 * (r - 0.5)
        return max(0.1, min(1.0, float(tau)))

    def _observe_reward(self, ev: Dict[str, Any]) -> None:
        tenant = str(ev.get("tenant") or os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")).strip() or "public"
        total = float(ev.get("total", 0.0))
        ema = self._ema_by_tenant.setdefault(tenant, _EMA(self._ema_alpha)).update(total)
        tau = self._tau_from_reward(ema)
        # Metrics update
        try:
            if self._g_explore is not None:
                self._g_explore.set(tau / 1.0)
            if self._g_regret is not None:
                self._g_regret.set(max(0.0, 1.0 - ema))
        except Exception:
            pass
        self._emit_cfg(tenant, tau)

    def run(self) -> None:  # pragma: no cover - integration loop
        self._ensure_clients()
        consumer = KafkaConsumer(
            TOPIC_GF,
            TOPIC_REWARD,
            TOPIC_NEXT,
            bootstrap_servers=self._bootstrap,
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=os.getenv("SOMABRAIN_CONSUMER_GROUP", "learner-online"),
            consumer_timeout_ms=1000,
        )
        last_emit = time.time()
        try:
            while not self._stop.is_set():
                msg = consumer.poll(timeout_ms=500)
                if msg is None:
                    # periodic emit (keep-alive)
                    now = time.time()
                    if now - last_emit >= self._emit_period:
                        last_emit = now
                        # Emit conservative default
                        self._emit_cfg(os.getenv("SOMABRAIN_DEFAULT_TENANT", "public"), 0.7)
                    continue
                # kafka-python poll returns dict in some versions; guard
                if isinstance(msg, dict):
                    for tp, records in msg.items():
                        for rec in records:
                            self._handle_record(rec)
                else:
                    # single message
                    self._handle_record(msg)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    def _handle_record(self, msg: Any) -> None:
        topic = getattr(msg, "topic", "") or ""
        payload = getattr(msg, "value", None)
        if topic == TOPIC_REWARD:
            ev = _dec(payload, self._serde_reward)
            if isinstance(ev, dict):
                self._observe_reward(ev)
        # GlobalFrame/NextEvent currently unused by the conservative learner; reserved for future features

    def stop(self) -> None:
        self._stop.set()


app = FastAPI(title="Learner Online")
_svc = LearnerService()
_thread: Optional[threading.Thread] = None


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    global _thread
    _thread = threading.Thread(target=_svc.run, daemon=True)
    _thread.start()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True}


def main() -> None:  # pragma: no cover
    port = int(os.getenv("LEARNER_ONLINE_PORT", "8084"))
    try:
        import uvicorn  # type: ignore

        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception:
        # Keep thread alive even if HTTP cannot start
        while True:
            time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    main()
