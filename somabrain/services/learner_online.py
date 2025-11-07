"""
Learner Online Service

Consumes reward events (and optionally future global frame / next events) and emits config
updates carrying exploration temperature (tau) and learning rate.

Policy (initial conservative mapping):
- Maintain EMA of reward.total per tenant with alpha LEARNER_EMA_ALPHA (default 0.2).
- Map EMA r in [0,1] to tau = clamp(0.1,1.0, 0.8 - 0.5*(r - 0.5)). Higher reward lowers exploration.
- Emit config update for every reward plus a periodic keep-alive (default period 30s).

Environment:
- SOMABRAIN_KAFKA_URL (bootstrap servers, may be kafka://host:port)
- LEARNER_EMA_ALPHA (default 0.2)
- LEARNER_EMIT_PERIOD (seconds, default 30)
- SOMABRAIN_DEFAULT_TENANT (fallback tenant label)
- SOMABRAIN_FF_LEARNER_ONLINE (enable flag) or ENABLE_COG_THREADS composite flag

Topics:
- Input:  cog.reward.events
- Output: cog.config.updates
  (Future reserved inputs: cog.global.frame, cog.next.events)

Serialization:
- If Avro schemas are available (reward_event, config_update) they are used.
- Otherwise falls back to JSON. (Config updates forced JSON for debugging if LEARNER_FORCE_JSON=1)
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

TOPIC_REWARD = "cog.reward.events"
TOPIC_CFG = "cog.config.updates"
TOPIC_GF = "cog.global.frame"
TOPIC_NEXT = "cog.next.events"


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
        self._serde_reward = _serde("reward_event")
        # Force JSON for config updates if LEARNER_FORCE_JSON set
        self._serde_cfg = None if os.getenv("LEARNER_FORCE_JSON", "").lower() in {"1","true","yes","on"} else _serde("config_update")
        self._ema_alpha = float(os.getenv("LEARNER_EMA_ALPHA", "0.2"))
        self._emit_period = float(os.getenv("LEARNER_EMIT_PERIOD", "30"))
        self._producer: Optional[KafkaProducer] = None
        self._stop = threading.Event()
        self._ema_by_tenant: Dict[str, _EMA] = {}
        # Metrics
        self._g_explore = metrics.get_gauge("soma_exploration_ratio", "Exploration ratio") if metrics else None
        self._g_regret = metrics.get_gauge("soma_policy_regret_estimate", "Estimated policy regret") if metrics else None

    def _ensure_producer(self) -> None:
        if KafkaProducer is None:
            raise RuntimeError("KafkaProducer unavailable")
        if self._producer is None:
            self._producer = KafkaProducer(bootstrap_servers=self._bootstrap, acks="1", linger_ms=5)
            print(f"learner_online: producer initialized bootstrap={self._bootstrap}")

    @staticmethod
    def _tau_from_reward(ema: float) -> float:
        try:
            r = max(0.0, min(1.0, float(ema)))
        except Exception:
            r = 0.5
        tau = 0.8 - 0.5 * (r - 0.5)
        return max(0.1, min(1.0, tau))

    def _emit_cfg(self, tenant: str, tau: float, lr: float = 0.05) -> None:
        if self._producer is None:
            return
        rec = {
            "tenant": tenant,
            "learning_rate": float(lr),
            "exploration_temp": float(tau),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            fut = self._producer.send(TOPIC_CFG, value=_enc(rec, self._serde_cfg))
            fut.get(timeout=5)
            self._producer.flush()
            print(f"learner_online: emitted config_update tenant={tenant} tau={tau:.3f} lr={lr:.3f}")
        except Exception as e:
            print(f"learner_online: emit failed {e}")

    def _observe_reward(self, ev: Dict[str, Any]) -> None:
        tenant = str(ev.get("tenant") or os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")).strip() or "public"
        total = float(ev.get("total", 0.0))
        ema = self._ema_by_tenant.setdefault(tenant, _EMA(self._ema_alpha)).update(total)
        tau = self._tau_from_reward(ema)
        print(f"learner_online: reward total={total:.3f} ema={ema:.3f} tau={tau:.3f} tenant={tenant}")
        try:
            if self._g_explore is not None:
                self._g_explore.set(tau / 1.0)
            if self._g_regret is not None:
                self._g_regret.set(max(0.0, 1.0 - ema))
        except Exception:
            pass
        self._emit_cfg(tenant, tau)

    def _handle_record(self, msg: Any) -> None:
        topic = getattr(msg, "topic", "") or ""
        payload = getattr(msg, "value", None)
        if topic == TOPIC_REWARD:
            ev = _dec(payload, self._serde_reward)
            if isinstance(ev, dict):
                self._observe_reward(ev)

    def run(self) -> None:
        if KafkaConsumer is None:
            raise RuntimeError("KafkaConsumer unavailable")
        self._ensure_producer()
        topics = [TOPIC_REWARD]
        if os.getenv("SOMABRAIN_FF_CONFIG_UPDATES", "1").lower() in {"1","true","yes","on"}:
            topics.append(TOPIC_GF)
        if os.getenv("SOMABRAIN_FF_NEXT_EVENT", "1").lower() in {"1","true","yes","on"}:
            topics.append(TOPIC_NEXT)
        consumer = KafkaConsumer(
            *topics,
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
                polled = consumer.poll(timeout_ms=500)
                if polled is None:
                    now = time.time()
                    if now - last_emit >= self._emit_period:
                        last_emit = now
                        self._emit_cfg(os.getenv("SOMABRAIN_DEFAULT_TENANT", "public"), 0.7)
                    continue
                if isinstance(polled, dict):
                    for tp, records in polled.items():
                        for rec in records:
                            self._handle_record(rec)
                else:
                    self._handle_record(polled)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()


app = FastAPI(title="Learner Online")
_svc = LearnerService()
_thread: Optional[threading.Thread] = None


@app.on_event("startup")
async def startup() -> None:  # pragma: no cover
    global _thread
    ff = os.getenv("SOMABRAIN_FF_LEARNER_ONLINE", "0").strip().lower() in {"1","true","yes","on"}
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in {"1","true","yes","on"}
    if not (ff or composite):
        return
    _thread = threading.Thread(target=_svc.run, daemon=True)
    _thread.start()


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "enabled": os.getenv("SOMABRAIN_FF_LEARNER_ONLINE", "0")}


@app.get("/metrics")
async def metrics_ep():  # type: ignore
    try:
        from somabrain import metrics as _m  # type: ignore
        return await _m.metrics_endpoint()
    except Exception:
        return {"status": "metrics not available"}


def main() -> None:  # pragma: no cover
    port = int(os.getenv("LEARNER_ONLINE_PORT", "8084"))
    try:
        import uvicorn  # type: ignore
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception:
        while True:
            time.sleep(60)


if __name__ == "__main__":  # pragma: no cover
    main()
