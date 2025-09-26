"""Simple script to emit sample autonomous metrics to a local Prometheus pushgateway or exposition endpoint.

Usage:
  - For local testing, run this script and point Prometheus to scrape the provided /metrics endpoint.
  - Example: python examples/emit_autonomous_metrics.py
"""

import time

from prometheus_client import start_http_server

from somabrain import metrics as app_metrics

AUTONOMOUS_HEALTH = app_metrics.get_gauge(
    "autonomous_component_health_status",
    "Health status of autonomous components",
    labelnames=["component"],
)
AUTONOMOUS_SUCCESS = app_metrics.get_gauge(
    "autonomous_actions_success_rate", "Success rate of autonomous actions"
)
AUTONOMOUS_EVENTS = app_metrics.get_counter(
    "autonomous_action_events_total",
    "Total autonomous actions",
    labelnames=["action", "result"],
)


def emit_loop():
    # Start a simple HTTP server for Prometheus to scrape
    start_http_server(8000)
    while True:
        # set a healthy component
        AUTONOMOUS_HEALTH.labels(component="monitor").set(2)
        AUTONOMOUS_HEALTH.labels(component="learner").set(1)
        AUTONOMOUS_HEALTH.labels(component="healer").set(2)
        AUTONOMOUS_SUCCESS.set(0.98)
        AUTONOMOUS_EVENTS.labels(action="auto_recover_system", result="success").inc(0)
        time.sleep(5)


if __name__ == "__main__":
    emit_loop()
