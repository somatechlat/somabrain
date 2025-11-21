"""Tripartite Integrator Hub.

Consumes predictor updates for state/agent/action domains, weights them by
confidence (exp(-alpha*error)), selects a leader, and emits a GlobalFrame
record. Uses Kafka + Avro; fails fast on missing dependencies.
"""

from __future__ import annotations

import json
import math
import os
import socket
import time
from datetime import datetime, timezone
from typing import Dict, Optional
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from common.config.settings import settings as shared_settings

try:
    from confluent_kafka import Consumer, Producer, KafkaError
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "confluent_kafka is required for integrator_hub_triplet; install the dependency."
    ) from exc

try:
    from fastavro import parse_schema, schemaless_writer
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "fastavro is required for integrator_hub_triplet; install the dependency."
    ) from exc

import somabrain.metrics as metrics


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
    labelnames=["leader"],
)
INTEGRATOR_ERROR = metrics.get_histogram(
    "somabrain_integrator_error",
    "Integrator observed predictor error",
    labelnames=["domain"],
    buckets=[i / 10.0 for i in range(11)],
)


class IntegratorHub:
    """Consumes predictor updates and emits GlobalFrame."""

    def __init__(
        self,
        alpha: float = 2.0,
        domains=None,
        topic_updates=None,
        topic_global: Optional[str] = None,
        bootstrap: Optional[str] = None,
    ):
        self.alpha = float(alpha)
        self.domains = domains or ["state", "agent", "action"]
        ss = shared_settings
        self.bootstrap = (
            bootstrap
            or (ss.kafka_bootstrap_servers if ss else None)
            or os.getenv("SOMABRAIN_KAFKA_URL")
        )
        if not self.bootstrap:
            raise RuntimeError("Kafka bootstrap not configured for IntegratorHub.")
        self.topic_updates = topic_updates or {
            "state": os.getenv("SOMABRAIN_TOPIC_STATE_UPDATES", "cog.state.updates"),
            "agent": os.getenv("SOMABRAIN_TOPIC_AGENT_UPDATES", "cog.agent.updates"),
            "action": os.getenv("SOMABRAIN_TOPIC_ACTION_UPDATES", "cog.action.updates"),
        }
        self.topic_global = topic_global or os.getenv(
            "SOMABRAIN_TOPIC_GLOBAL_FRAME", "cog.global.frame"
        )
        self.consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap,
                "group.id": "somabrain-integrator",
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }
        )
        self.consumer.subscribe(list(self.topic_updates.values()))
        self.producer = Producer({"bootstrap.servers": self.bootstrap})
        self._latest: Dict[str, Dict] = {}
        self._instance_id = socket.gethostname()
        # Health server
        self._health_port = int(os.getenv("SOMABRAIN_INTEGRATOR_HEALTH_PORT", "9015"))
        self._health_thread = threading.Thread(
            target=self._serve_health, name="integrator_health", daemon=True
        )
        self._health_thread.start()

    def _serve_health(self) -> None:
        hub_ref = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # type: ignore[override]
                if self.path not in ("/health", "/healthz", "/ready"):
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200 if hub_ref._latest else 503)
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
            server = HTTPServer(("", self._health_port), _Handler)
            server.serve_forever()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Health server failed: {exc}") from exc

    def _encode(self, record: Dict, schema) -> bytes:
        import io

        buf = io.BytesIO()
        schemaless_writer(buf, schema, record)
        return buf.getvalue()

    def _select_leader(self) -> Optional[str]:
        if set(self.domains).issubset(self._latest.keys()):
            # Choose highest confidence
            leader = max(self.domains, key=lambda d: self._latest[d]["confidence"])
            return leader
        return None

    def _publish_global(self, leader: str) -> None:
        weights = {d: float(self._latest[d]["confidence"]) for d in self.domains}
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
                "entropy_cap": 0.0,
                "current_entropy": 0.0,
                "dwell_satisfied": True,
                "transition_allowed": True,
            },
        }
        payload = self._encode(frame, SCHEMA_GLOBAL_FRAME)
        self.producer.produce(self.topic_global, payload)
        self.producer.flush()

    def run(self) -> None:  # pragma: no cover (I/O loop)
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(f"Kafka error: {msg.error()}")
            try:
                record = json.loads(msg.value())
                domain = record.get("domain")
                if domain not in self.domains:
                    continue
                err = float(record.get("error_metric"))
                conf = math.exp(-self.alpha * max(0.0, err))
                INTEGRATOR_ERROR.labels(domain=domain).observe(err)
                self._latest[domain] = {
                    "error": err,
                    "confidence": conf,
                    "ts": record.get("ts"),
                }
                leader = self._select_leader()
                if leader:
                    INTEGRATOR_LEADER.labels(leader=leader).inc()
                    self._publish_global(leader)
                self.consumer.commit(msg)
            except Exception as exc:
                raise RuntimeError(f"Failed to process predictor update: {exc}")
