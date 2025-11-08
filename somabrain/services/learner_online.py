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

import yaml

from fastapi import FastAPI

try:
    from confluent_kafka import Producer as CfProducer  # type: ignore
    from confluent_kafka import Consumer as CfConsumer  # type: ignore
    from confluent_kafka.admin import AdminClient as CfAdminClient, NewTopic as CfNewTopic  # type: ignore
except Exception:  # pragma: no cover
    CfProducer = None  # type: ignore
    CfConsumer = None  # type: ignore
    CfAdminClient = None  # type: ignore
    CfNewTopic = None  # type: ignore

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

TOPIC_REWARD = os.getenv("SOMABRAIN_TOPIC_REWARD_EVENTS", "cog.reward.events")
TOPIC_CFG = os.getenv("SOMABRAIN_TOPIC_CONFIG_UPDATES", "cog.config.updates")
TOPIC_GF = os.getenv("SOMABRAIN_TOPIC_GLOBAL_FRAME", "cog.global.frame")
TOPIC_NEXT = os.getenv("SOMABRAIN_TOPIC_NEXT_EVENTS", "cog.next.events")


def _bootstrap() -> str:
    # Prefer in-network bootstrap set by compose/k8s, then fall back to SOMABRAIN_KAFKA_URL
    url = (
        os.getenv("SOMA_KAFKA_BOOTSTRAP")
        or os.getenv("SOMABRAIN_KAFKA_URL")
        or "somabrain_kafka:9092"
    )
    return url.replace("kafka://", "")


def _serde(name: str) -> Optional[AvroSerde]:
    # Prefer Avro serde, but fall back to JSON when the in-repo `libs`
    # package (or serde) is not available. This prevents the learner
    # process from crashing in minimal dev images where `libs/` wasn't
    # copied into the container build.
    if load_schema is None or AvroSerde is None:
        print(
            f"learner_online: Avro serde not available for {name}, falling back to JSON"
        )
        return None
    try:
        return AvroSerde(load_schema(name))  # type: ignore[arg-type]
    except Exception as e:
        print(
            f"learner_online: avro serde load failed for {name}, falling back to JSON: {e}"
        )
        return None


