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
import threading
try:  # optional OTel init
    from observability.provider import init_tracing, get_tracer  # type: ignore
except Exception:  # pragma: no cover
    def init_tracing():
        return None

    def get_tracer(name: str):  # type: ignore
        class _Noop:
            def start_as_current_span(self, *_args, **_kwargs):
                class _Span:
                    def __enter__(self):
                        return self

                    def __exit__(self, *a):
                        return False

                return _Span()

        return _Noop()

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
INTEGRATOR_LEADER_SWITCHES = app_metrics.get_counter(
    "somabrain_integrator_leader_switches_total",
    "Leader changes per tenant",
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

# Entropy of domain weights (0 = degenerate, 1 = uniform across 3 domains)
INTEGRATOR_ENTROPY = app_metrics.get_histogram(
    "somabrain_integrator_leader_entropy",
    "Entropy of domain weight distribution (normalized)",
    labelnames=["tenant"],
    buckets=(
        0.0,
        0.05,
        0.1,
        0.15,
        0.2,
        0.25,
        0.3,
        0.35,
        0.4,
        0.45,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
    ),
)

# Shadow/Config metrics
INTEGRATOR_SHADOW_TOTAL = app_metrics.get_counter(
    "somabrain_integrator_shadow_total",
    "Frames routed to shadow topic",
)
INTEGRATOR_SHADOW_RATIO = app_metrics.get_gauge(
    "somabrain_integrator_shadow_ratio",
    "Observed ratio of frames sent to shadow topic (EMA-free, instantaneous)",
)
INTEGRATOR_TAU = app_metrics.get_gauge(
    "somabrain_integrator_tau",
    "Current softmax temperature (tau)",
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

    def set_tau(self, tau: float) -> None:
        self._tau = max(1e-6, float(tau))

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
        # Initialize tracing (no-op safe)
        init_tracing()
        self._tracer = get_tracer("somabrain.integrator_hub")
        # Start lightweight health server on a side port for K8s probes
        try:
            if os.getenv("HEALTH_PORT"):
                self._start_health_server()
        except Exception:
            pass
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
        # Feature flags
        self._soma_compat: bool = (
            os.getenv("SOMA_COMPAT", "").strip().lower() in ("1", "true", "yes", "on")
        )
        # Serde
        # Lazy import for Avro helpers to avoid import-time dependency for unit tests
        self._bu_schema = None
        self._gf_schema = None
        self._ic_schema = None
        self._avro_bu = None
        self._avro_gf = None
        self._avro_bu_soma = None
        self._avro_ic = None
        try:
            from libs.kafka_cog.avro_schemas import load_schema  # type: ignore

            self._bu_schema = load_schema("belief_update")
            self._gf_schema = load_schema("global_frame")
            # Optional compatibility schemas
            try:
                self._ic_schema = load_schema("integrator_context")
            except Exception:
                self._ic_schema = None
            try:
                _soma_schema = load_schema("belief_update_soma")
            except Exception:
                _soma_schema = None
            try:
                from libs.kafka_cog.serde import AvroSerde  # type: ignore

                self._avro_bu = AvroSerde(self._bu_schema)
                self._avro_gf = AvroSerde(self._gf_schema)
                if _soma_schema is not None:
                    try:
                        self._avro_bu_soma = AvroSerde(_soma_schema)
                    except Exception:
                        self._avro_bu_soma = None
                if self._ic_schema is not None:
                    try:
                        self._avro_ic = AvroSerde(self._ic_schema)
                    except Exception:
                        self._avro_ic = None
            except Exception:
                self._avro_bu = None
                self._avro_gf = None
                self._avro_bu_soma = None
                self._avro_ic = None
        except Exception:
            # Avro path unavailable; JSON fallback will be used
            self._bu_schema = None
            self._gf_schema = None
            self._ic_schema = None
        # Kafka
        self._consumer: Optional[KafkaConsumer] = None
        self._producer: Optional[KafkaProducer] = None
        self._group_id = group_id
        # State
        self._sm = SoftmaxIntegrator(tau=1.0, stale_seconds=10.0)
        try:
            INTEGRATOR_TAU.set(1.0)
        except Exception:
            pass
        self._shadow_ratio = float(os.getenv("SHADOW_RATIO", "0.0") or "0.0")
        self._frames_seen = 0
        self._shadow_sent = 0
        # Track leader switches per tenant
        self._last_leader: Dict[str, str] = {}
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

    def _start_health_server(self) -> None:
        try:
            from fastapi import FastAPI
            import uvicorn  # type: ignore

            app = FastAPI(title="IntegratorHub Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "integrator_hub"}

            # Prometheus metrics endpoint (optional)
            try:
                from somabrain import metrics as _M  # type: ignore

                @app.get("/metrics")
                async def _metrics_ep():  # type: ignore
                    return await _M.metrics_endpoint()
            except Exception:
                pass

            port = int(os.getenv("HEALTH_PORT"))
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            th = threading.Thread(target=server.run, daemon=True)
            th.start()
        except Exception:
            pass
    def _ensure_clients(self) -> None:
        if not self._bootstrap:
            raise RuntimeError("Kafka bootstrap not configured (SOMABRAIN_KAFKA_URL)")
        if self._consumer is None:
            topics = [
                "cog.state.updates",
                "cog.agent.updates",
                "cog.action.updates",
                "cog.config.updates",
            ]
            if self._soma_compat:
                # Consume SOMA belief updates as well
                topics.extend([
                    "soma.belief.state",
                    "soma.belief.agent",
                    "soma.belief.action",
                ])
            self._consumer = KafkaConsumer(
                *topics,
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

    def _decode_update_soma(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode a SOMA belief update and map to internal representation.

        Internal format uses keys: domain, confidence, delta_error, evidence.tenant
        """
        rec: Optional[Dict[str, Any]] = None
        # Prefer Avro soma schema if available
        if self._avro_bu_soma is not None:
            try:
                rec = self._avro_bu_soma.deserialize(payload)  # type: ignore
            except Exception:
                rec = None
        if rec is None:
            try:
                rec = json.loads(payload.decode("utf-8"))
            except Exception:
                return None
        try:
            # Map SOMA fields
            stream = str(rec.get("stream") or rec.get("Stream") or "state").lower()
            if stream not in ("state", "agent", "action"):
                # Enum may be uppercase
                stream = str(rec.get("stream") or "STATE").upper().strip()
                stream = stream.lower()
            ts_ms = int(rec.get("timestamp") or 0)
            delta_error = float(rec.get("delta_error") or 0.0)
            # Derive a confidence from delta_error (monotone decreasing)
            try:
                confidence = math.exp(-max(0.0, float(delta_error)))
            except Exception:
                confidence = 0.0
            metadata = rec.get("metadata") or {}
            tenant = "public"
            if isinstance(metadata, dict):
                tenant = str(metadata.get("tenant", "public") or "public").strip() or "public"
            mapped = {
                "domain": stream,
                "confidence": float(confidence),
                "delta_error": float(delta_error),
                "evidence": {"tenant": tenant, "ts_ms": ts_ms},
            }
            return mapped
        except Exception:
            return None

    def _encode_frame(self, record: Dict[str, Any]) -> bytes:
        if self._avro_gf is not None:
            try:
                return self._avro_gf.serialize(record)
            except Exception:
                pass
        return json.dumps(record).encode("utf-8")

    def _decode_config(self, payload: bytes) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    def _publish_frame(self, frame: Dict[str, Any]) -> None:
        if not self._producer:
            return
        # Shadow routing decision
        route_to_shadow = False
        try:
            import random as _random

            route_to_shadow = (self._shadow_ratio > 0.0) and (_random.random() < self._shadow_ratio)
        except Exception:
            route_to_shadow = False
        try:
            if route_to_shadow:
                self._producer.send("cog.integrator.context.shadow", value=self._encode_frame(frame))
                try:
                    INTEGRATOR_SHADOW_TOTAL.inc()
                    self._shadow_sent += 1
                    if self._frames_seen > 0:
                        INTEGRATOR_SHADOW_RATIO.set(max(0.0, min(1.0, float(self._shadow_sent) / float(self._frames_seen))))
                except Exception:
                    pass
            else:
                self._producer.send("cog.global.frame", value=self._encode_frame(frame))
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="publish").inc()

    def _publish_soma_context(
        self,
        leader: str,
        weights: Dict[str, float],
        gf_record: Dict[str, Any],
        policy_allowed: bool,
    ) -> None:
        if not self._producer or not self._soma_compat:
            return
        try:
            leader_score = float(weights.get(leader, 0.0))
        except Exception:
            leader_score = 0.0
        # Encode embedded global_frame as bytes (prefer Avro if available)
        try:
            gf_bytes = self._encode_frame(gf_record)
        except Exception:
            try:
                gf_bytes = json.dumps(gf_record).encode("utf-8")
            except Exception:
                gf_bytes = b"{}"
        ic = {
            "leader_stream": str(leader),
            "leader_score": float(leader_score),
            "global_frame": gf_bytes,
            "timestamp": int(time.time() * 1000),
            "policy_decision": bool(policy_allowed),
        }
        try:
            if self._avro_ic is not None:
                payload = self._avro_ic.serialize(ic)
            else:
                payload = json.dumps(ic).encode("utf-8")
            self._producer.send("soma.integrator.context", value=payload)
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="publish_soma").inc()

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
        # Leader switch metric
        try:
            last = self._last_leader.get(tenant)
            if last is not None and last != leader:
                INTEGRATOR_LEADER_SWITCHES.labels(tenant=tenant).inc()
            self._last_leader[tenant] = leader
        except Exception:
            pass
        # Observe entropy of weights (normalize by log(3) so range is 0..1)
        try:
            import math as _math

            ps = [max(1e-12, float(weights.get(k, 0.0))) for k in ("state", "agent", "action")]
            Z = sum(ps) or 1.0
            ps = [p / Z for p in ps]
            H = -sum(p * _math.log(p) for p in ps) / _math.log(3.0)
            INTEGRATOR_ENTROPY.labels(tenant=tenant).observe(max(0.0, min(1.0, float(H))))
        except Exception:
            pass
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
        policy_allowed = True
        if self._opa_url and self._opa_policy:
            allowed, new_leader, opa_note = self._opa_decide(tenant, leader, weights, ev)
            if not allowed:
                # If fail-closed, drop frame; otherwise continue with original leader
                if self._opa_fail_closed:
                    return None
                else:
                    policy_allowed = False
                    rationale += "; opa=deny"
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
        # Attach policy flag so caller can publish SOMA context if enabled
        gf["_policy_allowed"] = policy_allowed  # type: ignore
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
                topic = getattr(msg, "topic", "") or ""
                # Config updates: adjust tau (and optionally other params)
                if topic == "cog.config.updates":
                    cfg = self._decode_config(msg.value)
                    if isinstance(cfg, dict):
                        temp = cfg.get("exploration_temp")
                        if temp is not None:
                            try:
                                self._sm.set_tau(float(temp))
                                INTEGRATOR_TAU.set(float(temp))
                            except Exception:
                                pass
                    continue

                # Decode event depending on topic (cog vs soma)
                if topic.startswith("soma.belief."):
                    ev = self._decode_update_soma(msg.value)
                else:
                    ev = self._decode_update(msg.value)
                if not isinstance(ev, dict):
                    INTEGRATOR_ERRORS.labels(stage="decode").inc()
                    continue
                dom = str(ev.get("domain", "state"))
                INTEGRATOR_CONSUMED.labels(domain=dom).inc()
                with self._tracer.start_as_current_span("integrator_process_update"):
                    frame = self._process_update(ev)
                if frame is None:
                    continue
                # Track frames seen for shadow ratio gauge
                try:
                    self._frames_seen += 1
                except Exception:
                    pass
                # Publish primary global frame
                self._publish_frame(frame)
                # Publish SOMA integrator context if enabled
                if self._soma_compat:
                    try:
                        policy_allowed = bool(frame.pop("_policy_allowed", True))  # type: ignore
                    except Exception:
                        policy_allowed = True
                    leader_out = str(frame.get("leader", "state"))
                    weights_out = dict(frame.get("weights", {})) if isinstance(frame.get("weights"), dict) else {}
                    self._publish_soma_context(leader_out, weights_out, frame, policy_allowed)
                # Cache and metrics
                self._cache_frame(self._tenant_from(ev), frame)
                INTEGRATOR_PUBLISHED.labels(tenant=self._tenant_from(ev)).inc()
            except Exception:
                INTEGRATOR_ERRORS.labels(stage="loop").inc()


def main() -> None:  # pragma: no cover - manual run path
    ff = os.getenv("SOMABRAIN_FF_COG_INTEGRATOR", "").strip().lower()
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in ("1", "true", "yes", "on")
    if ff not in ("1", "true", "yes", "on") and not composite:
        print("Integrator Hub feature flag disabled; set SOMABRAIN_FF_COG_INTEGRATOR=1 to enable.")
        return
    hub = IntegratorHub()
    print("Starting Integrator Hub...")
    hub.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
