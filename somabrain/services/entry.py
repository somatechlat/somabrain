from __future__ import annotations
import signal
import threading
import time
from typing import Callable
from common.logging import logger
from .integrator_hub import IntegratorHub
from .segmentation_service import SegmentationService
from somabrain.monitoring.drift_detector import drift_service
from .calibration_service import CalibrationService
from .learner_online import LearnerService
from somabrain.modes import feature_enabled
from common.config.settings import settings

"""
Runtime Orchestrator for SomaBrain cognitive services.

Starts core services (integrator, segmentation, drift monitor, calibration,
and learner) in background threads within a single process. Each service
respects its own feature flags, and a composite flag `ENABLE_COG_THREADS=1`
will enable defaults suitable for full-capacity local runs.

Behavior is governed by centralized modes (see `somabrain.modes`). Legacy
ENABLE_* and SOMABRAIN_FF_* env flags are removed.

Usage:
    python -m somabrain.services.entry
"""




def _start_thread(target: Callable[[], None], name: str) -> threading.Thread:
    th = threading.Thread(target=target, name=name, daemon=True)
    th.start()
    print(f"orchestrator: started {name} thread")
    return th


def _run_integrator() -> None:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        hub = IntegratorHub()
        hub.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: integrator exited with error: {e}")


def _run_segmentation() -> None:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        svc = SegmentationService()
        svc.run()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: segmentation exited with error: {e}")


def _run_drift_monitor() -> None:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        drift_service.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: drift monitoring exited with error: {e}")


def _run_calibration() -> None:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        svc = CalibrationService()
        svc.run_forever()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: calibration exited with error: {e}")


def _run_learner() -> None:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        # Import directly and create a fresh service instance

        svc = LearnerService()
        svc.run()
    except Exception as e:  # pragma: no cover
        print(f"orchestrator: learner exited with error: {e}")


def main() -> None:  # pragma: no cover
    # Legacy composite flag ENABLE_COG_THREADS removed – rely on central feature flags.
    # The orchestrator now starts services solely based on `feature_enabled`.

    threads: list[threading.Thread] = []

    # Integrator Hub (respect master cog flag)
    if feature_enabled("integrator") and getattr(settings, "enable_cog_threads", True):
        threads.append(_start_thread(_run_integrator, "integrator_hub"))
    else:
        print("orchestrator: integrator disabled (cog flag or feature)")

    # Segmentation Service (respect master cog flag)
    if feature_enabled("segmentation") and getattr(
        settings, "enable_cog_threads", True
    ):
        threads.append(_start_thread(_run_segmentation, "segmentation_service"))
    else:
        print("orchestrator: segmentation disabled (cog flag or feature)")

    # Drift Monitoring (respect master cog flag)
    if feature_enabled("drift") and getattr(settings, "enable_cog_threads", True):
        threads.append(_start_thread(_run_drift_monitor, "drift_monitor"))
    else:
        print("orchestrator: drift monitoring disabled (cog flag or feature)")

    # Calibration Service (respect master cog flag)
    if feature_enabled("calibration") and getattr(settings, "enable_cog_threads", True):
        threads.append(_start_thread(_run_calibration, "calibration_service"))
    else:
        print("orchestrator: calibration disabled (cog flag or feature)")

    # Learner Online (respect master cog flag)
    if feature_enabled("learner") and getattr(settings, "enable_cog_threads", True):
        threads.append(_start_thread(_run_learner, "learner_online"))
    else:
        print("orchestrator: learner disabled (cog flag or feature)")

    # Handle SIGTERM/SIGINT gracefully by exiting the main loop
    stop = threading.Event()

def _sig_handler(signum, frame):  # type: ignore
        print(f"orchestrator: received signal {signum}; shutting down...")
        stop.set()

    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    raise
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        while not stop.is_set():
            time.sleep(1.0)
    finally:
        print("orchestrator: exit")


if __name__ == "__main__":  # pragma: no cover
    main()
