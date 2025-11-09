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
import json
import os
from datetime import datetime, timezone

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


@dataclass
class DriftState:
    """Current drift state for a domain/tenant."""
    entropy_history: deque[float]
    regret_history: deque[float]
    last_drift_time: float
    is_stable: bool = True


class DriftDetector:
    """
    Detects drift in predictor performance and triggers rollback.
    
    Monitors entropy and regret metrics to detect when the system
    is drifting from optimal performance.
    """
    
    def __init__(self, config: DriftConfig = DriftConfig()):
        self.config = config
        self.states: Dict[str, DriftState] = {}
        self.enabled = os.getenv("ENABLE_DRIFT_DETECTION", "0").lower() in {
            "1", "true", "yes", "on"
        }
        self.rollback_enabled = os.getenv("ENABLE_AUTO_ROLLBACK", "0").lower() in {
            "1", "true", "yes", "on"
        }
        # Producer for drift events (strict: Avro mandatory when enabled)
        if self.enabled:
            try:
                self._producer = make_producer()
            except Exception:
                # In strict mode, producer creation may fail in tests without Kafka; continue logic-only
                self._producer = None
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
            
            drift_detected = (
                avg_entropy > self.config.entropy_threshold or
                avg_regret > self.config.regret_threshold
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
                
                return True
            
            # Mark as stable
            state.is_stable = True
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
        
        print(f"DRIFT_ROLLBACK: {json.dumps(rollback_event)}")

        # Best-effort: disable advanced features to stabilize system
        try:
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
                    json.dump(
                        {
                            "ts": int(time.time()),
                            "tenant": tenant,
                            "domain": domain,
                            "trigger": trigger,
                            "disabled": [
                                "ENABLE_FUSION_NORMALIZATION",
                                "ENABLE_CONSISTENCY_CHECKS",
                                "ENABLE_CALIBRATION",
                            ],
                        },
                        f,
                        indent=2,
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Emit conservative config update to reduce exploration
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
                self._producer.send(TOPICS.get("config", "cog.config.updates"), value=cfg)
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