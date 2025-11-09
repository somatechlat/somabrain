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
from ..common.kafka import TOPICS, make_producer

# Optional Kafka imports
try:
    from kafka import KafkaConsumer, KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore
    KafkaProducer = None  # type: ignore


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
        # Producer for calibration snapshots
        self._producer = make_producer() if self.enabled else None
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
        
        # This would be the main service loop
        # For now, it's a placeholder
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
                self._producer.send(topic, value=record)
            except Exception as e:  # pragma: no cover
                print(f"WARN: failed to send predictor_calibration event for {domain}:{tenant}: {e}")


# Global service instance
calibration_service = CalibrationService()


def main() -> None:  # pragma: no cover
    """Entry point for calibration service."""
    service = CalibrationService()
    service.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()