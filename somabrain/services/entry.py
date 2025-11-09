"""
Runtime Orchestrator for SomaBrain cognitive services.

Starts core services (integrator, segmentation, drift monitor, calibration,
and learner) in background threads within a single process. Each service
respects its own feature flags, and a composite flag `ENABLE_COG_THREADS=1`
will enable defaults suitable for full-capacity local runs.

Environment flags of interest:
- ENABLE_COG_THREADS: enable composite mode ("1"/true)
- SOMABRAIN_FF_COG_INTEGRATOR: enable integrator hub
- SOMABRAIN_FF_COG_SEGMENTATION: enable segmentation service
- ENABLE_DRIFT_DETECTION: enable drift monitoring loop
- ENABLE_AUTO_ROLLBACK: enable rollback in drift detector
- ENABLE_CALIBRATION: enable calibration service
- SOMABRAIN_FF_LEARNER_ONLINE: enable learner online service

Usage:
    python -m somabrain.services.entry
"""

from __future__ import annotations

import os
import signal
import threading
import time
from typing import Callable, Optional


def _flag_on(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _start_thread(target: Callable[[], None], name: str) -> threading.Thread:
    th = threading.Thread(target=target, name=name, daemon=True)
    th.start()
    print(f"orchestrator: started {name} thread")
    return th


def _run_integrator() -> None:
    try:
        from .integrator_hub import IntegratorHub

        hub = IntegratorHub()
        hub.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: integrator exited with error: {e}")


def _run_segmentation() -> None:
    try:
        from .segmentation_service import SegmentationService

        svc = SegmentationService()
        svc.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: segmentation exited with error: {e}")


def _run_drift_monitor() -> None:
    try:
        from somabrain.monitoring.drift_detector import drift_service

        drift_service.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: drift monitoring exited with error: {e}")


def _run_calibration() -> None:
    try:
        from .calibration_service import CalibrationService

        svc = CalibrationService()
        svc.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: calibration exited with error: {e}")


def _run_learner() -> None:
    try:
        # Import directly and create a fresh service instance
        from .learner_online import LearnerService

        svc = LearnerService()
        svc.run()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: learner exited with error: {e}")


def main() -> None:  # pragma: no cover
    composite = _flag_on("ENABLE_COG_THREADS", "1")
    threads: list[threading.Thread] = []

    # Integrator Hub
    if composite or _flag_on("SOMABRAIN_FF_COG_INTEGRATOR"):
        threads.append(_start_thread(_run_integrator, "integrator_hub"))
    else:
        print("orchestrator: integrator disabled")

    # Segmentation Service
    if composite or _flag_on("SOMABRAIN_FF_COG_SEGMENTATION"):
        threads.append(_start_thread(_run_segmentation, "segmentation_service"))
    else:
        print("orchestrator: segmentation disabled")

    # Drift Monitoring
    if composite or _flag_on("ENABLE_DRIFT_DETECTION"):
        threads.append(_start_thread(_run_drift_monitor, "drift_monitor"))
    else:
        print("orchestrator: drift monitoring disabled")

    # Calibration Service
    if composite or _flag_on("ENABLE_CALIBRATION"):
        threads.append(_start_thread(_run_calibration, "calibration_service"))
    else:
        print("orchestrator: calibration disabled")

    # Learner Online
    if composite or _flag_on("SOMABRAIN_FF_LEARNER_ONLINE"):
        threads.append(_start_thread(_run_learner, "learner_online"))
    else:
        print("orchestrator: learner disabled")

    # Handle SIGTERM/SIGINT gracefully by exiting the main loop
    stop = threading.Event()

    def _sig_handler(signum, frame):  # type: ignore
        print(f"orchestrator: received signal {signum}; shutting down...")
        stop.set()

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    # Keep the main thread alive while workers run
    try:
        while not stop.is_set():
            time.sleep(1.0)
    finally:
        print("orchestrator: exit")


if __name__ == "__main__":  # pragma: no cover
    main()
