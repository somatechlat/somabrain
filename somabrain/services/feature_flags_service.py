from __future__ import annotations
import threading
from typing import Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from config.feature_flags import FeatureFlags
from somabrain import metrics as _metrics
from common.logging import logger
from somabrain.metrics import metrics_endpoint
from common.config.settings import settings
import uvicorn  # type: ignore

"""Feature‑flags HTTP service.

Provides a tiny FastAPI server exposing the current feature‑flag status via
``GET /feature-flags`` and Prometheus metrics via ``GET /metrics``. The service
uses the central ``somabrain.config.feature_flags.FeatureFlags`` implementation
so there is a single source of truth for all flags.

The service is intended to run as a separate process (similar to the other
``*_service`` modules) and can be started with ``python -m somabrain.services.feature_flags_service``.
"""




# Import the central feature‑flag helper.

# Re‑use the existing metrics module for gauge registration.

app = FastAPI(title="SomaBrain Feature Flags")


@app.get("/feature-flags", response_class=JSONResponse)
def get_flags() -> Any:
    """Return the current feature‑flag dictionary.

    The response format matches ``FeatureFlags.get_status()`` – a mapping of
    flag names to boolean values.
    """
    return FeatureFlags.get_status()


# Register a gauge per flag so Prometheus can scrape them.
def _register_flag_gauges() -> None:
    status = FeatureFlags.get_status()
    for name, enabled in status.items():
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            gauge = _metrics.get_gauge(
                "somabrain_feature_flag",
                "Feature flag status (1=enabled, 0=disabled)",
                labelnames=["flag"], )
            gauge.labels(flag=name).set(1 if enabled else 0)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            # failures should not crash the service.


def _periodic_update(stop_event: threading.Event, interval: float = 5.0) -> None:
    """Background thread that refreshes the gauges periodically.

    Flags can be toggled at runtime via the overrides file, so we keep the
    gauges in sync without requiring a service restart.
    """
    while not stop_event.is_set():
        _register_flag_gauges()
        stop_event.wait(interval)


def main() -> None:  # pragma: no cover – exercised via integration tests
    # Start a background thread that updates the gauges.
    stop_event = threading.Event()
    thread = threading.Thread(target=_periodic_update, args=(stop_event,), daemon=True)
    thread.start()

    # FastAPI will serve both /feature-flags and /metrics (the latter is
    # provided by ``somabrain.metrics.metrics_endpoint``).

@app.get("/metrics")
    async def metrics() -> Any:
        return await metrics_endpoint()

    # Use the centralized Settings value for the feature‑flags service port.

    port = int(settings.feature_flags_port)

    uvicorn.run(app, host="0.0.0.0", port=port)

    # When the server stops, signal the background thread to exit.
    stop_event.set()
    thread.join()


if __name__ == "__main__":  # pragma: no cover
    main()
