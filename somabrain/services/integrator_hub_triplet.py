from __future__ import annotations
import json
import math
import os
import socket
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Callable
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from common.config.settings import settings
import somabrain.runtime_config as runtime_config
from confluent_kafka import Consumer, Producer, KafkaError
from fastavro import parse_schema, schemaless_writer
import somabrain.metrics as metrics
from somabrain.infrastructure import get_redis_url
import requests
from common.logging import logger
import redis
import io

"""Tripartite Integrator Hub.

Consumes predictor updates for state/agent/action domains, weights them by
confidence (exp(-alpha*error)), selects a leader, and emits a GlobalFrame
record. Uses Kafka + Avro; fails fast on missing dependencies.
"""



# Use the canonical settings import as per Vibe coding rules.

try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "confluent_kafka is required for integrator_hub_triplet; install the dependency."
    ) from exc

try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "fastavro is required for integrator_hub_triplet; install the dependency."
    ) from exc



def _load_schema(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return parse_schema(json.load(f))


_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA_PREDICTOR_UPDATE = _load_schema(
    os.path.join(_ROOT, "proto", "cog", "predictor_update.avsc")
)
SCHEMA_GLOBAL_FRAME = _load_schema(
    os.path.join(_ROOT, "proto", "cog", "global_frame.avsc")
)

# Metrics
INTEGRATOR_LEADER = metrics.get_counter(
    "somabrain_integrator_leader_total",
    "Integrator leader selections",
    labelnames=["leader"], )
INTEGRATOR_ERROR = metrics.get_histogram(
    "somabrain_integrator_error",
    "Integrator observed predictor error",
    labelnames=["domain"],
    buckets=[i / 10.0 for i in range(11)], )
INTEGRATOR_OPA_REJECT = metrics.get_counter(
    "somabrain_integrator_opa_reject_total",
    "Integrator leader vetoed by OPA",
    labelnames=["leader"], )
INTEGRATOR_REDIS_CACHE = metrics.get_counter(
    "somabrain_integrator_redis_cache_total",
    "Integrator writes to Redis cache",
    labelnames=["leader"], )


class IntegratorHub:
    """Consumes predictor updates and emits GlobalFrame."""

def __init__(
        self,
        alpha: Optional[float] = None,
        domains=None,
        topic_updates=None,
        topic_global: Optional[str] = None,
        bootstrap: Optional[str] = None,
        producer: Optional[object] = None,
        redis_client: Optional[object] = None,
        opa_request: Optional[Callable[[str, Dict[str, float]], bool]] = None,
        start_io: bool = True,
        start_health: bool = True, ):
            pass
        ss = settings
        # Alpha/temperature/flag are re-read at runtime (see _effective_cfg)
        if alpha is None:
            alpha = getattr(ss, "predictor_alpha", 2.0)
        self.alpha = float(alpha)
        self.domains = domains or ["state", "agent", "action"]
        self._initial_temperature = float(
            getattr(ss, "integrator_softmax_temperature", 1.0)
        )
        self._initial_enable_flag = bool(getattr(ss, "enable_cog_threads", False))
        self._initial_opa_url = (getattr(ss, "opa_url", "") or "").strip()
        # Determine Kafka bootstrap configuration. If external backends are not required,
        # we avoid configuring Kafka to prevent container crashes in local environments.
        if getattr(ss, "require_external_backends", False):
            # Use central settings for Kafka bootstrap; fallback to provided arg.
            self.bootstrap = bootstrap or ss.kafka_bootstrap_servers
        else:
            # When external backends are disabled, skip Kafka bootstrap configuration.
            self.bootstrap = None
        if not self.bootstrap:
            raise RuntimeError("Kafka bootstrap not configured for IntegratorHub.")
        self.topic_updates = topic_updates or {
            "state": getattr(ss, "topic_state_updates", "cog.state.updates"),
            "agent": getattr(ss, "topic_agent_updates", "cog.agent.updates"),
            "action": getattr(ss, "topic_action_updates", "cog.action.updates"),
        }
        self.topic_global = topic_global or getattr(
            ss, "topic_global_frame", "cog.global.frame"
        )
        self.consumer = None
        self.producer = producer
        # Initialise Kafka consumer/producer only when I/O is required and a bootstrap server is configured.
        if start_io and self.bootstrap:
            self.consumer = Consumer(
                {
                    "bootstrap.servers": self.bootstrap,
                    "group.id": "somabrain-integrator",
                    "enable.auto.commit": False,
                    "auto.offset.reset": "earliest",
                }
            )
            self.consumer.subscribe(list(self.topic_updates.values()))
            self.producer = producer or Producer({"bootstrap.servers": self.bootstrap})
        self._latest: Dict[str, Dict] = {}
        self._instance_id = socket.gethostname()
        self._redis_client = redis_client
        if self._redis_client is None:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                redis_url = get_redis_url()
                if redis_url:
                    pass

                    self._redis_client = redis.from_url(redis_url)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                self._redis_client = None
        self._opa_request = opa_request or self._default_opa_request
        # Health server
        self._health_port = int(getattr(ss, "integrator_health_port", 9015))
        self._health_thread = None
        if start_health:
            self._health_thread = threading.Thread(
                target=self._serve_health, name="integrator_health", daemon=True
            )
            self._health_thread.start()

def _serve_health(self) -> None:
        hub_ref = self

class _Handler(BaseHTTPRequestHandler):
    pass
def do_GET(self):  # type: ignore[override]
                if self.path not in ("/health", "/healthz", "/ready"):
                    self.send_response(404)
                    self.end_headers()
                    return
                # Liveness/ready: the process is running if we can answer; do not
                # fail health merely because no updates have been observed yet.
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                payload = {
                    "ok": bool(hub_ref._latest),
                    "domains": list(hub_ref._latest.keys()),
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))

