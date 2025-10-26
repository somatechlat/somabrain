"""
Segmentation Service
--------------------

Consumes GlobalFrame events and emits SegmentBoundary records when the leader
domain changes or when a maximum dwell threshold is reached.

Optionally, supports a CPD (change-point detection) mode that consumes
BeliefUpdate events (Δerror streams) from state/agent/action domains and
emits SegmentBoundary on statistically significant shifts.

Design choices:
- Stateless Kafka I/O around a small, testable Segmenter core that tracks the
  current leader and last-change timestamp.
- Uses Avro schemaless serde if `fastavro` is installed; otherwise falls back
  to JSON payloads for local/dev.
- Metrics are exported via somabrain.metrics (counters + histogram).

Environment variables:
- SOMABRAIN_KAFKA_URL: bootstrap servers (default localhost:30001)
- SOMABRAIN_FF_COG_SEGMENTATION: enable/disable service (default off)
- SOMABRAIN_SEGMENT_MODE: 'leader' (default) or 'cpd'
- SOMABRAIN_SEGMENT_MAX_DWELL_MS: optional max dwell; emits boundary even if
    leader hasn't changed (default 0 meaning disabled)
- SOMABRAIN_CPD_MIN_SAMPLES: warmup samples before testing (default 20)
- SOMABRAIN_CPD_Z: Z-score threshold vs running std (default 4.0)
- SOMABRAIN_CPD_MIN_GAP_MS: minimum gap between boundaries per domain (default 1000)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
import threading
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

try:
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


# --- CPD mode support -------------------------------------------------------

@dataclass
class Update:
    ts: str
    tenant: str
    domain: str
    delta_error: float


def _parse_update(value: bytes, serde: Optional[AvroSerde]) -> Optional[Update]:
    if value is None:
        return None
    try:
        if serde is not None:
            data = serde.deserialize(value)  # type: ignore[arg-type]
        else:
            data = json.loads(value.decode("utf-8"))
        ts = str(data.get("ts") or "")
        tenant = str((data.get("tenant") or "public").strip() or "public")
        domain = str((data.get("domain") or "").strip())
        de = data.get("delta_error")
        delta_error = float(de if de is not None else 0.0)
        if not ts or not domain:
            return None
        return Update(ts=ts, tenant=tenant, domain=domain, delta_error=delta_error)
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


class _Welford:
    """Online mean/std estimator.

    Keeps running mean and variance using Welford's algorithm.
    """

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2

    @property
    def variance(self) -> float:
        return self.M2 / self.n if self.n > 0 else 0.0

    @property
    def std(self) -> float:
        import math

        return math.sqrt(self.variance)


class CPDSegmenter:
    """Change-point detection over delta_error per tenant:domain.

    Evidence values:
    - "cpd" when Z-score threshold exceeded vs running std after warmup
    - "max_dwell" when no CPD but dwell exceeds threshold
    """

    def __init__(self, max_dwell_ms: int, min_samples: int, z_threshold: float, min_gap_ms: int, min_std: float = 0.02):
        self.max_dwell_ms = max(0, int(max_dwell_ms))
        self.min_samples = max(1, int(min_samples))
        self.z = float(z_threshold)
        self.min_gap_ms = max(0, int(min_gap_ms))
        self.min_std = float(min_std)
        # State per tenant:domain
        self._stats: Dict[Tuple[str, str], _Welford] = {}
        self._last_change_ms: Dict[Tuple[str, str], Optional[int]] = {}

    @staticmethod
    def _parse_ts(ts: str) -> int:
        return Segmenter._parse_ts(ts)

    def observe(self, ts: str, tenant: str, domain: str, delta_error: float) -> Optional[Tuple[str, str, int, str]]:
        key = ((tenant or "public").strip() or "public", (domain or "").strip())
        if not key[1]:
            return None
        now_ms = self._parse_ts(ts)
        st = self._stats.get(key)
        if st is None:
            st = _Welford()
            self._stats[key] = st
            self._last_change_ms[key] = now_ms
        # Dwell boundary first
        last_change = self._last_change_ms.get(key)
        if (
            self.max_dwell_ms > 0
            and last_change is not None
            and now_ms - last_change >= self.max_dwell_ms
        ):
            self._last_change_ms[key] = now_ms
            dwell = now_ms - (last_change or now_ms)
            return (key[1], ts, int(dwell), "max_dwell")

        # Test threshold against PRE-update stats to avoid diluting spike
        if st.n >= self.min_samples:
            std = max(self.min_std, st.std)
            z = abs((float(delta_error) - st.mean) / std)
            if z >= self.z:
                # Respect min_gap guard
                if last_change is not None and self.min_gap_ms > 0 and (now_ms - last_change) < self.min_gap_ms:
                    return None
                self._last_change_ms[key] = now_ms
                dwell = now_ms - (last_change or now_ms)
                # Reset stats to avoid repeated triggers on same regime
                self._stats[key] = _Welford()
                return (key[1], ts, int(dwell), "cpd")
        # No trigger; update stats and continue
        st.update(float(delta_error))
        return None


class HazardSegmenter:
    """Two-state HMM-style hazard-based change detector per tenant:domain.

    States: STABLE (0) and VOLATILE (1)
    - Transition probability lambda controls switching tendency between states.
    - Emission model: Normal with mean=running mean (from STABLE) and
      std = sigma_s for STABLE, and k * sigma_s for VOLATILE (broader).

    Evidence values:
    - "hmm" when MAP state flips with min-gap respected
    - "max_dwell" when dwell exceeds threshold regardless of state

    Parameters
    ----------
    max_dwell_ms : int
        Maximum dwell before forcing a boundary (0 to disable)
    hazard_lambda : float
        Transition probability between states per observation (0..1)
    vol_sigma_mult : float
        Multiplier applied to sigma in VOLATILE state
    min_samples : int
        Warmup samples before decisions (to estimate mean/std)
    min_gap_ms : int
        Minimum time gap between boundaries for a key
    min_std : float
        Lower bound on sigma to avoid degeneracy
    """

    def __init__(
        self,
        max_dwell_ms: int,
        hazard_lambda: float,
        vol_sigma_mult: float,
        min_samples: int,
        min_gap_ms: int,
        min_std: float = 0.02,
    ) -> None:
        self.max_dwell_ms = max(0, int(max_dwell_ms))
        self.lmb = min(1.0, max(0.0, float(hazard_lambda)))
        self.k = max(1.0, float(vol_sigma_mult))
        self.min_samples = max(1, int(min_samples))
        self.min_gap_ms = max(0, int(min_gap_ms))
        self.min_std = float(min_std)
        # Per key (tenant:domain) state
        self._stats: Dict[Tuple[str, str], _Welford] = {}
        self._last_change_ms: Dict[Tuple[str, str], Optional[int]] = {}
        self._map_state: Dict[Tuple[str, str], int] = {}

    @staticmethod
    def _parse_ts(ts: str) -> int:
        return Segmenter._parse_ts(ts)

    @staticmethod
    def _log_norm_pdf(x: float, mu: float, sigma: float) -> float:
        import math

        s = max(1e-9, float(sigma))
        z = (x - mu) / s
        # log pdf of Normal
        return -0.5 * (z * z) - (math.log(s) + 0.5 * math.log(2 * math.pi))

    def observe(self, ts: str, tenant: str, domain: str, delta_error: float) -> Optional[Tuple[str, str, int, str]]:
        key = ((tenant or "public").strip() or "public", (domain or "").strip())
        if not key[1]:
            return None
        now_ms = self._parse_ts(ts)
        st = self._stats.get(key)
        if st is None:
            st = _Welford()
            self._stats[key] = st
            self._last_change_ms[key] = now_ms
            self._map_state[key] = 0  # assume STABLE at start
        # Dwell enforcement
        last_change = self._last_change_ms.get(key)
        if (
            self.max_dwell_ms > 0
            and last_change is not None
            and now_ms - last_change >= self.max_dwell_ms
        ):
            self._last_change_ms[key] = now_ms
            dwell = now_ms - (last_change or now_ms)
            return (key[1], ts, int(dwell), "max_dwell")

        x = float(delta_error)
        # Warmup
        if st.n < self.min_samples:
            st.update(x)
            return None
        mu = st.mean
        sigma = max(self.min_std, st.std)
        # Prior on state from previous MAP with symmetric transitions
        prev_state = int(self._map_state.get(key, 0))
        pS_prev = 1.0 if prev_state == 0 else 0.0
        pV_prev = 1.0 - pS_prev
        # Predict step
        pS_pred = (1.0 - self.lmb) * pS_prev + self.lmb * pV_prev
        pV_pred = self.lmb * pS_prev + (1.0 - self.lmb) * pV_prev
        # Emission log-likelihoods (avoid underflow)
        import math as _math
        log_like_S = self._log_norm_pdf(x, mu, sigma)
        log_like_V = self._log_norm_pdf(x, mu, self.k * sigma)
        # Update (log-domain)
        eps = 1e-18
        log_post_S = _math.log(max(eps, pS_pred)) + log_like_S
        log_post_V = _math.log(max(eps, pV_pred)) + log_like_V
        new_state = 0 if log_post_S >= log_post_V else 1
        # Boundary on state flip with min gap
        if new_state != prev_state:
            if last_change is None or (self.min_gap_ms == 0) or ((now_ms - last_change) >= self.min_gap_ms):
                self._map_state[key] = new_state
                self._last_change_ms[key] = now_ms
                dwell = now_ms - (last_change or now_ms)
                # Update stats reset on flip to avoid stale params
                self._stats[key] = _Welford()
                self._stats[key].update(x)
                return (key[1], ts, int(dwell), "hmm")
        # No boundary; update STABLE stats when STABLE more likely than VOLATILE
        if log_post_S >= log_post_V:
            st.update(x)
        return None


class SegmentationService:
    def __init__(self):
        _init_metrics()
        init_tracing()
        self._tracer = get_tracer("somabrain.segmentation_service")
        # Start health server for k8s probes
        try:
            if os.getenv("HEALTH_PORT"):
                self._start_health_server()
        except Exception:
            pass
        self._serde_in: Optional[AvroSerde] = None
        self._serde_out: Optional[AvroSerde] = None
        self._serde_update: Optional[AvroSerde] = None
        try:
            if load_schema is not None and AvroSerde is not None:
                gf_schema = load_schema("global_frame")
                sb_schema = load_schema("segment_boundary")
                self._serde_in = AvroSerde(gf_schema)
                self._serde_out = AvroSerde(sb_schema)
                # Optional for CPD mode
                try:
                    bu_schema = load_schema("belief_update")
                    self._serde_update = AvroSerde(bu_schema)
                except Exception:
                    self._serde_update = None
        except Exception:
            self._serde_in = None
            self._serde_out = None
            self._serde_update = None
        max_dwell_ms = int(os.getenv("SOMABRAIN_SEGMENT_MAX_DWELL_MS", "0") or "0")
        self._segmenter = Segmenter(max_dwell_ms=max_dwell_ms)
        # CPD mode parameters
        self._cpd = CPDSegmenter(
            max_dwell_ms=max_dwell_ms,
            min_samples=int(os.getenv("SOMABRAIN_CPD_MIN_SAMPLES", "20") or "20"),
            z_threshold=float(os.getenv("SOMABRAIN_CPD_Z", "4.0") or "4.0"),
            min_gap_ms=int(os.getenv("SOMABRAIN_CPD_MIN_GAP_MS", "1000") or "1000"),
            min_std=float(os.getenv("SOMABRAIN_CPD_MIN_STD", "0.02") or "0.02"),
        )
        self._mode = (os.getenv("SOMABRAIN_SEGMENT_MODE", "leader") or "leader").strip().lower()

    def _start_health_server(self) -> None:
        try:
            from fastapi import FastAPI
            import uvicorn  # type: ignore

            app = FastAPI(title="Segmentation Health")

            @app.get("/healthz")
            async def _hz():  # type: ignore
                return {"ok": True, "service": "segmentation"}

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

    def run_forever(self) -> None:  # pragma: no cover - integration loop
        if KafkaConsumer is None or KafkaProducer is None:
            print("Kafka client not available; segmentation service idle.")
            while True:
                time.sleep(60)
        # Select topics based on mode
        if self._mode == "cpd" or self._mode == "hazard":
            topics = [
                "cog.state.updates",
                "cog.agent.updates",
                "cog.action.updates",
            ]
        else:
            topics = ["cog.global.frame"]
        consumer = KafkaConsumer(
            *topics,
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
                if self._mode == "cpd":
                    with self._tracer.start_as_current_span("segmentation_cpd"):
                        upd = _parse_update(msg.value, self._serde_update)
                        if upd is None:
                            continue
                        out = self._cpd.observe(upd.ts, upd.tenant, upd.domain, upd.delta_error)
                        if out is None:
                            continue
                        domain, boundary_ts, dwell_ms, evidence = out
                        tenant = upd.tenant
                elif self._mode == "hazard":
                    with self._tracer.start_as_current_span("segmentation_hazard"):
                        upd = _parse_update(msg.value, self._serde_update)
                        if upd is None:
                            continue
                        # Initialize hazard segmenter lazily
                        if not hasattr(self, "_hazard"):
                            setattr(
                                self,
                                "_hazard",
                                HazardSegmenter(
                                    max_dwell_ms=int(os.getenv("SOMABRAIN_SEGMENT_MAX_DWELL_MS", "0") or "0"),
                                    hazard_lambda=float(os.getenv("SOMABRAIN_HAZARD_LAMBDA", "0.02") or "0.02"),
                                    vol_sigma_mult=float(os.getenv("SOMABRAIN_HAZARD_VOL_MULT", "3.0") or "3.0"),
                                    min_samples=int(os.getenv("SOMABRAIN_HAZARD_MIN_SAMPLES", "20") or "20"),
                                    min_gap_ms=int(os.getenv("SOMABRAIN_CPD_MIN_GAP_MS", "1000") or "1000"),
                                    min_std=float(os.getenv("SOMABRAIN_CPD_MIN_STD", "0.02") or "0.02"),
                                ),
                            )
                        hz: HazardSegmenter = getattr(self, "_hazard")
                        out = hz.observe(upd.ts, upd.tenant, upd.domain, upd.delta_error)
                        if out is None:
                            continue
                        domain, boundary_ts, dwell_ms, evidence = out
                        tenant = upd.tenant
                else:
                    with self._tracer.start_as_current_span("segmentation_leader"):
                        frame = _parse_frame(msg.value, self._serde_in)
                        if frame is None:
                            continue
                        out = self._segmenter.observe(frame.ts, frame.leader, frame.tenant)
                        if out is None:
                            continue
                        domain, boundary_ts, dwell_ms, evidence = out
                        tenant = frame.tenant

                record = {
                    "tenant": tenant,
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
                            BOUNDARY_EMITTED.labels(domain=domain, evidence=evidence).inc()
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
    composite = os.getenv("ENABLE_COG_THREADS", "").strip().lower() in ("1", "true", "yes", "on")
    ff = os.getenv("SOMABRAIN_FF_COG_SEGMENTATION", "0").strip().lower()
    if ff not in ("1", "true", "yes", "on") and not composite:
        print("Segmentation feature flag disabled; exiting.")
        return
    svc = SegmentationService()
    svc.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
