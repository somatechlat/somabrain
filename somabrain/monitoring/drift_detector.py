"""
Drift detection and automated rollback service for SomaBrain.

Implements drift detection based on entropy and regret metrics,
with automated rollback capabilities.

Version: 1.0.0 - Roadmap Implementation
"""

import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque
import os
from datetime import datetime, timezone
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

from somabrain.common.kafka import TOPICS, make_producer, encode  # type: ignore
from somabrain.common.events import compute_regret_from_confidence  # type: ignore

# Removed legacy kafka-python optional imports (strict mode)


try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


@dataclass
class DriftConfig:
    """Configuration for drift detection."""
    entropy_threshold: float = 0.8  # Max entropy for stability
    regret_threshold: float = 0.5   # Max regret for stability
    window_size: int = 100         # Rolling window size
    min_samples: int = 20          # Minimum samples before detection
    cooldown_period: int = 60      # Seconds between rollbacks
    adaptive: bool = True          # Enable adaptive baseline thresholds
    ema_alpha: float = 0.05        # EMA smoothing factor for baselines

    def __post_init__(self):
        if not (0.0 < self.ema_alpha <= 1.0):
            raise ValueError("ema_alpha must be in (0,1]")


@dataclass
class DriftState:
    """Current drift state for a domain/tenant."""
    entropy_history: deque[float]
    regret_history: deque[float]
    last_drift_time: float
    is_stable: bool = True
    entropy_baseline: float = 0.0
    regret_baseline: float = 0.0
    baseline_initialized: bool = False


