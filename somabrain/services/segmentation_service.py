"""
Segmentation Service
--------------------

Consumes GlobalFrame events and emits SegmentBoundary records when the leader
domain changes or when a maximum dwell threshold is reached.

Design choices:
- Stateless Kafka I/O around a small, testable Segmenter core that tracks the
  current leader and last-change timestamp.
- Uses Avro schemaless serde if `fastavro` is installed; otherwise falls back
  to JSON payloads for local/dev.
- Metrics are exported via somabrain.metrics (counters + histogram).

Environment variables:
- SOMABRAIN_KAFKA_URL: bootstrap servers (default localhost:30001)
- SOMABRAIN_FF_COG_SEGMENTATION: enable/disable service (default off)
- SOMABRAIN_SEGMENT_MAX_DWELL_MS: optional max dwell; emits boundary even if
  leader hasn't changed (default 0 meaning disabled)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


# Lazy imports for optional dependencies
try:  # pragma: no cover - optional at runtime
    from kafka import KafkaConsumer, KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore
    KafkaProducer = None  # type: ignore


try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover - unit tests focus on core segmenter
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


BOUNDARY_EMITTED = None
BOUNDARY_LATENCY = None


def _init_metrics() -> None:
    global BOUNDARY_EMITTED, BOUNDARY_LATENCY
    if metrics is None:
        return
    if BOUNDARY_EMITTED is None:
        try:
            BOUNDARY_EMITTED = metrics.get_counter(
                "somabrain_segments_emitted_total",
                "Segment boundaries emitted",
                labelnames=["domain", "evidence"],
            )
        except Exception:
            BOUNDARY_EMITTED = None
    if BOUNDARY_LATENCY is None:
        try:
            BOUNDARY_LATENCY = metrics.get_histogram(
                "somabrain_segments_dwell_ms",
                "Observed dwell durations at boundaries (ms)",
            )
        except Exception:
            BOUNDARY_LATENCY = None


@dataclass
class Frame:
    ts: str
    leader: str
    tenant: str


def _parse_frame(value: bytes, serde: Optional[AvroSerde]) -> Optional[Frame]:
    if value is None:
        return None
    try:
        if serde is not None:
            data = serde.deserialize(value)  # type: ignore[arg-type]
        else:
            data = json.loads(value.decode("utf-8"))
        ts = str(data.get("ts") or "")
        leader = str(data.get("leader") or "")
        # tenant is nested in frame map from IntegratorHub
        tenant = "public"
        try:
            frame_map = data.get("frame") or {}
            tv = frame_map.get("tenant") if isinstance(frame_map, dict) else None
            tenant = str(tv or "public").strip() or "public"
        except Exception:
            tenant = "public"
        if not ts or not leader:
            return None
        return Frame(ts=ts, leader=leader, tenant=tenant)
    except Exception:
        return None


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _now_ms() -> int:
    return int(time.time() * 1000)


class Segmenter:
    """Tracks leader changes and computes dwell.

    Contract:
    - input: (ts_str, leader)
    - state: last_leader, last_change_ms
    - output: optional (domain, boundary_ts_str, dwell_ms, evidence)

    Evidence values:
    - "leader_change" when leader swaps
    - "max_dwell" when max dwell threshold is reached and leader hasn't changed
    """

    def __init__(self, max_dwell_ms: int = 0):
        self.max_dwell_ms = max(0, int(max_dwell_ms))
        # Maintain independent state per tenant
        self._last_leader: Dict[str, Optional[str]] = {}
        self._last_change_ms: Dict[str, Optional[int]] = {}

    @staticmethod
    def _parse_ts(ts: str) -> int:
        # Expect RFC3339-like strings; fall back to epoch-ms if numeric.
        ts = (ts or "").strip()
        if not ts:
            return _now_ms()
        # Fast path: integer string millis
        if ts.isdigit():
            try:
                return int(ts)
            except Exception:
                return _now_ms()
        # Try fromisoformat (Python >=3.7)
        try:
            from datetime import datetime

            # Remove Z if present
            ts2 = ts[:-1] if ts.endswith("Z") else ts
            dt = datetime.fromisoformat(ts2)
            return int(dt.timestamp() * 1000)
        except Exception:
            return _now_ms()

    def observe(self, ts: str, leader: str, tenant: Optional[str] = None) -> Optional[Tuple[str, str, int, str]]:
        """Observe a frame for a tenant and possibly emit a boundary.

        Backward compatible: if tenant is None, use 'public' bucket.
        """
        t = (tenant or "public").strip() or "public"
        now_ms = self._parse_ts(ts)
        leader = (leader or "").strip()
        if not leader:
            return None

        last_leader = self._last_leader.get(t)
        last_change = self._last_change_ms.get(t)

        if last_leader is None:
            # Initialize state; no boundary yet
            self._last_leader[t] = leader
            self._last_change_ms[t] = now_ms
            return None

        # Check max dwell first
        if (
            self.max_dwell_ms > 0
            and last_change is not None
            and now_ms - last_change >= self.max_dwell_ms
            and leader == last_leader
        ):
            dwell = now_ms - (last_change or now_ms)
            boundary_ts = ts
            domain = last_leader or leader
            # Reset change marker but keep same leader
            self._last_change_ms[t] = now_ms
            return (domain, boundary_ts, int(dwell), "max_dwell")

        # Leader change
        if leader != last_leader:
            dwell = now_ms - (last_change or now_ms)
            boundary_ts = ts
            domain = last_leader
            # Update state to new leader
            self._last_leader[t] = leader
            self._last_change_ms[t] = now_ms
            return (domain, boundary_ts, int(dwell), "leader_change")

        # No boundary
        return None


class SegmentationService:
    def __init__(self):
        _init_metrics()
        self._serde_in: Optional[AvroSerde] = None
        self._serde_out: Optional[AvroSerde] = None
        try:
            if load_schema is not None and AvroSerde is not None:
                gf_schema = load_schema("global_frame")
                sb_schema = load_schema("segment_boundary")
                self._serde_in = AvroSerde(gf_schema)
                self._serde_out = AvroSerde(sb_schema)
        except Exception:
            self._serde_in = None
            self._serde_out = None
        max_dwell_ms = int(os.getenv("SOMABRAIN_SEGMENT_MAX_DWELL_MS", "0") or "0")
        self._segmenter = Segmenter(max_dwell_ms=max_dwell_ms)

    def run_forever(self) -> None:  # pragma: no cover - integration loop
        if KafkaConsumer is None or KafkaProducer is None:
            print("Kafka client not available; segmentation service idle.")
            while True:
                time.sleep(60)
        consumer = KafkaConsumer(
            "cog.global.frame",
            bootstrap_servers=_bootstrap(),
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=os.getenv("SOMABRAIN_CONSUMER_GROUP", "segmentation-service"),
        )
        producer = KafkaProducer(
            bootstrap_servers=_bootstrap(),
            value_serializer=lambda m: m,
            acks="all",
        )
        try:
            for msg in consumer:
                frame = _parse_frame(msg.value, self._serde_in)
                if frame is None:
                    continue
                out = self._segmenter.observe(frame.ts, frame.leader, frame.tenant)
                if out is None:
                    continue
                domain, boundary_ts, dwell_ms, evidence = out
                record = {
                    "tenant": frame.tenant,
                    "domain": domain,
                    "boundary_ts": boundary_ts,
                    "dwell_ms": int(dwell_ms),
                    "evidence": evidence,
                }
                payload: bytes
                try:
                    if self._serde_out is not None:
                        payload = self._serde_out.serialize(record)
                    else:
                        payload = json.dumps(record).encode("utf-8")
                except Exception:
                    continue

                try:
                    producer.send("cog.segments", value=payload)
                    if BOUNDARY_EMITTED is not None:
                        try:
                            BOUNDARY_EMITTED.labels(
                                domain=domain, evidence=evidence
                            ).inc()
                        except Exception:
                            pass
                    if BOUNDARY_LATENCY is not None:
                        try:
                            BOUNDARY_LATENCY.observe(float(max(0, int(dwell_ms))))
                        except Exception:
                            pass
                except Exception:
                    # drop on floor; best-effort
                    continue
        finally:
            try:
                consumer.close()
            except Exception:
                pass
            try:
                producer.flush(2)
                producer.close()
            except Exception:
                pass


def main() -> None:  # pragma: no cover - service entrypoint
    ff = os.getenv("SOMABRAIN_FF_COG_SEGMENTATION", "0").strip()
    if ff not in ("1", "true", "True", "yes"):
        print("Segmentation feature flag disabled; exiting.")
        return
    svc = SegmentationService()
    svc.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