def _enc(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def _dec(
    payload: Optional[bytes], serde: Optional[AvroSerde]
) -> Optional[Dict[str, Any]]:
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
        # Require Avro serde for config updates (no JSON fallback)
        self._serde_cfg = _serde("config_update")
        # Optional serde for next‑event (fallback to JSON if Avro missing)
        self._serde_next = _serde("next_event")
        # Load per‑tenant adaptation overrides (tau decay, entropy cap)
        self._tenant_overrides: Dict[str, Dict[str, Any]] = {}
        try:
            # Support both historic and current env var names.
            cfg_path = (
                os.getenv("SOMABRAIN_LEARNING_TENANTS_FILE")
                or os.getenv("LEARNING_TENANTS_CONFIG")
                or "config/learning.tenants.yaml"
            )
            with open(cfg_path, "r", encoding="utf-8") as f:
                self._tenant_overrides = yaml.safe_load(f) or {}
        except Exception:
            # If the file is missing or malformed, fall back to empty overrides.
            self._tenant_overrides = {}
        self._ema_alpha = float(os.getenv("LEARNER_EMA_ALPHA", "0.2"))
        self._emit_period = float(os.getenv("LEARNER_EMIT_PERIOD", "30"))
        self._producer: Optional[Any] = None
        self._producer_mode: str = ""
        self._stop = threading.Event()
        self._ema_by_tenant: Dict[str, _EMA] = {}
        # Metrics
        self._g_explore = (
            metrics.get_gauge("soma_exploration_ratio", "Exploration ratio")
            if metrics
            else None
        )
        self._g_regret = (
            metrics.get_gauge("soma_policy_regret_estimate", "Estimated policy regret")
            if metrics
            else None
        )
        # Gauge for regret derived from next_event confidence (1 - confidence)
        self._g_next_regret = (
            metrics.get_gauge(
                "soma_next_event_regret", "Regret derived from next_event confidence"
            )
            if metrics
            else None
        )
        self._topic_checked = False

    def _print_effective_config(self) -> None:
        try:
            # Reflect current effective learner + Kafka settings (no secrets)
            def _f(name: str, default: str) -> float:
                try:
                    return float(os.getenv(name, default))
                except Exception:
                    return float(default)

            cfg = {
                "bootstrap": self._bootstrap,
                "producer_mode": self._producer_mode or "unknown",
                "topics": {
                    "reward": TOPIC_REWARD,
                    "config": TOPIC_CFG,
                    "global_frame": TOPIC_GF,
                    "next": TOPIC_NEXT,
                },
                "ema_alpha": self._ema_alpha,
                "emit_period_s": self._emit_period,
                "tau_min": _f("LEARNER_TAU_MIN", "0.1"),
                "tau_max": _f("LEARNER_TAU_MAX", "1.0"),
                "default_lr": _f("LEARNER_DEFAULT_LR", "0.05"),
                "keepalive_tau": _f("LEARNER_KEEPALIVE_TAU", "0.7"),
                "serde": {
                    "reward": "avro" if self._serde_reward else "json",
                    "config": "avro" if self._serde_cfg else "json",
                },
                "flags": {
                    "FF_LEARNER_ONLINE": os.getenv("SOMABRAIN_FF_LEARNER_ONLINE", "0"),
                    "FF_NEXT_EVENT": os.getenv("SOMABRAIN_FF_NEXT_EVENT", "0"),
                    "FF_CONFIG_UPDATES": os.getenv("SOMABRAIN_FF_CONFIG_UPDATES", "0"),
                },
            }
            print("learner_online: effective_config " + json.dumps(cfg, sort_keys=True))
        except Exception:
            # Never fail the process due to config printing
            pass

    def _ensure_producer(self) -> None:
        if self._producer is None:
            if CfProducer is None:
                raise RuntimeError(
                    "confluent-kafka Producer required for learner_online"
                )
            conf = {
                "bootstrap.servers": self._bootstrap,
                "socket.timeout.ms": 10000,
                "message.send.max.retries": 1,
                "queue.buffering.max.ms": 50,
            }
            self._producer = CfProducer(conf)
            self._producer_mode = "confluent"
            print(
                f"learner_online: confluent producer initialized bootstrap={self._bootstrap}"
            )

    def _ensure_topic(self) -> None:
        if self._topic_checked:
            return
        self._topic_checked = True
        if CfAdminClient is None or CfNewTopic is None:
            print(
                "learner_online: confluent AdminClient unavailable, skipping topic ensure"
            )
            return
        try:
            admin = CfAdminClient({"bootstrap.servers": self._bootstrap})
            md = admin.list_topics(timeout=5)
            existing = set(md.topics.keys()) if md and hasattr(md, "topics") else set()
            # Ensure config updates topic exists
            if TOPIC_CFG not in existing:
                print(f"learner_online: creating missing topic {TOPIC_CFG}")
                newt = CfNewTopic(TOPIC_CFG, num_partitions=1, replication_factor=1)
                fs = admin.create_topics([newt])
                for _, f in fs.items():
                    try:
                        f.result(timeout=10)
                    except Exception as e:
                        print(f"learner_online: create topic failed {e}")
            else:
                print(f"learner_online: topic {TOPIC_CFG} already exists")
            # Ensure next‑event topic exists (optional, only if flag enabled)
            if os.getenv("SOMABRAIN_FF_NEXT_EVENT", "1").lower() in {"1", "true", "yes", "on"}:
                if TOPIC_NEXT not in existing:
                    print(f"learner_online: creating missing topic {TOPIC_NEXT}")
                    newt = CfNewTopic(TOPIC_NEXT, num_partitions=1, replication_factor=1)
                    fs = admin.create_topics([newt])
                    for _, f in fs.items():
                        try:
                            f.result(timeout=10)
                        except Exception as e:
                            print(f"learner_online: create next topic failed {e}")
                else:
                    print(f"learner_online: topic {TOPIC_NEXT} already exists")
        except Exception as e:
            print(f"learner_online: topic ensure failed {repr(e)}")

    def _tau_from_reward(self, ema: float) -> float:
        try:
            r = max(0.0, min(1.0, float(ema)))
        except Exception:
            r = 0.5
        tau = 0.8 - 0.5 * (r - 0.5)
        tmin = float(os.getenv("LEARNER_TAU_MIN", "0.1"))
        tmax = float(os.getenv("LEARNER_TAU_MAX", "1.0"))
        return max(tmin, min(tmax, tau))

    def _emit_cfg(self, tenant: str, tau: float, lr: Optional[float] = None) -> None:
        if self._producer is None:
            return
        if lr is None:
            try:
                lr = float(os.getenv("LEARNER_DEFAULT_LR", "0.05"))
            except Exception:
                lr = 0.05
        # Apply per‑tenant tau decay if configured
        decay = (
            float(self._tenant_overrides.get(tenant, {}).get("tau_decay_rate", 0.0))
        )
        if decay:
            # Decay is multiplicative: tau = tau * (1 - decay)
            tau = max(0.0, tau * (1.0 - decay))
        # Simple entropy‑cap placeholder: if an entropy_cap is set, ensure tau does not exceed it.
        # In a full implementation this would compute Shannon entropy of the weight vector.
        entropy_cap = self._tenant_overrides.get(tenant, {}).get("entropy_cap")
        if entropy_cap is not None:
            try:
                cap_val = float(entropy_cap)
                if tau > cap_val:
                    tau = cap_val
            except Exception:
                pass
        rec = {
            "tenant": tenant,
            "learning_rate": float(lr),
            "exploration_temp": float(tau),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            start = time.time()
            payload = _enc(rec, self._serde_cfg)
            # confluent-kafka produce + flush
            delivered = {"ok": False}

            def _cb(err, msg):
                if err is None:
                    delivered["ok"] = True
                    print(
                        f"learner_online: emitted config_update tenant={tenant} tau={tau:.3f} lr={lr:.3f} part={msg.partition()} off={msg.offset()}"
                    )
                else:
                    print(f"learner_online: delivery error {err}")

            self._producer.produce(TOPIC_CFG, payload, callback=_cb)
            self._producer.flush(15)
            dur_ms = (time.time() - start) * 1000.0
            if not delivered["ok"]:
                print(
                    f"learner_online: emit failed delivery-timeout tenant={tenant} tau={tau:.3f} ms={dur_ms:.1f}"
                )
        except Exception as e:
            print(
                f"learner_online: emit failed {repr(e)} tenant={tenant} tau={tau:.3f}"
            )

    def _observe_reward(self, ev: Dict[str, Any]) -> None:
        tenant = (
            str(
                ev.get("tenant") or os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
            ).strip()
            or "public"
        )
        total = float(ev.get("total", 0.0))
        ema = self._ema_by_tenant.setdefault(tenant, _EMA(self._ema_alpha)).update(
            total
        )
        tau = self._tau_from_reward(ema)
        print(
            f"learner_online: reward total={total:.3f} ema={ema:.3f} tau={tau:.3f} tenant={tenant}"
        )
        try:
            if self._g_explore is not None:
                self._g_explore.set(tau / 1.0)
            if self._g_regret is not None:
                self._g_regret.set(max(0.0, 1.0 - ema))
        except Exception:
            pass
        self._emit_cfg(tenant, tau)

    def _observe_next_event(self, ev: Dict[str, Any]) -> None:
        """Process a NextEvent record.

        The current simple regret definition is ``1 - confidence`` (range 0‑1).
        The value is logged and exposed via the ``soma_next_event_regret`` gauge.
        Future work can feed this regret into the EMA‑based tau calculation.
        """
        tenant = (
            str(ev.get("tenant") or os.getenv("SOMABRAIN_DEFAULT_TENANT", "public"))
            .strip()
            or "public"
        )
        confidence = float(ev.get("confidence", 0.0))
        regret = max(0.0, min(1.0, 1.0 - confidence))
        print(
            f"learner_online: next_event tenant={tenant} confidence={confidence:.3f} regret={regret:.3f}"
        )
        if self._g_next_regret is not None:
            try:
                self._g_next_regret.set(regret)
            except Exception:
                pass

    def _handle_record(self, msg: Any) -> None:
        topic = getattr(msg, "topic", "") or ""
        payload = getattr(msg, "value", None)
        if topic == TOPIC_REWARD:
            ev = _dec(payload, self._serde_reward)
            if isinstance(ev, dict):
                self._observe_reward(ev)
        elif topic == TOPIC_NEXT:
            ev = _dec(payload, self._serde_next)
            if isinstance(ev, dict):
                self._observe_next_event(ev)
        elif topic == TOPIC_NEXT:
            ev = _dec(payload, self._serde_next)
            if isinstance(ev, dict):
                # For now we only log the next‑event; future logic can use it for regret estimation
                print(f"learner_online: received next_event {ev}")

    def run(self) -> None:
        if CfConsumer is None:
            raise RuntimeError("confluent-kafka Consumer required for learner_online")
        self._ensure_producer()
        self._ensure_topic()
        self._print_effective_config()
        topics = [TOPIC_REWARD]
        if os.getenv("SOMABRAIN_FF_CONFIG_UPDATES", "1").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            topics.append(TOPIC_GF)
        if os.getenv("SOMABRAIN_FF_NEXT_EVENT", "1").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            topics.append(TOPIC_NEXT)
        # Use confluent_kafka.Consumer
        conf = {
            "bootstrap.servers": self._bootstrap,
            "group.id": os.getenv("SOMABRAIN_CONSUMER_GROUP", "learner-online"),
            "auto.offset.reset": "latest",
        }
        consumer = CfConsumer(conf)
        consumer.subscribe(topics)
        last_emit = time.time()
        try:
            while not self._stop.is_set():
                msg = consumer.poll(timeout=0.5)
                if msg is None:
                    now = time.time()
                    if now - last_emit >= self._emit_period:
                        last_emit = now
                        try:
                            ktau = float(os.getenv("LEARNER_KEEPALIVE_TAU", "0.7"))
                        except Exception:
                            ktau = 0.7
                        self._emit_cfg(
                            os.getenv("SOMABRAIN_DEFAULT_TENANT", "public"), ktau
                        )
                    continue
                if msg.error():
                    # skip errors but log
                    try:
                        err = msg.error()
                        print(f"learner_online: consumer error {err}")
                    except Exception:
                        pass
                    continue

                # build a small adapter message with .topic and .value to reuse handler
                class _MsgAdapter:
                    def __init__(self, m):
                        self._m = m

                    @property
                    def topic(self):
                        return self._m.topic()

                    @property
                    def value(self):
                        return self._m.value()

                self._handle_record(_MsgAdapter(msg))
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
    ff = os.getenv("SOMABRAIN_FF_LEARNER_ONLINE", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
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