class DriftDetector:
    """
    Detects drift in predictor performance and triggers rollback.
    
    Monitors entropy and regret metrics to detect when the system
    is drifting from optimal performance.
    """
    
    def __init__(self, config: DriftConfig = DriftConfig()):
        self.config = config
        self.states: Dict[str, DriftState] = {}
        # Persistence path (warm restart of baselines + last_drift)
        self._store_path = os.getenv("SOMABRAIN_DRIFT_STORE", "./data/drift/state.json")
        from somabrain.modes import feature_enabled
        self.enabled = feature_enabled("drift")
        self.rollback_enabled = feature_enabled("auto_rollback")
        # Producer for drift events (strict: fail-fast if enabled)
        if self.enabled:
            try:
                self._producer = make_producer()
            except Exception as e:
                raise RuntimeError(f"drift_detector: Kafka producer init failed (strict mode): {e}")
        else:
            self._producer = None
        
        # Metrics
        self.drift_events = (
            metrics.get_counter(
                "somabrain_drift_events_total",
                "Total drift detection events",
                labelnames=["domain", "tenant", "type"]
            ) if metrics else None
        )
        
        self.rollback_events = (
            metrics.get_counter(
                "somabrain_rollback_events_total",
                "Total rollback events",
                labelnames=["domain", "tenant", "trigger"]
            ) if metrics else None
        )
        
        self.entropy_gauge = (
            metrics.get_gauge(
                "somabrain_drift_entropy",
                "Current entropy value",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        
        self.regret_gauge = (
            metrics.get_gauge(
                "somabrain_drift_regret",
                "Current regret value",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )

        # Load persisted state (best-effort, strict parse)
        try:
            self._load_state()
        except Exception:
            # Corrupted or missing store; ignore (warm start semantics only)
            pass
        
    def _get_state_key(self, domain: str, tenant: str) -> str:
        """Get state key for domain/tenant."""
        return f"{domain}:{tenant}"
    
    def _get_or_create_state(self, domain: str, tenant: str) -> DriftState:
        """Get or create drift state for domain/tenant."""
        key = self._get_state_key(domain, tenant)
        if key not in self.states:
            self.states[key] = DriftState(
                entropy_history=deque(maxlen=self.config.window_size),
                regret_history=deque(maxlen=self.config.window_size),
                last_drift_time=0,
                is_stable=True
            )
        return self.states[key]

    # -------- Persistence (minimal JSON) --------
    def _persist_state(self) -> None:
        """Persist baselines and last_drift_time for warm restarts.

        Format:
        {
          "version": 1,
          "updated": <iso>,
          "entries": {
            "domain:tenant": {
               "last_drift_time": <float>,
               "entropy_baseline": <float>,
               "regret_baseline": <float>,
               "baseline_initialized": <bool>
            }, ...
          }
        }
        """
        try:
            import pathlib
            p = pathlib.Path(self._store_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            entries: Dict[str, Any] = {}
            for k, st in self.states.items():
                entries[k] = {
                    "last_drift_time": float(st.last_drift_time),
                    "entropy_baseline": float(st.entropy_baseline),
                    "regret_baseline": float(st.regret_baseline),
                    "baseline_initialized": bool(st.baseline_initialized),
                }
            blob = {
                "version": 1,
                "updated": datetime.now(timezone.utc).isoformat(),
                "entries": entries,
            }
            with p.open("w", encoding="utf-8") as f:
                if yaml is not None:
                    f.write(yaml.safe_dump(blob, sort_keys=True))
                else:
                    f.write(str(blob))
        except Exception:
            pass

    def _load_state(self) -> None:
        """Load previously persisted drift state."""
        import pathlib
        p = pathlib.Path(self._store_path)
        if not p.exists():
            return
        raw = p.read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(raw)
        else:
            import ast
            data = ast.literal_eval(raw)
        if not isinstance(data, dict):
            raise RuntimeError("drift_detector: persisted state root not dict")
        if int(data.get("version", 0)) != 1:
            raise RuntimeError("drift_detector: incompatible state version")
        entries = data.get("entries")
        if not isinstance(entries, dict):
            return
        for k, v in entries.items():
            if not isinstance(v, dict):
                continue
            # Parse key into domain/tenant
            try:
                domain, tenant = k.split(":", 1)
            except Exception:
                continue
            st = self._get_or_create_state(domain, tenant)
            try:
                st.last_drift_time = float(v.get("last_drift_time", 0.0))
                st.entropy_baseline = float(v.get("entropy_baseline", 0.0))
                st.regret_baseline = float(v.get("regret_baseline", 0.0))
                st.baseline_initialized = bool(v.get("baseline_initialized", False))
            except Exception:
                continue
    
    def add_observation(self, domain: str, tenant: str, 
                       confidence: float, entropy: float) -> bool:
        """
        Add observation and detect drift.
        
        Args:
            domain: Predictor domain
            tenant: Tenant identifier
            confidence: Prediction confidence
            entropy: Current entropy value
            
        Returns:
            True if drift detected
        """
        if not self.enabled:
            return False
            
        state = self._get_or_create_state(domain, tenant)
        regret = compute_regret_from_confidence(confidence)
        
        # Update metrics
        if self.entropy_gauge:
            self.entropy_gauge.labels(domain=domain, tenant=tenant).set(entropy)
        if self.regret_gauge:
            self.regret_gauge.labels(domain=domain, tenant=tenant).set(regret)
        
        # Add to history
        with threading.Lock():
            state.entropy_history.append(entropy)
            state.regret_history.append(regret)
            
            # Skip if not enough samples
            if len(state.entropy_history) < self.config.min_samples:
                return False
                
            # Check cooldown
            if time.time() - state.last_drift_time < self.config.cooldown_period:
                return False
            
            # Detect drift
            avg_entropy = sum(state.entropy_history) / len(state.entropy_history)
            avg_regret = sum(state.regret_history) / len(state.regret_history)

            # Adaptive baselines (EMA) for thresholds
            if self.config.adaptive:
                if not state.baseline_initialized:
                    state.entropy_baseline = avg_entropy
                    state.regret_baseline = avg_regret
                    state.baseline_initialized = True
                else:
                    a = self.config.ema_alpha
                    state.entropy_baseline = (1 - a) * state.entropy_baseline + a * avg_entropy
                    state.regret_baseline = (1 - a) * state.regret_baseline + a * avg_regret
                # Dynamic thresholds: baseline + fixed margin (retain safety margin)
                entropy_thresh = max(self.config.entropy_threshold, state.entropy_baseline + 0.10)
                regret_thresh = max(self.config.regret_threshold, state.regret_baseline + 0.10)
            else:
                entropy_thresh = self.config.entropy_threshold
                regret_thresh = self.config.regret_threshold
            
            drift_detected = (
                avg_entropy > entropy_thresh or avg_regret > regret_thresh
            )
            
            if drift_detected:
                state.last_drift_time = time.time()
                state.is_stable = False
                
                # Record metrics
                if self.drift_events:
                    if avg_entropy > self.config.entropy_threshold:
                        self.drift_events.labels(
                            domain=domain, tenant=tenant, type="entropy"
                        ).inc()
                    if avg_regret > self.config.regret_threshold:
                        self.drift_events.labels(
                            domain=domain, tenant=tenant, type="regret"
                        ).inc()
                
                # Trigger rollback if enabled
                if self.rollback_enabled:
                    self._trigger_rollback(domain, tenant, "drift_detected")

                # Emit fusion drift event
                try:
                    if self._producer:
                        record = {
                            "tenant": tenant,
                            "domain": domain,
                            "entropy": float(avg_entropy),
                            "regret": float(avg_regret),
                            "alpha": None,
                            "action": None,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                        # Avro strict serialization
                        payload = encode(record, "fusion_drift_event")
                        topic = TOPICS.get("fusion_drift", "cog.fusion.drift.events")
                        self._producer.send(topic, value=payload)
                except Exception as e:  # pragma: no cover
                    print(f"WARN: failed to emit fusion_drift_event: {e}")
                # Persist immediately on drift detection
                try:
                    self._persist_state()
                except Exception:
                    pass
                
                return True
            
            # Mark as stable
            state.is_stable = True
            # Persist periodically (non-drift path) every ~window_size updates per key
            if len(state.entropy_history) == self.config.window_size:
                self._persist_state()
            return False
    
    def _trigger_rollback(self, domain: str, tenant: str, trigger: str) -> None:
        """Trigger automatic rollback."""
        if self.rollback_events:
            self.rollback_events.labels(
                domain=domain, tenant=tenant, trigger=trigger
            ).inc()
        
        # Log rollback event
        rollback_event = {
            "timestamp": int(time.time()),
            "domain": domain,
            "tenant": tenant,
            "trigger": trigger,
            "action": "rollback_to_baseline"
        }
        
        try:
            if yaml is not None:
                rendered = yaml.safe_dump(rollback_event).strip()
            else:
                rendered = str(rollback_event)
            print(f"DRIFT_ROLLBACK: {rendered}")
        except Exception:
            pass

        # Best-effort: disable advanced features to stabilize system
        try:
            # Disable features only if mode permits rollback
            from somabrain.modes import feature_enabled
            if feature_enabled("auto_rollback"):
                os.environ["ENABLE_FUSION_NORMALIZATION"] = "0"
                os.environ["ENABLE_CONSISTENCY_CHECKS"] = "0"
                os.environ["ENABLE_CALIBRATION"] = "0"
            # Persist overrides for operators/other services to detect
            overrides_path = os.getenv(
                "SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json"
            )
            try:
                import pathlib

                p = pathlib.Path(overrides_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("w", encoding="utf-8") as f:
                    blob = {
                        "ts": int(time.time()),
                        "tenant": tenant,
                        "domain": domain,
                        "trigger": trigger,
                        "disabled": [
                            "ENABLE_FUSION_NORMALIZATION",
                            "ENABLE_CONSISTENCY_CHECKS",
                            "ENABLE_CALIBRATION",
                        ],
                    }
                    if yaml is not None:
                        f.write(yaml.safe_dump(blob, sort_keys=True))
                    else:
                        f.write(str(blob))
            except Exception:
                pass
        except Exception:
            pass

        # Emit conservative config update to reduce exploration (Avro-only)
        try:
            if self._producer:
                cfg = {
                    "learning_rate": 0.01,
                    "exploration_temp": 0.05,
                    "lambda_state": 0.0,
                    "lambda_agent": 0.0,
                    "lambda_action": 0.0,
                    "gamma_state": None,
                    "gamma_agent": None,
                    "gamma_action": None,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                payload_cfg = encode(cfg, "config_update")
                self._producer.send(TOPICS.get("config", "cog.config.updates"), value=payload_cfg)
        except Exception:
            pass

        # Emit structured rollback event (Avro-only)
        try:
            if self._producer:
                rollback = {
                    "tenant": tenant,
                    "domain": domain,
                    "trigger": trigger,
                    "action": "rollback_to_baseline",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                payload_rb = encode(rollback, "fusion_rollback_event")
                self._producer.send(TOPICS.get("fusion_rollback", "cog.fusion.rollback.events"), value=payload_rb)
        except Exception as e:
            print(f"WARN: failed to emit fusion_rollback_event: {e}")
        # Persist state after rollback (contains updated last_drift_time)
        try:
            self._persist_state()
        except Exception:
            pass
    
    def get_drift_status(self, domain: str, tenant: str) -> Dict[str, Any]:
        """Get current drift status for domain/tenant."""
        state = self._get_or_create_state(domain, tenant)
        
        if len(state.entropy_history) == 0:
            return {
                "stable": True,
                "entropy": 0.0,
                "regret": 0.0,
                "samples": 0,
                "last_drift": None
            }
        
        avg_entropy = sum(state.entropy_history) / len(state.entropy_history)
        avg_regret = sum(state.regret_history) / len(state.regret_history)
        
        return {
            "stable": state.is_stable,
            "entropy": avg_entropy,
            "regret": avg_regret,
            "samples": len(state.entropy_history),
            "last_drift": state.last_drift_time
        }
    
    def reset_drift_state(self, domain: str, tenant: str) -> None:
        """Reset drift state for domain/tenant."""
        key = self._get_state_key(domain, tenant)
        if key in self.states:
            state = self.states[key]
            state.entropy_history.clear()
            state.regret_history.clear()
            state.last_drift_time = 0
            state.is_stable = True

    def emit_snapshot(self, domain: str, tenant: str) -> None:
        """Emit a non-drift snapshot event (periodic telemetry)."""
        if not self.enabled or not self._producer:
            return
        state = self._get_or_create_state(domain, tenant)
        if len(state.entropy_history) == 0:
            return
        avg_entropy = sum(state.entropy_history) / len(state.entropy_history)
        avg_regret = sum(state.regret_history) / len(state.regret_history)
        record = {
            "tenant": tenant,
            "domain": domain,
            "entropy": float(avg_entropy),
            "regret": float(avg_regret),
            "alpha": None,
            "action": None,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        try:
            topic = TOPICS.get("fusion_drift", "cog.fusion.drift.events")
            payload = encode(record, "fusion_drift_event")
            self._producer.send(topic, value=payload)
        except Exception as e:  # pragma: no cover
            print(f"WARN: drift snapshot emission failed: {e}")
        # Persist snapshot baseline updates occasionally
        try:
            self._persist_state()
        except Exception:
            pass

    # --- Export helpers ---
    def export_state(self) -> Dict[str, Any]:
        """Return current persisted fields as a dict for operators/tests.

        Structure matches entries payload in persistence file.
        { "domain:tenant": { "last_drift_time": float, "entropy_baseline": float,
                              "regret_baseline": float, "baseline_initialized": bool } }
        """
        out: Dict[str, Any] = {}
        for k, st in self.states.items():
            out[k] = {
                "last_drift_time": float(st.last_drift_time),
                "entropy_baseline": float(st.entropy_baseline),
                "regret_baseline": float(st.regret_baseline),
                "baseline_initialized": bool(st.baseline_initialized),
            }
        return out


# Global drift detector instance
drift_detector = DriftDetector()


class DriftMonitoringService:
    """Service that monitors for drift and manages rollbacks."""
    
    def __init__(self):
        self.detector = drift_detector
        self.enabled = self.detector.enabled
        
    def run_forever(self) -> None:  # pragma: no cover
        """Run drift monitoring service."""
        if not self.enabled:
            print("Drift monitoring disabled")
            return
        
        print("Starting drift monitoring service...")
        
        while True:
            time.sleep(10)  # Passive loop; integrator feeds observations directly.
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall drift monitoring status."""
        return {
            "enabled": self.enabled,
            "rollback_enabled": self.detector.rollback_enabled,
            "config": {
                "entropy_threshold": self.detector.config.entropy_threshold,
                "regret_threshold": self.detector.config.regret_threshold,
                "window_size": self.detector.config.window_size,
                "min_samples": self.detector.config.min_samples
            }
        }


# Global service instance
drift_service = DriftMonitoringService()