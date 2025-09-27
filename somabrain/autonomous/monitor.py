"""
Autonomous Monitoring for SomaBrain.

This module provides monitoring capabilities for autonomous operations,
including health checks, anomaly detection, and alerting.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

from .. import metrics as app_metrics
from .config import AutonomousConfig

logger = logging.getLogger(__name__)


# Gauge to expose health status of autonomous components (0=unhealthy,1=degraded,2=healthy)
AUTONOMOUS_HEALTH_STATUS = app_metrics.get_gauge(
    "autonomous_component_health_status",
    "Health status of autonomous components (0=unhealthy,1=degraded,2=healthy)",
    labelnames=["component"],
)


@dataclass
class HealthStatus:
    """Health status of a system component."""

    component: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    metrics: Dict[str, float] = field(default_factory=dict)
    details: str = ""


@dataclass
class Anomaly:
    """Anomaly detected in system metrics."""

    component: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str = ""


class HealthChecker:
    """Health checker for autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.health_status: Dict[str, HealthStatus] = {}
        self.check_functions: Dict[str, Callable] = {}
        self.last_check_time: datetime = datetime.now()

    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        self.check_functions[name] = check_func
        logger.info(f"Registered health check: {name}")

    def run_health_checks(self) -> Dict[str, HealthStatus]:
        """Run all registered health checks."""
        results = {}

        for name, check_func in self.check_functions.items():
            try:
                status = check_func()
                results[name] = HealthStatus(
                    component=name,
                    status=status.get("status", "unknown"),
                    timestamp=datetime.now(),
                    metrics=status.get("metrics", {}),
                    details=status.get("details", ""),
                )
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = HealthStatus(
                    component=name,
                    status="unhealthy",
                    timestamp=datetime.now(),
                    details=f"Check failed: {str(e)}",
                )

        # Update Prometheus gauge based on results
        for comp, hs in results.items():
            val = {"unhealthy": 0, "degraded": 1, "healthy": 2}.get(hs.status, 0)
            try:
                AUTONOMOUS_HEALTH_STATUS.labels(component=comp).set(val)
            except Exception as e:
                logger.error(f"Failed to set health gauge for {comp}: {e}")

        self.health_status = results
        self.last_check_time = datetime.now()
        return results

    def get_system_metrics(self) -> Dict[str, float]:
        """Get system-level metrics."""
        if psutil is None:  # pragma: no cover - optional dependency
            logger.debug("psutil not available; system metrics disabled")
            return {}
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "network_bytes_sent": psutil.net_io_counters().bytes_sent,
                "network_bytes_recv": psutil.net_io_counters().bytes_recv,
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        metrics = self.get_system_metrics()
        status = "healthy"
        details = []

        # Check CPU usage
        if "cpu_percent" in metrics:
            cpu_threshold = self.config.monitoring.alert_threshold_cpu
            if metrics["cpu_percent"] > cpu_threshold:
                status = "degraded"
                details.append(f"CPU usage high: {metrics['cpu_percent']:.1f}%")

        # Check memory usage
        if "memory_percent" in metrics:
            memory_threshold = self.config.monitoring.alert_threshold_memory
            if metrics["memory_percent"] > memory_threshold:
                status = "degraded"
                details.append(f"Memory usage high: {metrics['memory_percent']:.1f}%")

        return {
            "status": status,
            "metrics": metrics,
            "details": "; ".join(details) if details else "System healthy",
        }


