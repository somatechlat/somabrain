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

# Tracing provider (fallback to no-op if observability package is unavailable)
try:
    from observability.provider import init_tracing, get_tracer  # type: ignore
except Exception:  # pragma: no cover - test/import fallback
    from contextlib import contextmanager

    def init_tracing() -> None:  # type: ignore
        return None

    class _NoopTracer:
        @contextmanager
        def start_as_current_span(self, name: str):  # type: ignore
            yield None

    def get_tracer(name: str) -> _NoopTracer:  # type: ignore
        return _NoopTracer()


import somabrain.metrics as app_metrics
import math as _math

try:
    from somabrain.integrator.consistency import consistency_score  # type: ignore
except Exception:  # pragma: no cover - optional import in tests

    def consistency_score(agent_posterior, action_posterior):  # type: ignore
        return None


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
INTEGRATOR_LEADER_TOTAL = app_metrics.get_counter(
    "somabrain_integrator_leader_total",
    "GlobalFrame leader selection count",
    labelnames=["leader"],
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

# OPA decision counters
INTEGRATOR_OPA_ALLOW_TOTAL = app_metrics.get_counter(
    "somabrain_integrator_opa_allow_total",
    "Count of OPA allow decisions in integrator",
)
INTEGRATOR_OPA_DENY_TOTAL = app_metrics.get_counter(
    "somabrain_integrator_opa_deny_total",
    "Count of OPA deny decisions in integrator",
)
INTEGRATOR_OPA_VETO_RATIO = app_metrics.get_gauge(
    "somabrain_integrator_opa_veto_ratio",
    "Ratio of OPA veto (deny) decisions to total decisions (rolling)",
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

# Fusion-normalization (metrics-only seam)
INTEGRATOR_ALPHA = app_metrics.get_gauge(
    "somabrain_integrator_alpha",
    "Current integrator alpha parameter for error->confidence mapping",
)
INTEGRATOR_ALPHA_TARGET = app_metrics.get_gauge(
    "somabrain_integrator_alpha_target",
    "Target regret/entropy composite driving adaptive alpha",
)
INTEGRATOR_KAPPA = app_metrics.get_gauge(
    "somabrain_integrator_kappa",
    "Consistency kappa (1 - JSD) across agent/action posteriors",
    labelnames=["tenant"],
)
INTEGRATOR_KAPPA_HIST = app_metrics.get_histogram(
    "somabrain_integrator_kappa_hist",
    "Distribution of consistency kappa (1 - JSD)",
    labelnames=["tenant"],
    buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
)
INTEGRATOR_NORMALIZED_ERROR = app_metrics.get_gauge(
    "somabrain_integrator_normalized_error",
    "Per-domain normalized prediction error (z-score)",
    labelnames=["domain"],
)
INTEGRATOR_CAND_WEIGHT = app_metrics.get_gauge(
    "somabrain_integrator_candidate_weight",
    "Candidate fusion weight from exp(-alpha * e_norm) (metrics-only)",
    labelnames=["tenant", "domain"],
)

# Cross-thread consistency (agent intent vs next action)
INTEGRATOR_CONSISTENCY = app_metrics.get_gauge(
    "somabrain_integrator_consistency",
    "Feasibility consistency between agent intent and next action",
    labelnames=["tenant"],
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

    def snapshot(
        self, tenant: str
    ) -> Tuple[str, Dict[str, float], Dict[str, DomainObs]]:
        """Return (leader, weights, raw_map) for tenant.

        Stale observations older than stale_seconds are ignored.
        """
        t = (tenant or "public").strip() or "public"
        now = time.time()
        raw = {
            k: v
            for k, v in self._by_tenant.get(t, {}).items()
            if (now - v.ts) <= self._stale
        }
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
        # Initialize tracing (required)
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
        self._soma_compat: bool = os.getenv("SOMA_COMPAT", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        # Serde
        # Lazy import for Avro helpers to avoid import-time dependency for unit tests
        self._bu_schema = None
        self._gf_schema = None
        self._ic_schema = None
        self._cfg_schema = None
        self._avro_bu = None
        self._avro_gf = None
        self._avro_bu_soma = None
        self._avro_ic = None
        self._avro_cfg = None
        try:
            from libs.kafka_cog.avro_schemas import load_schema  # type: ignore

            self._bu_schema = load_schema("belief_update")
            self._gf_schema = load_schema("global_frame")
            try:
                self._cfg_schema = load_schema("config_update")
            except Exception:
                self._cfg_schema = None
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
                if self._cfg_schema is not None:
                    try:
                        self._avro_cfg = AvroSerde(self._cfg_schema)
                    except Exception:
                        self._avro_cfg = None
            except Exception:
                self._avro_bu = None
                self._avro_gf = None
                self._avro_bu_soma = None
                self._avro_ic = None
                self._avro_cfg = None
        except Exception:
            # Avro path unavailable; JSON fallback will be used
            self._bu_schema = None
            self._gf_schema = None
            self._ic_schema = None
            self._cfg_schema = None
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
        # Allow both legacy and namespaced env var for shadow routing ratio
        try:
            self._shadow_ratio = float(
                os.getenv("SOMABRAIN_SHADOW_RATIO", "")
                or os.getenv("SHADOW_RATIO", "0.0")
                or "0.0"
            )
        except Exception:
            self._shadow_ratio = 0.0
        self._frames_seen = 0
        self._shadow_sent = 0
        # Local OPA decision counters for ratio calculations
        self._opa_allow_count: int = 0
        self._opa_deny_count: int = 0
        # Track leader switches per tenant
        self._last_leader: Dict[str, str] = {}
        # Track recent kappa per tenant for rationale context
        self._last_kappa: Dict[str, float] = {}
        # Confidence enforcement from delta_error
        try:
            self._alpha = float(os.getenv("SOMABRAIN_INTEGRATOR_ALPHA", "2.0") or "2.0")
        except Exception:
            self._alpha = 2.0
        try:
            INTEGRATOR_ALPHA.set(float(self._alpha))
        except Exception:
            pass
        # Default ON: enforce confidence normalization from delta_error unless explicitly disabled
        self._enforce_conf = os.getenv(
            "SOMABRAIN_INTEGRATOR_ENFORCE_CONF", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        
        # Fusion normalization with adaptive alpha
        self._norm_enabled = os.getenv(
            "ENABLE_FUSION_NORMALIZATION", "0"
        ).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        
        # Adaptive alpha for fusion normalization
        try:
            self._adaptive_alpha = float(os.getenv("INTEGRATOR_ADAPTIVE_ALPHA", "2.0"))
            self._alpha_min = float(os.getenv("INTEGRATOR_ALPHA_MIN", "0.1"))
            self._alpha_max = float(os.getenv("INTEGRATOR_ALPHA_MAX", "5.0"))
            self._alpha_target_regret = float(os.getenv("INTEGRATOR_TARGET_REGRET", "0.15"))
            self._alpha_eta = float(os.getenv("INTEGRATOR_ALPHA_ETA", "0.05"))  # step size
        except Exception:
            self._adaptive_alpha = 2.0
            self._alpha_min = 0.1
            self._alpha_max = 5.0
            self._alpha_target_regret = 0.15
            self._alpha_eta = 0.05
        # Rolling stats per domain for delta_error normalization (Welford)
        self._stats = {
            "state": {"n": 0, "mean": 0.0, "m2": 0.0},
            "agent": {"n": 0, "mean": 0.0, "m2": 0.0},
            "action": {"n": 0, "mean": 0.0, "m2": 0.0},
        }
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

            self._opa_url = (
                _settings.opa_url or os.getenv("SOMABRAIN_OPA_URL") or ""
            ).strip()
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
                os.getenv("SOMA_OPA_FAIL_CLOSED", "false").lower()
                in ("1", "true", "yes", "on")
            )

    def _start_health_server(self) -> None:
        try:
            from fastapi import FastAPI
            import uvicorn  # type: ignore

            app = FastAPI(title="IntegratorHub Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "integrator_hub"}

            @app.get("/tau")
            async def _tau_ep():  # type: ignore
                try:
                    return {"tau": float(self._sm._tau)}
                except Exception:
                    return {"tau": None}

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
                topics.extend(
                    [
                        "soma.belief.state",
                        "soma.belief.agent",
                        "soma.belief.action",
                    ]
                )
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
                tenant = (
                    str(metadata.get("tenant", "public") or "public").strip()
                    or "public"
                )
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
        # Try Avro config_update first, then JSON fallback
        if getattr(self, "_avro_cfg", None) is not None:
            try:
                rec = self._avro_cfg.deserialize(payload)  # type: ignore[attr-defined]
                if isinstance(rec, dict):
                    return rec
            except Exception:
                pass
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    def _publish_frame(self, frame: Dict[str, Any]) -> None:
        if not self._producer:
            return
        # Shadow routing decision (duplicate to shadow topic, never suppress primary)
        route_to_shadow = False
        try:
            import random as _random

            route_to_shadow = (self._shadow_ratio > 0.0) and (
                _random.random() < self._shadow_ratio
            )
        except Exception:
            route_to_shadow = False
        try:
            # Always send primary global frame
            self._producer.send("cog.global.frame", value=self._encode_frame(frame))
            # Optionally duplicate to shadow topic for evaluation
            if route_to_shadow:
                self._producer.send(
                    "cog.integrator.context.shadow", value=self._encode_frame(frame)
                )
                try:
                    INTEGRATOR_SHADOW_TOTAL.inc()
                    self._shadow_sent += 1
                    if self._frames_seen > 0:
                        INTEGRATOR_SHADOW_RATIO.set(
                            max(
                                0.0,
                                min(
                                    1.0,
                                    float(self._shadow_sent) / float(self._frames_seen),
                                ),
                            )
                        )
                except Exception:
                    pass
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
        derr = float(ev.get("delta_error", 0.0))
        # Update rolling stats for normalization (metrics-only)
        try:
            s = self._stats.get(domain)
            if s is not None:
                s["n"] += 1
                n = s["n"]
                delta = derr - s["mean"]
                s["mean"] += delta / float(n)
                s["m2"] += delta * (derr - s["mean"])
        except Exception:
            pass
        # Normalize confidence if enforcement enabled or missing/invalid
        conf_in = ev.get("confidence")
        conf_norm: float
        try:
            conf_norm = float(conf_in) if conf_in is not None else float("nan")
        except Exception:
            conf_norm = float("nan")
        need_norm = self._enforce_conf or (
            not (isinstance(conf_in, (int, float)) and 0.0 <= conf_norm <= 1.0)
        )
        if need_norm:
            try:
                conf_norm = math.exp(-max(0.0, float(derr)) * float(self._alpha))
            except Exception:
                conf_norm = 0.0
        conf = float(conf_norm)
        ts = time.time()
        self._sm.update(
            tenant, domain, DomainObs(ts=ts, confidence=conf, delta_error=derr, meta=ev)
        )
        leader, weights, raw = self._sm.snapshot(tenant)
        # Cross-thread consistency metric (set when both posteriors available)
        try:
            a_ob = raw.get("agent")
            x_ob = raw.get("action")
            a_post = (
                a_ob.meta.get("posterior")
                if a_ob and isinstance(a_ob.meta, dict)
                else None
            )
            x_post = (
                x_ob.meta.get("posterior")
                if x_ob and isinstance(x_ob.meta, dict)
                else None
            )
            score = consistency_score(a_post, x_post)
            if score is not None:
                INTEGRATOR_CONSISTENCY.labels(tenant=tenant).set(float(score))
                # Derive kappa (1 - JSD) if distributions present
                try:
                    kappa = self._compute_kappa(a_post, x_post)
                    if kappa is not None:
                        INTEGRATOR_KAPPA.labels(tenant=tenant).set(float(kappa))
                        try:
                            INTEGRATOR_KAPPA_HIST.labels(tenant=tenant).observe(
                                float(max(0.0, min(1.0, kappa)))
                            )
                        except Exception:
                            pass
                        try:
                            self._last_kappa[tenant] = float(kappa)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        # Normalization pathway: compute normalized error and candidate weights; optionally use for selection
        fused_weights: Optional[Dict[str, float]] = None
        adaptive_regret_sample: Optional[float] = None
        if self._norm_enabled:
            try:
                # Emit normalized error for the current domain
                s = self._stats.get(domain) or {"n": 0}
                if s.get("n", 0) > 1:
                    var = max(0.0, float(s["m2"]) / float(s["n"] - 1))
                    std = (var**0.5) if var > 0.0 else 1.0
                    e_norm = (derr - float(s["mean"])) / max(1e-9, std)
                else:
                    e_norm = 0.0
                INTEGRATOR_NORMALIZED_ERROR.labels(domain=domain).set(float(e_norm))
            except Exception:
                pass
            # Candidate weights over currently available domains (raw)
            try:
                cand_exps: Dict[str, float] = {}
                for d, ob in raw.items():
                    ss = self._stats.get(d) or {"n": 0}
                    if ss.get("n", 0) > 1:
                        var = max(0.0, float(ss["m2"]) / float(ss["n"] - 1))
                        std = (var**0.5) if var > 0.0 else 1.0
                        e_nd = (float(ob.delta_error) - float(ss["mean"])) / max(
                            1e-9, std
                        )
                    else:
                        e_nd = 0.0
                    try:
                        cand_exps[d] = math.exp(-float(self._alpha) * float(e_nd))
                    except Exception:
                        cand_exps[d] = 1.0
                Zc = sum(cand_exps.values()) or 1.0
                fused_weights = {d: float(v / Zc) for d, v in cand_exps.items()}
                for d, v in fused_weights.items():
                    INTEGRATOR_CAND_WEIGHT.labels(tenant=tenant, domain=d).set(v)
                # Simple regret proxy: 1 - max weight (confidence of leader proxy)
                try:
                    adaptive_regret_sample = max(0.0, 1.0 - max(fused_weights.values()))
                except Exception:
                    adaptive_regret_sample = None
            except Exception:
                pass
        # If normalization flag enabled and we computed fused_weights, use it for leader selection and rationale
        if self._norm_enabled and fused_weights is not None and fused_weights:
            # Merge fused weights into the 3-domain map (fill missing domains with 0)
            norm_weights = {"state": 0.0, "agent": 0.0, "action": 0.0}
            norm_weights.update({k: float(v) for k, v in fused_weights.items()})
            weights = norm_weights
            leader = max(weights.items(), key=lambda kv: kv[1])[0]
        # Adaptive alpha update (after fused weights computed)
        if self._norm_enabled and adaptive_regret_sample is not None:
            try:
                # Composite target: move alpha up if regret_mean > target, down otherwise
                diff = float(adaptive_regret_sample) - float(self._alpha_target_regret)
                self._adaptive_alpha = max(
                    self._alpha_min,
                    min(self._alpha_max, self._adaptive_alpha + self._alpha_eta * diff),
                )
                # Apply to operational alpha used in confidence normalization
                self._alpha = float(self._adaptive_alpha)
                INTEGRATOR_ALPHA.set(self._alpha)
                INTEGRATOR_ALPHA_TARGET.set(float(self._alpha_target_regret))
            except Exception:
                pass
        # Leader switch metric
        try:
            last = self._last_leader.get(tenant)
            if last is not None and last != leader:
                INTEGRATOR_LEADER_SWITCHES.labels(tenant=tenant).inc()
            self._last_leader[tenant] = leader
        except Exception:
            pass
        # Observe entropy of weights (normalize by log(3) so range is 0..1)
        H_norm = None
        try:
            import math as _math

            ps = [
                max(1e-12, float(weights.get(k, 0.0)))
                for k in ("state", "agent", "action")
            ]
            Z = sum(ps) or 1.0
            ps = [p / Z for p in ps]
            H = -sum(p * _math.log(p) for p in ps) / _math.log(3.0)
            H_norm = max(0.0, min(1.0, float(H)))
            INTEGRATOR_ENTROPY.labels(tenant=tenant).observe(H_norm)
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
        fusion_note = "fusion=normalized" if (self._norm_enabled and fused_weights) else "fusion=softmax"
        rationale = f"{fusion_note} tau=1.0 domains={','.join(sorted(k for k in weights.keys() if weights[k]>0))}"
        # Append recent kappa/entropy context if available
        try:
            k = self._last_kappa.get(tenant)
            if k is not None:
                rationale += f"; kappa={k:.3f}"
        except Exception:
            pass
        try:
            if H_norm is not None:
                rationale += f" H={H_norm:.3f}"
        except Exception:
            pass
        # Optional OPA gating/adjustment
        leader_adj = leader
        policy_allowed = True
        if self._opa_url and self._opa_policy:
            allowed, new_leader, opa_note = self._opa_decide(
                tenant, leader, weights, ev
            )
            if not allowed:
                try:
                    INTEGRATOR_OPA_DENY_TOTAL.inc()
                except Exception:
                    pass
                # Update local counters and ratio gauge
                try:
                    self._opa_deny_count += 1
                    total = self._opa_allow_count + self._opa_deny_count
                    if total > 0:
                        INTEGRATOR_OPA_VETO_RATIO.set(
                            float(self._opa_deny_count) / float(total)
                        )
                except Exception:
                    pass
                # If fail-closed, drop frame; otherwise continue with original leader
                if self._opa_fail_closed:
                    return None
                else:
                    policy_allowed = False
                    rationale += "; opa=deny"
            else:
                try:
                    INTEGRATOR_OPA_ALLOW_TOTAL.inc()
                except Exception:
                    pass
                # Update local counters and ratio gauge
                try:
                    self._opa_allow_count += 1
                    total = self._opa_allow_count + self._opa_deny_count
                    if total > 0:
                        INTEGRATOR_OPA_VETO_RATIO.set(
                            float(self._opa_deny_count) / float(total)
                        )
                except Exception:
                    pass
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
        # Count leader selections
        try:
            INTEGRATOR_LEADER_TOTAL.labels(leader=leader_adj).inc()
        except Exception:
            pass
        return gf

    @staticmethod
    def _compute_kappa(agent_post: Any, action_post: Any) -> Optional[float]:
        """Compute kappa = 1 - JSD(P_agent || P_action) if both are dicts of probabilities.

        Expects each posterior to hold a probability mapping under keys 'intent_probs' and
        'action_probs' respectively (fallback to direct mapping if already probability dict).
        Returns None if cannot compute.
        """
        try:
            if not isinstance(agent_post, dict) or not isinstance(action_post, dict):
                return None
            # Extract probability maps
            ap = agent_post.get("intent_probs") if "intent_probs" in agent_post else agent_post
            xp = action_post.get("action_probs") if "action_probs" in action_post else action_post
            if not isinstance(ap, dict) or not isinstance(xp, dict):
                return None
            # Unified key set
            keys = set(ap.keys()) | set(xp.keys())
            if not keys:
                return None
            # Normalize each distribution
            def _norm(m: Dict[str, Any]) -> Dict[str, float]:
                vals = {k: float(m.get(k, 0.0)) for k in keys}
                Z = sum(vals.values()) or 1.0
                return {k: max(0.0, vals[k] / Z) for k in keys}
            pa = _norm(ap)
            px = _norm(xp)
            # Mixture
            pm = {k: 0.5 * (pa[k] + px[k]) for k in keys}
            def _kl(p: Dict[str, float], q: Dict[str, float]) -> float:
                acc = 0.0
                for k in keys:
                    pk = max(1e-12, p[k])
                    qk = max(1e-12, q[k])
                    acc += pk * _math.log(pk / qk)
                return acc
            jsd = 0.5 * _kl(pa, pm) + 0.5 * _kl(px, pm)
            # Normalize JSD by log(|keys|) to keep in [0,1]
            denom = _math.log(float(len(keys))) if len(keys) > 1 else 1.0
            jsd_norm = min(1.0, max(0.0, jsd / denom))
            kappa = 1.0 - jsd_norm
            return kappa
        except Exception:
            return None

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
            return (
                allow,
                (str(new_leader) if isinstance(new_leader, str) else None),
                note,
            )
        except Exception:
            INTEGRATOR_ERRORS.labels(stage="opa").inc()
            INTEGRATOR_OPA_LAT.observe(max(0.0, time.perf_counter() - t0))
            return (not self._opa_fail_closed), None, ""

    def run_forever(self) -> None:
        self._ensure_clients()
        assert self._consumer is not None
        # Persistent outer loop: KafkaConsumer iterator stops after consumer_timeout_ms with no records.
        while True:
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
                                    try:
                                        print(
                                            f"integrator_hub: applied config_update tau={float(temp):.3f}"
                                        )
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                            # Observe optional per-domain lambda attribution (no behavior change yet)
                            try:
                                for dkey, label in (
                                    ("lambda_state", "state"),
                                    ("lambda_agent", "agent"),
                                    ("lambda_action", "action"),
                                ):
                                    val = cfg.get(dkey)
                                    if isinstance(val, (int, float)):
                                        # Reuse candidate weight gauge namespace or create a dedicated gauge if needed.
                                        # For simplicity, expose as somabrain_integrator_candidate_weight with domain label 'lambda_<domain>'
                                        INTEGRATOR_CAND_WEIGHT.labels(
                                            tenant=self._tenant_from(cfg),
                                            domain=f"lambda_{label}",
                                        ).set(float(val))
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
                    with self._tracer.start_as_current_span(
                        "integrator_process_update"
                    ):
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
                        weights_out = (
                            dict(frame.get("weights", {}))
                            if isinstance(frame.get("weights"), dict)
                            else {}
                        )
                        self._publish_soma_context(
                            leader_out, weights_out, frame, policy_allowed
                        )
                    # Cache and metrics
                    self._cache_frame(self._tenant_from(ev), frame)
                    INTEGRATOR_PUBLISHED.labels(tenant=self._tenant_from(ev)).inc()
                except Exception:
                    INTEGRATOR_ERRORS.labels(stage="loop").inc()


def main() -> None:  # pragma: no cover - manual run path
    ff = os.getenv("SOMABRAIN_FF_COG_INTEGRATOR", "").strip().lower()
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not (ff in ("1", "true", "yes", "on") or composite):
        import logging
        from somabrain.metrics import get_counter

        logging.info(
            "integrator_hub: disabled; set SOMABRAIN_FF_COG_INTEGRATOR=1 or ENABLE_COG_THREADS=1 to enable"
        )
        try:
            _MX_INT_DISABLED = get_counter(
                "somabrain_integrator_disabled_total",
                "Count of integrator hub disabled exits",
            )
            _MX_INT_DISABLED.inc()
        except Exception:
            pass
        return
    hub = IntegratorHub()
    import logging
    from somabrain.metrics import get_counter

    logging.info("Starting Integrator Hub...")
    try:
        _MX_INT_INIT = get_counter(
            "somabrain_integrator_init_total",
            "Number of Integrator Hub initializations",
        )
        _MX_INT_INIT.inc()
    except Exception:
        pass
    hub.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
