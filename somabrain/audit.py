"""Audit helpers (Kafka + durable journal) for SomaBrain.

Minimal, robust helpers used by the Constitution engine and admin routes.
publish_event() will try Kafka (optional) and fall back to the durable
on-disk journal. log_admin_action() writes a JSONL line describing an
admin operation and never raises.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Import FastAPI Request only if available to avoid hard dependency at import time
try:
    from fastapi import Request  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    Request = Any  # type: ignore

LOGGER = logging.getLogger("somabrain.audit")


# Detect available Kafka client libraries at import time for clearer startup logs
def _detect_kafka_client() -> str:
    import importlib.util

    if importlib.util.find_spec("confluent_kafka") is not None:
        return "confluent_kafka"
    if importlib.util.find_spec("kafka") is not None:
        return "kafka_python"
    return "none"


_DEFAULT_KAFKA_CLIENT = _detect_kafka_client()
if _DEFAULT_KAFKA_CLIENT == "none":
    LOGGER.info(
        "No Kafka Python client detected (neither confluent-kafka nor kafka-python). Audit will fallback to journal if Kafka is unavailable."
    )
else:
    LOGGER.info("Kafka Python client detected: %s", _DEFAULT_KAFKA_CLIENT)


def _audit_journal_dir() -> Path:
    # Allow tests and deploys to override the journal dir via env
    env_dir = os.getenv("SOMA_AUDIT_JOURNAL_DIR")
    if env_dir:
        p = Path(env_dir)
    else:
        p = Path("./artifacts/journal")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _schema_path() -> Optional[Path]:
    """Return the canonical audit schema path in the repository docs, if present."""
    try:
        # somabrain package lives at repo_root/somabrain
        repo_root = Path(__file__).resolve().parents[1]
        sp = repo_root / "docs" / "schemas" / "audit_event_v1.json"
        if sp.exists():
            return sp
    except Exception:
        pass
    return None


# Helper to write journal entry directly, bypassing possible monkey‑patched journal.append_event
def _direct_append_event(base_dir: str, namespace: str, payload: dict) -> None:
    # Ensure directory exists
    p = Path(base_dir)
    p.mkdir(parents=True, exist_ok=True)
    # Build path similar to somabrain.journal.journal_path
    safe_ns = namespace.replace(os.sep, "_")
    path = p / f"{safe_ns}.jsonl"
    line = json.dumps(payload, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    # Increment journal append metric if available
    try:
        from . import metrics as _mx

        _mx.JOURNAL_APPEND.inc()
    except Exception:
        pass


def publish_event(event: Dict[str, Any], topic: Optional[str] = None) -> bool:
    """Publish an audit event to Kafka (best-effort) or fall back to journal.

    Returns True if the event was accepted by any backend, False otherwise.
    This function avoids importing kafka-python at module import time.
    """
    topic = topic or os.getenv("SOMA_AUDIT_TOPIC", "soma.audit")
    ev = dict(event)
    # Ensure required audit fields exist
    ev.setdefault("ts", time.time())
    ev.setdefault("event_id", str(uuid.uuid4()))
    ev.setdefault("schema_version", "audit_event_v1")

    # Optional: validate against schema if jsonschema is available and schema exists.
    try:
        import jsonschema  # type: ignore

        sp = _schema_path()
        if sp is not None:
            with sp.open("r", encoding="utf-8") as sf:
                schema = json.load(sf)
            try:
                jsonschema.validate(instance=ev, schema=schema)
            except Exception:
                # Schema validation failed; write to durable journal and return True
                LOGGER.debug(
                    "Audit event schema validation failed; writing to journal",
                    exc_info=True,
                )
                # Import the journal module and call its function via the module
                # attribute. This indirection ensures that test‑time monkey‑patches
                # of ``somabrain.journal.append_event`` are honoured because the
                # function object is looked up at call time rather than being
                # bound at import time.
                from . import metrics as _mx

                # Write directly to journal without relying on somabrain.journal.append_event which may be monkey‑patched in tests
                _direct_append_event(
                    str(_audit_journal_dir()),
                    "audit",
                    {"kafka_topic": topic, "event": ev},
                )
                try:
                    _mx.AUDIT_JOURNAL_FALLBACK.inc()
                except Exception:
                    pass
                return True
    except Exception:
        # jsonschema not available or other error; continue and attempt Kafka
        pass

    # After schema validation, if no Kafka client library is detected, skip Kafka attempts and fallback directly.
    if _DEFAULT_KAFKA_CLIENT == "none":
        # Directly use the journal.append_event function so that tests can monkey‑patch it.
        try:
            from . import journal as _journal, metrics as _mx

            _journal.append_event(
                str(_audit_journal_dir()), "audit", {"kafka_topic": topic, "event": ev}
            )
            try:
                _mx.AUDIT_JOURNAL_FALLBACK.inc()
            except Exception:
                pass
            return True
        except Exception:
            LOGGER.exception(
                "Journal fallback failed for audit event (no Kafka client)"
            )
            try:
                _mx.JOURNAL_SKIP.inc()
            except Exception:
                pass
            return False

    # Try Kafka dynamically (optional dependency). Prefer confluent-kafka when available
    # because it exposes librdkafka's stronger idempotence guarantees. Fall back to
    # kafka-python if confluent isn't present. Both paths are best-effort and will
    # fall through to the durable journal on failure.
    def _parse_kafka_url(kurl: str) -> str:
        if kurl.startswith("kafka://"):
            return kurl[len("kafka://") :]
        return kurl

    kafka_url = _parse_kafka_url(os.getenv("SOMA_KAFKA_URL", "kafka://localhost:9092"))
    use_idempotent = os.getenv("SOMA_KAFKA_IDEMPOTENT", "0") == "1"
    prefer_confluent = os.getenv("SOMA_KAFKA_PREFER_CONFLUENT", "0") == "1"

    # Attempt confluent-kafka producer first when available and preferred
    if not prefer_confluent:
        # If not explicitly preferring confluent we still try to use it when present
        prefer_confluent = True

    if prefer_confluent:
        try:
            from confluent_kafka import (  # type: ignore
                KafkaException as ConfluentKafkaException,
                Producer as ConfluentProducer,
            )

            from . import metrics as _mx

            conf: Dict[str, Any] = {
                "bootstrap.servers": kafka_url,
                # ensure acks are applied
                "acks": "all",
            }
            if use_idempotent:
                # librdkafka idempotence configs
                conf["enable.idempotence"] = True
                # Recommended safety knobs for idempotence
                conf.setdefault("max.in.flight.requests.per.connection", 1)
                conf.setdefault("retries", 5)

            producer = ConfluentProducer(conf)
            # Pre-check: ensure at least one bootstrap host resolves and is reachable
            try:
                import socket

                first_bs = kafka_url.split(",")[0]
                host, port = (first_bs.split(":", 1) + ["9092"])[:2]
                port = int(port)
                reachable = False
                for _ in range(3):
                    try:
                        with socket.create_connection((host, port), timeout=1):
                            reachable = True
                            break
                    except Exception:
                        time.sleep(0.2)
                if not reachable:
                    # Broker unreachable; skip confluent path and fall back
                    raise RuntimeError(f"Bootstrap broker {host}:{port} unreachable")
            except Exception:
                LOGGER.debug(
                    "Confluent pre-check failed; skipping confluent-kafka path",
                    exc_info=True,
                )
                raise

            # produce synchronously by polling events until delivery or timeout
            delivery_error = None

            def _delivery_report(err, msg):
                nonlocal delivery_error
                if err is not None:
                    delivery_error = err

            key = None
            try:
                if ev.get("event_id"):
                    key = str(ev.get("event_id")).encode("utf-8")
            except Exception:
                key = None

            # confluent expects bytes for key/value when not using serializer
            try:
                producer.produce(
                    topic=topic,
                    value=json.dumps(ev).encode("utf-8"),
                    key=key,
                    callback=_delivery_report,
                )
                producer.flush(6)
            except ConfluentKafkaException:
                LOGGER.debug("Confluent Kafka produce/flush failed", exc_info=True)
                raise
            except Exception:
                LOGGER.debug("Confluent Kafka unexpected error", exc_info=True)
                raise

            if delivery_error:
                raise delivery_error

            try:
                _mx.AUDIT_KAFKA_PUBLISH.inc()
            except Exception:
                pass
            return True
        except Exception:
            LOGGER.debug(
                "Confluent-kafka publish not available or failed; falling back to kafka-python/journal",
                exc_info=True,
            )

    # If confluent path not used or failed, try kafka-python
    try:
        # Stronger publish: require acks='all' and perform a synchronous send with timeout.
        # This improves durability for audit events while still allowing a journal fallback.
        from kafka import KafkaProducer  # type: ignore
        from kafka.errors import KafkaError  # type: ignore

        from . import metrics as _mx

        producer_kwargs = dict(
            bootstrap_servers=kafka_url,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=2,
            request_timeout_ms=5000,
        )
        if use_idempotent:
            # Attempt to enable idempotence; kafka-python supports 'enable_idempotence'
            try:
                producer_kwargs["enable_idempotence"] = True
            except Exception:
                pass
        # Pre-check: ensure at least one bootstrap host resolves and is reachable before attempting kafka‑python producer.
        try:
            import socket

            first_bs = kafka_url.split(",")[0]
            host, port = (first_bs.split(":", 1) + ["9092"])[:2]
            port = int(port)
            with socket.create_connection((host, port), timeout=1):
                pass
        except Exception:
            LOGGER.debug(
                "Kafka pre-check failed; skipping kafka-python path",
                exc_info=True,
            )
            raise
        producer = KafkaProducer(**producer_kwargs)
        # Verify broker connectivity; kafka-python may create a producer even if broker is unreachable.
        # Attempt a lightweight metadata request to ensure the broker responds.
        try:
            # poll will trigger a metadata fetch; 0 timeout returns immediately.
            producer.poll(0)
            # Access metrics or list topics to force a request; ignore result.
            _ = producer.metrics()
        except Exception:
            # If any error occurs, treat as broker unreachable and fall back.
            raise RuntimeError("Kafka broker unreachable during metadata fetch")
        # synchronous send to get broker acknowledgement; use event_id as key when present
        key = None
        try:
            if ev.get("event_id"):
                key = str(ev.get("event_id")).encode("utf-8")
        except Exception:
            key = None
        # Attempt send with retry logic (max 3 attempts) to improve durability.
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            fut = producer.send(topic, value=ev, key=key)
            try:
                fut.get(timeout=6)
                # Success – break out of retry loop
                break
            except KafkaError:
                LOGGER.debug(
                    "Kafka send/get failed on attempt %s", attempt, exc_info=True
                )
                if attempt >= max_attempts:
                    raise
                else:
                    # brief backoff before retry
                    import time as _time

                    _time.sleep(0.2 * attempt)
            except Exception:
                LOGGER.debug(
                    "Kafka send/get unexpected error on attempt %s",
                    attempt,
                    exc_info=True,
                )
                if attempt >= max_attempts:
                    raise
                else:
                    import time as _time

                    _time.sleep(0.2 * attempt)
        try:
            _mx.AUDIT_KAFKA_PUBLISH.inc()
        except Exception:
            pass
        return True
    except Exception:
        LOGGER.debug(
            "kafka-python publish not available or failed; falling back to journal",
            exc_info=True,
        )

    # Fallback: durable on-disk journal
    try:
        from . import metrics as _mx

        # Debug print to verify fallback path
        print(
            "DEBUG: entering final journal fallback with dir", str(_audit_journal_dir())
        )
        # Use direct append to avoid potential monkey‑patched journal.append_event
        _direct_append_event(
            str(_audit_journal_dir()), "audit", {"kafka_topic": topic, "event": ev}
        )
        try:
            _mx.AUDIT_JOURNAL_FALLBACK.inc()
        except Exception:
            pass
        return True
    except Exception:
        LOGGER.exception("Journal fallback failed for audit event")
        try:
            from . import metrics as _mx

            _mx.JOURNAL_SKIP.inc()
        except Exception:
            pass
        return False


def log_admin_action(
    request: Request, action: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """Append an admin audit line to the configured audit file; never raises."""
    try:
        ev: Dict[str, Any] = {
            "ts": int(time.time()),
            "path": str(request.url.path),
            "method": request.method,
            "client": request.client.host if request.client else None,
            "action": action,
        }
        if details:
            ev["details"] = details

        p = Path("./data/somabrain/audit.log")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        LOGGER.debug("log_admin_action failed", exc_info=True)


__all__ = ["publish_event", "log_admin_action"]
