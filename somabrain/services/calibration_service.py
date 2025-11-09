"""
Calibration service for SomaBrain predictors.

Provides temperature scaling and calibration metrics for all predictor domains.
"""

import os
import time
import threading
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone

from ..calibration.calibration_metrics import calibration_tracker
from ..common.infra import assert_ready
from ..common.kafka import TOPICS, make_producer, encode

# Removed legacy kafka-python optional imports (strict mode)


try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


class CalibrationService:
    """Service for managing predictor calibration."""
    
    def __init__(self):
        self.enabled = os.getenv("ENABLE_CALIBRATION", "0").lower() in {
            "1", "true", "yes", "on"
        }
        # Producer for calibration snapshots (resilient in tests)
        if self.enabled:
            try:
                self._producer = make_producer()
            except Exception:
                self._producer = None
        else:
            self._producer = None
        # Persistence path (configurable via SOMABRAIN_CALIBRATION_STORE)
        self._store_path = os.getenv(
            "SOMABRAIN_CALIBRATION_STORE", "./data/calibration/state.json"
        )
        if self.enabled:
            calibration_tracker.load(self._store_path)
        
        # Calibration metrics
        self.calibration_gauge = (
            metrics.get_gauge(
                "somabrain_calibration_ece",
                "Expected Calibration Error by domain",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        
        self.temperature_gauge = (
            metrics.get_gauge(
                "somabrain_calibration_temperature",
                "Temperature scaling parameter",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        
        self.brier_gauge = (
            metrics.get_gauge(
                "somabrain_calibration_brier",
                "Brier score for calibration",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        # Acceptance enforcement metrics
        self.ece_pre = (
            metrics.get_gauge(
                "somabrain_calibration_ece_pre",
                "ECE prior to latest calibration fit",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        self.ece_post = (
            metrics.get_gauge(
                "somabrain_calibration_ece_post",
                "ECE after calibration temperature applied",
                labelnames=["domain", "tenant"]
            ) if metrics else None
        )
        self.downgrade_counter = (
            metrics.get_counter(
                "somabrain_calibration_downgrade_total",
                "Count of calibration downgrades (rollback temperature)",
                labelnames=["domain", "tenant", "reason"]
            ) if metrics else None
        )
        # Store last stable temperature to allow rollback
        self._last_good_temperature: Dict[str, float] = {}
        
    def record_prediction(self, domain: str, tenant: str, 
                         confidence: float, accuracy: float) -> None:
        """
        Record a prediction for calibration tracking.
        
        Args:
            domain: Predictor domain
            tenant: Tenant identifier
            confidence: Predicted confidence
            accuracy: Actual accuracy (from feedback)
        """
        if not self.enabled:
            return
            
        calibration_tracker.add_observation(domain, tenant, confidence, accuracy)
        # After adding an observation, enforce acceptance if enough samples
        self._maybe_enforce(domain, tenant)
        
        # Update metrics
        metrics_data = calibration_tracker.get_calibration_metrics(domain, tenant)
        
        if self.calibration_gauge:
            self.calibration_gauge.labels(domain=domain, tenant=tenant).set(
                metrics_data["ece"]
            )
        
        if self.temperature_gauge:
            self.temperature_gauge.labels(domain=domain, tenant=tenant).set(
                metrics_data["temperature"]
            )
        
        if self.brier_gauge:
            self.brier_gauge.labels(domain=domain, tenant=tenant).set(
                metrics_data["brier"]
            )
    
    def get_calibration_status(self, domain: str, tenant: str) -> Dict[str, Any]:
        """Get calibration status for domain/tenant."""
        if not self.enabled:
            return {"enabled": False}
            
        metrics_data = calibration_tracker.get_calibration_metrics(domain, tenant)
        
        return {
            "enabled": True,
            "domain": domain,
            "tenant": tenant,
            "ece": metrics_data["ece"],
            "brier_score": metrics_data["brier"],
            "temperature": metrics_data["temperature"],
            "samples": metrics_data["samples"],
            "needs_calibration": calibration_tracker.should_calibrate(domain, tenant),
            "last_good_temperature": self._last_good_temperature.get(f"{domain}:{tenant}"),
        }
    
    def get_all_calibration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get calibration status for all domains and tenants."""
        if not self.enabled:
            return {"enabled": False}
            
        return {
            "enabled": True,
            "calibration_data": calibration_tracker.get_all_metrics()
        }
    
    def export_reliability_data(self, domain: str, tenant: str) -> Dict[str, Any]:
        """Export reliability diagram data."""
        if not self.enabled:
            return {"enabled": False}
            
        return calibration_tracker.export_reliability_data(domain, tenant)
    
    def run_forever(self) -> None:  # pragma: no cover
        """Run calibration service."""
        if not self.enabled:
            print("Calibration service disabled")
            return
        
        print("Starting calibration service...")
        
        while True:
            time.sleep(30)  # Emit snapshot every 30 seconds
            try:
                self._emit_calibration_snapshots()
                calibration_tracker.persist(self._store_path)
            except Exception as e:
                print(f"WARN: calibration snapshot emission failed: {e}")

    def _emit_calibration_snapshots(self) -> None:
        """Emit predictor calibration events for all tracked domain/tenant pairs."""
        if not self._producer:
            return
        all_metrics = calibration_tracker.get_all_metrics()
        for key, metrics_data in all_metrics.items():
            if ":" not in key:
                continue
            domain, tenant = key.split(":", 1)
            record = {
                "tenant": tenant,
                "domain": domain,
                "temperature": float(metrics_data.get("temperature", 1.0)),
                "ece": float(metrics_data.get("ece", 0.0)),
                "brier": float(metrics_data.get("brier", 0.0)),
                "samples": int(metrics_data.get("samples", 0)),
                "needs_calibration": bool(calibration_tracker.should_calibrate(domain, tenant)),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            try:
                topic = TOPICS.get("predictor_calibration", "cog.predictor.calibration")
                payload = encode(record, "predictor_calibration")
                self._producer.send(topic, value=payload)
            except Exception as e:  # pragma: no cover
                print(f"WARN: failed to send predictor_calibration event for {domain}:{tenant}: {e}")
        # Periodically enforce acceptance across all metrics
        try:
            for key in all_metrics.keys():
                if ":" not in key:
                    continue
                d, t = key.split(":", 1)
                self._maybe_enforce(d, t)
        except Exception:
            pass

    # --- Acceptance enforcement -------------------------------------------------
    def _maybe_enforce(self, domain: str, tenant: str) -> None:
        """Enforce calibration acceptance: require >=30% ECE reduction when fitted.

        Logic:
        - Compute pre-ECE using raw confidences (temperature=1) and post-ECE using scaler.temperature.
        - If post-ECE not at least 30% lower than pre-ECE (and samples >= 200), rollback temperature to last good value.
        - Maintain metrics ece_pre/ece_post and increment downgrade counter on rollback.
        - Update last_good_temperature when acceptance passes.
        """
        if not self.enabled:
            return
        key = f"{domain}:{tenant}"
        metrics_data = calibration_tracker.get_calibration_metrics(domain, tenant)
        samples = int(metrics_data.get("samples", 0))
        if samples < 50:  # Need minimum samples for any fit
            return
        try:
            from ..calibration.calibration_metrics import calibration_tracker as _tracker  # type: ignore
            # Access raw confidences/accuracies window
            raw_conf = list(_tracker.calibration_data[key]["confidences"]) if key in _tracker.calibration_data else []
            raw_acc = list(_tracker.calibration_data[key]["accuracies"]) if key in _tracker.calibration_data else []
        except Exception:
            raw_conf, raw_acc = [], []
        if len(raw_conf) < 50:
            return
        try:
            from ..calibration.temperature_scaling import compute_ece as _ece
            # Pre-ECE assumes identity temperature
            pre_ece = _ece(raw_conf, raw_acc)
            scaler = calibration_tracker.temperature_scalers[domain][tenant]
            # If not fitted, no acceptance yet
            if not getattr(scaler, "is_fitted", False):
                # On first fit, store baseline temperature
                self._last_good_temperature.setdefault(key, float(getattr(scaler, "temperature", 1.0)))
                return
            # Compute post-scaled confidences
            post_scaled = [scaler.scale(c) for c in raw_conf]
            post_ece = _ece(post_scaled, raw_acc)
            # Emit metrics
            if self.ece_pre:
                try:
                    self.ece_pre.labels(domain=domain, tenant=tenant).set(pre_ece)
                except Exception:
                    pass
            if self.ece_post:
                try:
                    self.ece_post.labels(domain=domain, tenant=tenant).set(post_ece)
                except Exception:
                    pass
            # Acceptance requirement: post_ece <= 0.7 * pre_ece (30% reduction) for large sample regime
            if samples >= 200 and pre_ece > 0.0:
                improved = (post_ece <= 0.7 * pre_ece)
                if not improved:
                    # Rollback temperature to last good (or 1.0 fallback)
                    last_good = self._last_good_temperature.get(key, 1.0)
                    old_temp = float(getattr(scaler, "temperature", last_good))
                    setattr(scaler, "temperature", float(last_good))
                    setattr(scaler, "is_fitted", True)
                    if self.downgrade_counter:
                        try:
                            self.downgrade_counter.labels(domain=domain, tenant=tenant, reason="ece_regression").inc()
                        except Exception:
                            pass
                    print(f"calibration_service: downgrade temperature domain={domain} tenant={tenant} from={old_temp:.3f} to={last_good:.3f} pre_ece={pre_ece:.4f} post_ece={post_ece:.4f}")
                else:
                    # Update last good temperature on improvement
                    self._last_good_temperature[key] = float(getattr(scaler, "temperature", 1.0))
        except Exception:
            pass


# Global service instance
calibration_service = CalibrationService()


def main() -> None:  # pragma: no cover
    """Entry point for calibration service."""
    service = CalibrationService()
    if not service.enabled:
        print("Calibration service disabled")
        return
    # Fail-fast infra readiness before starting loop (OPA optional here)
    assert_ready(require_kafka=True, require_redis=False, require_postgres=True, require_opa=False)
    service.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()