def log_message(self, format, *args):  # noqa: N802
                return

        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            server = HTTPServer(("", self._health_port), _Handler)
            server.serve_forever()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Health server failed: {exc}") from exc

def _encode(self, record: Dict, schema) -> bytes:
    pass

        buf = io.BytesIO()
        schemaless_writer(buf, schema, record)
        return buf.getvalue()

def _effective_cfg(self) -> Dict[str, float | bool | str]:
        """Load current config, allowing runtime overrides via runtime_config."""

def _get_bool(key: str, default: bool) -> bool:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return runtime_config.get_bool(key, default)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return default

def _get_float(key: str, default: float) -> float:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return float(runtime_config.get_float(key, default))
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return default

def _get_str(key: str, default: str) -> str:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return str(runtime_config.get_str(key, default))
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                return default

        alpha = _get_float(
            "predictor_alpha", getattr(settings, "predictor_alpha", self.alpha)
        )
        temp = _get_float("integrator_temperature", self._initial_temperature)
        flag = _get_bool("enable_cog_threads", self._initial_enable_flag)
        opa_url = _get_str("opa_url", self._initial_opa_url).strip()
        return {"alpha": alpha, "temperature": temp, "enable": flag, "opa_url": opa_url}

def _select_leader(self) -> Optional[str]:
        if not set(self.domains).issubset(self._latest.keys()):
            return None
        cfg = self._effective_cfg()
        temperature = cfg["temperature"]
        # Precision-weighted softmax: w = exp(-alpha * error) or confidence fallback
        weights = {}
        for d in self.domains:
            rec = self._latest[d]
            err = rec.get("delta_error")
            if err is not None and math.isfinite(err):
                weights[d] = math.exp(-cfg["alpha"] * float(max(err, 0.0)))
            else:
                weights[d] = max(0.0, float(rec.get("confidence", 0.0)))
        if temperature <= 0:
            return max(weights.items(), key=lambda kv: kv[1])[0]
        max_w = max(weights.values())
        exps = {d: math.exp((w - max_w) / temperature) for d, w in weights.items()}
        total = sum(exps.values()) or 1.0
        probs = {d: v / total for d, v in exps.items()}
        return max(probs.items(), key=lambda kv: kv[1])[0]