class AnomalyDetector:
    """Anomaly detector for system metrics."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.metrics_history: Dict[str, deque] = {}
        self.anomalies: List[Anomaly] = []
        self.max_history_size = 1000

    def add_metric(
        self, name: str, value: float, timestamp: Optional[datetime] = None
    ) -> None:
        """Add a metric value to history."""
        if name not in self.metrics_history:
            self.metrics_history[name] = deque(maxlen=self.max_history_size)

        if timestamp is None:
            timestamp = datetime.now()

        self.metrics_history[name].append((timestamp, value))

    def detect_anomalies(self, metrics: Dict[str, float]) -> List[Anomaly]:
        """Detect anomalies in metrics."""
        detected_anomalies = []

        for metric_name, value in metrics.items():
            # Skip if not enough history
            if (
                metric_name not in self.metrics_history
                or len(self.metrics_history[metric_name]) < 10
            ):
                self.add_metric(metric_name, value)
                continue

            # Get historical values
            history = [v for t, v in self.metrics_history[metric_name]]

            # Calculate statistics
            mean = np.mean(history)
            std = np.std(history)

            # Detect anomalies using z-score
            if std > 0:
                z_score = abs(value - mean) / std
                if z_score > 3:  # 3 sigma threshold
                    severity = "high" if z_score > 4 else "medium"
                    anomaly = Anomaly(
                        component="system",
                        metric=metric_name,
                        value=value,
                        threshold=mean + (3 * std),
                        timestamp=datetime.now(),
                        severity=severity,
                        description=f"Value {value:.2f} deviates significantly from mean {mean:.2f} (z-score: {z_score:.2f})",
                    )
                    detected_anomalies.append(anomaly)
                    self.anomalies.append(anomaly)
                    logger.warning(f"Anomaly detected: {anomaly.description}")

            # Add current value to history
            self.add_metric(metric_name, value)

        return detected_anomalies


class AlertManager:
    """Alert manager for autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.alerts: List[Dict[str, Any]] = []
        self.notification_channels: List[Callable] = []
        # Register a default console logging channel
        self.register_notification_channel(self._console_channel)
        # Optionally set up an email channel if SMTP settings are provided in config.custom_parameters
        smtp_cfg = self.config.custom_parameters.get("smtp")
        if isinstance(smtp_cfg, dict):
            try:
                self._email_cfg = smtp_cfg
                self.register_notification_channel(self._email_channel)
            except Exception as e:
                logger.error(f"Failed to set up email alert channel: {e}")

    def _console_channel(self, alert: Dict[str, Any]) -> None:
        """Default channel that logs alerts to the logger."""
        level = alert.get("severity", "info").upper()
        msg = f"[ALERT] {alert.get('title')}: {alert.get('message')}"
        if level == "CRITICAL" or level == "HIGH":
            logger.error(msg)
        elif level == "MEDIUM" or level == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)

    def _email_channel(self, alert: Dict[str, Any]) -> None:
        """Send alert via email using SMTP configuration.
        Expected config.custom_parameters['smtp'] keys: host, port, username, password, from_addr, to_addrs.
        """
        cfg = getattr(self, "_email_cfg", None)
        if not cfg:
            return
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["Subject"] = f"[SomaBrain Alert] {alert.get('title')}"
            msg["From"] = cfg.get("from_addr")
            msg["To"] = ", ".join(cfg.get("to_addrs", []))
            body = f"Severity: {alert.get('severity')}\n\n{alert.get('message')}"
            msg.set_content(body)
            with smtplib.SMTP_SSL(cfg.get("host"), cfg.get("port")) as server:
                server.login(cfg.get("username"), cfg.get("password"))
                server.send_message(msg)
            logger.info(f"Email alert sent for {alert.get('title')}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def register_notification_channel(self, channel_func: Callable) -> None:
        """Register a notification channel."""
        self.notification_channels.append(channel_func)
        logger.info("Registered notification channel")

    def send_alert(self, title: str, message: str, severity: str = "info") -> None:
        """Send an alert through all registered channels."""
        alert = {
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(),
        }

        self.alerts.append(alert)

        # Send through all channels
        for channel in self.notification_channels:
            try:
                channel(alert)
            except Exception as e:
                logger.error(f"Failed to send alert through channel: {e}")

        logger.info(f"Alert sent: {title} - {message}")


class AutonomousMonitor:
    """Main monitor for autonomous operations."""

    def __init__(self, config: AutonomousConfig):
        self.config = config
        self.health_checker = HealthChecker(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.alert_manager = AlertManager(config)
        self.is_running = False
        self.last_monitoring_cycle: datetime = datetime.now()

    def start_monitoring(self) -> None:
        """Start autonomous monitoring."""
        if self.is_running:
            logger.warning("Monitoring already running")
            return

        self.is_running = True
        logger.info("Autonomous monitoring started")

        # Register system health check
        self.health_checker.register_check(
            "system", self.health_checker.check_system_health
        )

    def stop_monitoring(self) -> None:
        """Stop autonomous monitoring."""
        self.is_running = False
        logger.info("Autonomous monitoring stopped")

    def run_monitoring_cycle(self) -> None:
        """Run a single monitoring cycle."""
        if not self.is_running:
            return

        # Run health checks
        health_results = self.health_checker.run_health_checks()

        # Collect metrics for anomaly detection
        all_metrics = {}
        for result in health_results.values():
            all_metrics.update(result.metrics)

        # Detect anomalies
        anomalies = self.anomaly_detector.detect_anomalies(all_metrics)

        # Send alerts for anomalies
        for anomaly in anomalies:
            self.alert_manager.send_alert(
                title=f"Anomaly Detected: {anomaly.metric}",
                message=anomaly.description,
                severity=anomaly.severity,
            )

        # Check for unhealthy components
        for component, status in health_results.items():
            if status.status == "unhealthy":
                self.alert_manager.send_alert(
                    title=f"Component Unhealthy: {component}",
                    message=status.details,
                    severity="high",
                )
            elif status.status == "degraded":
                self.alert_manager.send_alert(
                    title=f"Component Degraded: {component}",
                    message=status.details,
                    severity="medium",
                )

        self.last_monitoring_cycle = datetime.now()
