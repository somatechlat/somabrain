"""
Cognitive Orchestrator Service

Listens to GlobalFrame and SegmentBoundary topics and, on boundaries, enqueues
an episodic snapshot into the transactional outbox for downstream persistence.

Design:
- Consume `cog.global.frame` and `cog.segments`.
- Maintain a small per-tenant context with the last GlobalFrame and a running
  summary for the current segment window.
- On a SegmentBoundary event, compose a minimal memory payload capturing the
  boundary, the last global frame context, and basic tags, then call
  somabrain.db.outbox.enqueue_event with topic "memory.episodic.snapshot".
- All networking and heavy deps are optional: Avro serde used when available;
  falls back to JSON parse.

Environment:
- SOMABRAIN_KAFKA_URL: bootstrap servers (default localhost:30001)
- SOMABRAIN_FF_COG_ORCHESTRATOR: enable service (1/true)
- SOMABRAIN_ORCH_NAMESPACE: memory namespace for snapshots (default: "cog")

"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Optional Kafka
try:  # pragma: no cover - optional at runtime
    from kafka import KafkaConsumer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore

# Optional Avro serde
try:  # pragma: no cover
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore

# Outbox API (DB-backed)
try:
    from somabrain.db.outbox import enqueue_event  # type: ignore
except Exception:  # pragma: no cover
    enqueue_event = None  # type: ignore


@dataclass
class GlobalFrameCtx:
    ts: str
    tenant: str
    leader: str
    weights: Dict[str, float] = field(default_factory=dict)
    frame: Dict[str, str] = field(default_factory=dict)
    rationale: str = ""
    count: int = 0


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _parse_global_frame(raw: bytes, serde: Optional[AvroSerde]) -> Optional[GlobalFrameCtx]:
    try:
        data: Dict[str, Any]
        if serde is not None:
            data = serde.deserialize(raw)  # type: ignore[arg-type]
        else:
            data = json.loads(raw.decode("utf-8"))
        ts = str(data.get("ts") or "")
        leader = str(data.get("leader") or "")
        tenant = "public"
        frame_map = data.get("frame") or {}
        if isinstance(frame_map, dict):
            tenant = str(frame_map.get("tenant") or "public").strip() or "public"
        weights = data.get("weights") if isinstance(data.get("weights"), dict) else {}
        rationale = str(data.get("rationale") or "")
        if not ts or not leader:
            return None
        return GlobalFrameCtx(
            ts=ts,
            tenant=tenant,
            leader=leader,
            weights={k: float(v) for k, v in (weights or {}).items()},
            frame=frame_map if isinstance(frame_map, dict) else {},
            rationale=rationale,
            count=1,
        )
    except Exception:
        return None


def _parse_segment_boundary(raw: bytes, serde: Optional[AvroSerde]) -> Optional[Dict[str, Any]]:
    try:
        if serde is not None:
            return serde.deserialize(raw)  # type: ignore[arg-type]
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


class OrchestratorService:
    def __init__(self) -> None:
        self._serde_gf: Optional[AvroSerde] = None
        self._serde_sb: Optional[AvroSerde] = None
        if load_schema is not None and AvroSerde is not None:
            try:
                self._serde_gf = AvroSerde(load_schema("global_frame"))  # type: ignore[arg-type]
            except Exception:
                self._serde_gf = None
            try:
                self._serde_sb = AvroSerde(load_schema("segment_boundary"))  # type: ignore[arg-type]
            except Exception:
                self._serde_sb = None
        self._ns = os.getenv("SOMABRAIN_ORCH_NAMESPACE", "cog")
        # Minimal leader->tools routing (JSON via env)
        try:
            routing_raw = os.getenv("SOMABRAIN_ORCH_ROUTING", "")
            self._routing = json.loads(routing_raw) if routing_raw else {}
        except Exception:
            self._routing = {}
        # per-tenant rolling context for current segment
        self._ctx: Dict[str, GlobalFrameCtx] = {}

    def _remember_snapshot(self, tenant: str, boundary: Dict[str, Any]) -> None:
        if enqueue_event is None:
            return  # no-op if outbox not wired
        gf = self._ctx.get(tenant)
        # Compose a minimal episodic payload for memory
        key = f"segment:{boundary.get('boundary_ts') or int(time.time()*1000)}"
        value: Dict[str, Any] = {
            "memory_type": "episodic",
            "segment": {
                "domain": boundary.get("domain"),
                "boundary_ts": boundary.get("boundary_ts"),
                "dwell_ms": int(boundary.get("dwell_ms") or 0),
                "evidence": boundary.get("evidence"),
            },
            "tenant": tenant,
            "namespace": self._ns,
        }
        if gf is not None:
            value["leader"] = gf.leader
            value["weights"] = gf.weights
            value["frame"] = gf.frame
            value["rationale"] = gf.rationale
            value["last_frame_ts"] = gf.ts
            value["frames_in_segment"] = gf.count
            # Leader-aware routing tags (optional)
            try:
                tools = self._routing.get(gf.leader)
                if isinstance(tools, list) and tools:
                    value["route"] = {"tools": [str(t) for t in tools]}
            except Exception:
                pass
        tags = ["cog", "segment", str(boundary.get("domain") or "?")]
        payload = {
            "tenant": tenant,
            "namespace": self._ns,
            "key": key,
            "value": value,
            "tags": tags,
            "policy_tags": ["auto:segment"],
        }
        try:
            enqueue_event(
                topic="memory.episodic.snapshot",
                payload=payload,
                dedupe_key=f"{tenant}:{key}",
                tenant_id=tenant,
            )
        except Exception:
            # best-effort enqueue; drop on error
            pass

    def run_forever(self) -> None:  # pragma: no cover - integration loop
        if KafkaConsumer is None:
            print("Kafka client not available; orchestrator service idle.")
            while True:
                time.sleep(60)
        consumer = KafkaConsumer(
            "cog.global.frame",
            "cog.segments",
            bootstrap_servers=_bootstrap(),
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=os.getenv("SOMABRAIN_CONSUMER_GROUP", "orchestrator-service"),
        )
        try:
            for msg in consumer:
                topic = getattr(msg, "topic", "") or ""
                if topic == "cog.global.frame":
                    gf = _parse_global_frame(msg.value, self._serde_gf)
                    if gf is None:
                        continue
                    # Update per-tenant context
                    ctx = self._ctx.get(gf.tenant)
                    if ctx is None:
                        self._ctx[gf.tenant] = gf
                    else:
                        ctx.ts = gf.ts
                        ctx.leader = gf.leader
                        ctx.weights = gf.weights
                        ctx.frame = gf.frame
                        ctx.rationale = gf.rationale
                        ctx.count += 1
                else:  # cog.segments
                    sb = _parse_segment_boundary(msg.value, self._serde_sb)
                    if not isinstance(sb, dict):
                        continue
                    tenant = str(sb.get("tenant") or "public").strip() or "public"
                    # Enqueue episodic snapshot for this tenant
                    self._remember_snapshot(tenant, sb)
        finally:
            try:
                consumer.close()
            except Exception:
                pass


def main() -> None:  # pragma: no cover - entrypoint
    ff = os.getenv("SOMABRAIN_FF_COG_ORCHESTRATOR", "0").strip().lower()
    if ff not in ("1", "true", "yes", "on"):
        print("Orchestrator feature flag disabled; exiting.")
        return
    OrchestratorService().run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