def _publish_global(self, leader: str) -> None:
        cfg = self._effective_cfg()
        present = {d: self._latest[d] for d in self.domains if d in self._latest}
        if leader not in present:
            return
        weights = {}
        entropy = 0.0
        alpha = cfg["alpha"]
        for d, rec in present.items():
            err = rec.get("delta_error")
            if err is not None and math.isfinite(err):
                w = math.exp(-alpha * float(max(err, 0.0)))
                try:
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    INTEGRATOR_ERROR.labels(domain=d).observe(float(err))
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
            else:
                w = max(0.0, float(rec.get("confidence", 0.0)))
            weights[d] = w
        total_w = sum(weights.values()) or 1.0
        probs = {d: w / total_w for d, w in weights.items()}
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            entropy = -sum(p * math.log(p) for p in probs.values() if p > 0)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            entropy = 0.0
        now = datetime.now(timezone.utc).isoformat()
        frame = {
            "ts": now,
            "leader": leader,
            "weights": weights,
            "frame": {},
            "rationale": "tripartite-integrator",
            "leader_election": {
                "instance_id": self._instance_id,
                "election_time": now,
                "leader_tenure_seconds": 0.0,
                "min_dwell_ms": 0,
                "entropy_cap": float(
                    getattr(settings, "integrator_entropy_cap", 0.0) or 0.0
                ),
                "current_entropy": float(entropy),
                "dwell_satisfied": True,
                "transition_allowed": True,
            },
        }
        payload = self._encode(frame, SCHEMA_GLOBAL_FRAME)
        if self._redis_client:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                self._redis_client.setex(f"globalframe:{leader}", 300, payload)
                INTEGRATOR_REDIS_CACHE.labels(leader=leader).inc()
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
        opa_url = cfg["opa_url"]
        if opa_url:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                if not self._opa_request(
                    opa_url, {"leader": leader, "weights": weights}
                ):
                    INTEGRATOR_OPA_REJECT.labels(leader=leader).inc()
                    return
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                INTEGRATOR_OPA_REJECT.labels(leader=leader).inc()
                return
        self.producer.produce(self.topic_global, payload)
        self.producer.flush()

def _default_opa_request(self, url: str, context: Dict[str, float]) -> bool:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            resp = requests.post(url, json={"input": context}, timeout=1)
            if not resp.ok:
                return False
            return bool(resp.json().get("result", False))
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            return False

def run(self) -> None:  # pragma: no cover (I/O loop)
        if self.consumer is None:
            return
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(f"Kafka error: {msg.error()}")
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                record = json.loads(msg.value())
                domain = record.get("domain")
                if domain not in self.domains:
                    continue
                err = float(record.get("error_metric"))
                cfg = self._effective_cfg()
                conf = math.exp(-float(cfg["alpha"]) * max(0.0, err))
                INTEGRATOR_ERROR.labels(domain=domain).observe(err)
                self._latest[domain] = {
                    "error": err,
                    "confidence": conf,
                    "ts": record.get("ts"),
                }
                if cfg["enable"]:
                    leader = self._select_leader()
                    if leader:
                        INTEGRATOR_LEADER.labels(leader=leader).inc()
                        self._publish_global(leader)
                self.consumer.commit(msg)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
    raise RuntimeError(f"Failed to process predictor update: {exc}")


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------
# When the module is executed via ``python -m somabrain.services.integrator_hub_triplet``
# (as defined in the Docker compose ``command``), we want the process to stay
# alive and expose the health endpoint.  The original implementation only
# defined the ``IntegratorHub`` class without any side‑effects, causing the
# container to exit immediately after import.  This resulted in repeated
# restarts and failed health checks.
#
# The block below creates an ``IntegratorHub`` instance with ``start_io=False``
# so it does not attempt to connect to Kafka (respecting the ``require_external_backends``
# setting).  The health server is started automatically in ``__init__``.  We then
# keep the process alive with a simple sleep loop, allowing the health endpoint
# to be queried while avoiding unnecessary CPU usage.
if __name__ == "__main__":  # pragma: no cover
    hub = IntegratorHub(start_io=False)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        # Keep the process running so the health server remains reachable.
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        # Graceful shutdown on SIGINT / container stop.
