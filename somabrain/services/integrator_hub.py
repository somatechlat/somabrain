"""Cognitive Integrator Hub

Consumes BeliefUpdate events from Kafka, computes a softmax leader across
domains per tenant, publishes a GlobalFrame event, and caches the latest
frame in Redis for quick access.

Environment:
- SOMABRAIN_KAFKA_URL: Bootstrap servers (kafka://host:port or host:port)
- SOMABRAIN_REDIS_URL: Redis URL (redis://host:port/db)
- SOMABRAIN_OPA_URL: Optional OPA base URL for gating (POST /v1/data/<policy>)
- SOMABRAIN_OPA_POLICY: Optional policy path (e.g., soma.policy.integrator)
- SOMABRAIN_FF_COG_INTEGRATOR: Feature flag (1/true to enable main())

Topics:
- Input:  cog.state.updates, cog.agent.updates, cog.action.updates
- Output: cog.global.frame

Contracts:
- Input:  proto/cog/belief_update.avsc
- Output: proto/cog/global_frame.avsc
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from kafka import KafkaConsumer, KafkaProducer  # type: ignore

import somabrain.metrics as app_metrics


INTEGRATOR_CONSUMED = app_metrics.get_counter(
    "somabrain_integrator_updates_total",
    "BeliefUpdate records consumed",
    labelnames=["domain"],
)
INTEGRATOR_PUBLISHED = app_metrics.get_counter(
    "somabrain_integrator_frames_total",
    "GlobalFrame records published",
    labelnames=["tenant"],
)
INTEGRATOR_ERRORS = app_metrics.get_counter(
    "somabrain_integrator_errors_total",
    "Unhandled errors in integrator loop",
    labelnames=["stage"],
)

# Optional OPA decision latency
INTEGRATOR_OPA_LAT = app_metrics.get_histogram(
    "somabrain_integrator_opa_latency_seconds",
    "OPA decision latency for integrator gating",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_scheme(url: str) -> str:
    u = (url or "").strip()
    return u.split("://", 1)[1] if "://" in u else u


@dataclass
class DomainObs:
    ts: float
    confidence: float
    delta_error: float
    meta: Dict[str, Any] = field(default_factory=dict)


class SoftmaxIntegrator:
    """Maintains last observation per domain and computes softmax leader.

    - Per tenant store the most recent observation for each domain.
    - Compute softmax across confidences with temperature tau.
    """

    def __init__(self, tau: float = 1.0, stale_seconds: float = 10.0) -> None:
        self._tau = max(1e-6, float(tau))
        self._stale = max(0.0, float(stale_seconds))
        self._by_tenant: Dict[str, Dict[str, DomainObs]] = {}

    def update(self, tenant: str, domain: str, obs: DomainObs) -> None:
        t = (tenant or "public").strip() or "public"
        d = domain.strip().lower()
        if d not in ("state", "agent", "action"):
            return
        self._by_tenant.setdefault(t, {})[d] = obs

    def snapshot(self, tenant: str) -> Tuple[str, Dict[str, float], Dict[str, DomainObs]]:
        """Return (leader, weights, raw_map) for tenant.

        Stale observations older than stale_seconds are ignored.
        """
        t = (tenant or "public").strip() or "public"
        now = time.time()
        raw = {k: v for k, v in self._by_tenant.get(t, {}).items() if (now - v.ts) <= self._stale}
        if not raw:
            return ("state", {"state": 1.0, "agent": 0.0, "action": 0.0}, {})
        # Softmax over available domains
        exps: Dict[str, float] = {}
        for d, ob in raw.items():
            exps[d] = math.exp(float(ob.confidence) / self._tau)
        Z = sum(exps.values()) or 1.0
        weights = {d: (v / Z) for d, v in exps.items()}
        leader = max(weights.items(), key=lambda kv: kv[1])[0]
        # Fill missing domains with 0
        for d in ("state", "agent", "action"):
            if d not in weights:
                weights[d] = 0.0
        return leader, weights, raw


class IntegratorHub:
    def __init__(self, group_id: str = "integrator-hub-v1") -> None:
        # Bootstrap (prefer shared settings when available)
        bs = None
        redis_url = None
        try:
            from common.config.settings import settings as _settings  # type: ignore

            bs = _settings.kafka_bootstrap_servers
            redis_url = _settings.redis_url
        except Exception:
            pass
        bs = bs or os.getenv("SOMABRAIN_KAFKA_URL") or ""
        redis_url = redis_url or os.getenv("SOMABRAIN_REDIS_URL") or ""
        self._bootstrap = _strip_scheme(bs)
        self._redis_url = redis_url
        # Serde
        # Lazy import for Avro helpers to avoid import-time dependency for unit tests
        self._bu_schema = None
        self._gf_schema = None
        self._avro_bu = None
        self._avro_gf = None
        try:
            from libs.kafka_cog.avro_schemas import load_schema  # type: ignore

            self._bu_schema = load_schema("belief_update")
            self._gf_schema = load_schema("global_frame")
            try:
                from libs.kafka_cog.serde import AvroSerde  # type: ignore

                self._avro_bu = AvroSerde(self._bu_schema)
                self._avro_gf = AvroSerde(self._gf_schema)
            except Exception:
                self._avro_bu = None
                self._avro_gf = None
        except Exception:
            # Avro path unavailable; JSON fallback will be used
            self._bu_schema = None
            self._gf_schema = None
        # Kafka
        self._consumer: Optional[KafkaConsumer] = None
        self._producer: Optional[KafkaProducer] = None
        self._group_id = group_id
        # State
        self._sm = SoftmaxIntegrator(tau=1.0, stale_seconds=10.0)
        # Redis cache (optional)
        self._cache = None
        if self._redis_url:
            try:
                from common.utils.cache import RedisCache  # type: ignore

                self._cache = RedisCache(self._redis_url, namespace="cog")
            except Exception:
                self._cache = None
        # OPA (optional)
        self._opa_url: Optional[str] = None
        self._opa_policy: Optional[str] = None
        self._opa_fail_closed: bool = False
        try:
            from common.config.settings import settings as _settings  # type: ignore

            self._opa_url = (_settings.opa_url or os.getenv("SOMABRAIN_OPA_URL") or "").strip()
            self._opa_policy = os.getenv("SOMABRAIN_OPA_POLICY", "").strip()
            # Prefer mode-aware fail-closed if available
            try:
                self._opa_fail_closed = bool(_settings.mode_opa_fail_closed())
            except Exception:
                self._opa_fail_closed = bool(
                    os.getenv("SOMA_OPA_FAIL_CLOSED", "false").lower()
                    in ("1", "true", "yes", "on")
                )
        except Exception:
            self._opa_url = (os.getenv("SOMABRAIN_OPA_URL") or "").strip()
            self._opa_policy = os.getenv("SOMABRAIN_OPA_POLICY", "").strip()
            self._opa_fail_closed = bool(
                os.getenv("SOMA_OPA_FAIL_CLOSED", "false").lower() in ("1", "true", "yes", "on")
            )

    def _ensure_clients(self) -> None:
        if not self._bootstrap:
            raise RuntimeError("Kafka bootstrap not configured (SOMABRAIN_KAFKA_URL)")
        if self._consumer is None:
            self._consumer = KafkaConsumer(
                "cog.state.updates",
                "cog.agent.updates",
                "cog.action.updates",
                bootstrap_servers=self._bootstrap,
                group_id=self._group_id,
                enable_auto_commit=True,
                auto_offset_reset="latest",
                consumer_timeout_ms=1000,
            )
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap,
                acks="1",
                linger_ms=5,
            )

    def _decode_update(self, payload: bytes) -> Optional[Dict[str, Any]]:
        # Try Avro first
        if self._avro_bu is not None:
            try:
                return self._avro_bu.deserialize(payload)
            except Exception:
                pass
        # Fallback to JSON
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    def _encode_frame(self, record: Dict[str, Any]) -> bytes:
        if self._avro_gf is not None:
            try:
                return self._avro_gf.serialize(record)
            except Exception:
                pass
        return json.dumps(record).encode("utf-8")

    def _publish_frame(self, frame: Dict[str, Any]) -> None:
        if not self._producer:
            return
        try:
            self._producer.send("cog.global.frame", value=self._encode_frame(frame))
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="publish").inc()

    def _cache_frame(self, tenant: str, frame: Dict[str, Any]) -> None:
        if not self._cache:
            return
        try:
            self._cache.set(f"global_frame:{tenant}", frame, ttl_seconds=120)
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="redis").inc()

    @staticmethod
    def _tenant_from(ev: Dict[str, Any]) -> str:
        try:
            evd = ev.get("evidence") or {}
            t = str(evd.get("tenant", "")).strip()
            return t or "public"
        except Exception:
            return "public"

    def _process_update(self, ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        domain = str(ev.get("domain", "state")).strip().lower()
        tenant = self._tenant_from(ev)
        conf = float(ev.get("confidence", 0.0))
        derr = float(ev.get("delta_error", 0.0))
        ts = time.time()
        self._sm.update(tenant, domain, DomainObs(ts=ts, confidence=conf, delta_error=derr, meta=ev))
        leader, weights, raw = self._sm.snapshot(tenant)
        # Build GlobalFrame per schema (map values must be string for frame)
        frame_map: Dict[str, str] = {
            "tenant": tenant,
            "leader_domain": leader,
        }
        # Include leader delta_error and confidence as strings
        try:
            lob = raw.get(leader)
            if lob is not None:
                frame_map["leader_confidence"] = f"{lob.confidence:.6f}"
                frame_map["leader_delta_error"] = f"{lob.delta_error:.6f}"
        except Exception:
            pass
        rationale = f"softmax_tau=1.0 domains={','.join(sorted(k for k in weights.keys() if weights[k]>0))}"
        # Optional OPA gating/adjustment
        leader_adj = leader
        if self._opa_url and self._opa_policy:
            allowed, new_leader, opa_note = self._opa_decide(tenant, leader, weights, ev)
            if not allowed:
                # If fail-closed, drop frame; otherwise continue with original leader
                if self._opa_fail_closed:
                    return None
                else:
                    rationale += f"; opa=deny"
            else:
                if new_leader and new_leader in ("state", "agent", "action"):
                    leader_adj = new_leader
                rationale += f"; opa=allow{opa_note}"
        gf = {
            "ts": _now_iso(),
            "leader": leader_adj,
            "weights": {k: float(v) for k, v in weights.items()},
            "frame": frame_map,
            "rationale": rationale,
        }
        return gf

    def _opa_decide(
        self,
        tenant: str,
        leader: str,
        weights: Dict[str, float],
        ev: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], str]:
        """Call OPA to allow/adjust leader.

        Returns: (allowed, new_leader|None, note)
        """
        url = self._opa_url or ""
        pol = self._opa_policy or ""
        if not url or not pol:
            return True, None, ""
        # Build input
        payload = {
            "input": {
                "tenant": tenant,
                "candidate": {"leader": leader, "weights": weights},
                "event": ev,
            }
        }
        # POST /v1/data/<policy>
        endpoint = url.rstrip("/") + "/v1/data/" + pol.replace(".", "/")
        t0 = time.perf_counter()
        try:
            import requests  # type: ignore

            resp = requests.post(endpoint, json=payload, timeout=1.5)
            INTEGRATOR_OPA_LAT.observe(max(0.0, time.perf_counter() - t0))
            if resp.status_code >= 400:
                return (not self._opa_fail_closed), None, ""
            data = resp.json()
            # Expect {"result": {"allow": bool, "leader": optional str}}
            res = data.get("result") if isinstance(data, dict) else None
            if not isinstance(res, dict):
                return True, None, ""
            allow = bool(res.get("allow", True))
            new_leader = res.get("leader")
            note = ""
            if isinstance(new_leader, str) and new_leader:
                note = f"; leader={new_leader}"
            return allow, (str(new_leader) if isinstance(new_leader, str) else None), note
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="opa").inc()
            INTEGRATOR_OPA_LAT.observe(max(0.0, time.perf_counter() - t0))
            return (not self._opa_fail_closed), None, ""

    def run_forever(self) -> None:
        self._ensure_clients()
        assert self._consumer is not None
        for msg in self._consumer:
            try:
                ev = self._decode_update(msg.value)
                if not isinstance(ev, dict):
                    INTEGRATOR_ERRORS.labels(stage="decode").inc()
                    continue
                dom = str(ev.get("domain", "state"))
                INTEGRATOR_CONSUMED.labels(domain=dom).inc()
                frame = self._process_update(ev)
                if frame is None:
                    continue
                self._publish_frame(frame)
                self._cache_frame(self._tenant_from(ev), frame)
                INTEGRATOR_PUBLISHED.labels(tenant=self._tenant_from(ev)).inc()
            except Exception:
                INTEGRATOR_ERRORS.labels(stage="loop").inc()


def main() -> None:  # pragma: no cover - manual run path
    ff = os.getenv("SOMABRAIN_FF_COG_INTEGRATOR", "").strip().lower()
    if ff not in ("1", "true", "yes", "on"):
        print("Integrator Hub feature flag disabled; set SOMABRAIN_FF_COG_INTEGRATOR=1 to enable.")
        return
    hub = IntegratorHub()
    print("Starting Integrator Hub...")
    hub.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
