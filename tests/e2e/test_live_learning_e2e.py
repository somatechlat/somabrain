"""Live E2E: agent interactions train the brain (:30101).

Runs the same sequence as ``scripts/live_learning_e2e.py`` against the live
stack. Skips when the API is unreachable — a skip is not a green proof.

Credential law: bearer resolved via Vault token file path (never env secrets).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
import urllib.error
import urllib.request

# Live HTTP proof only — must not boot Django settings (no_django contract).
pytestmark = [pytest.mark.no_django, pytest.mark.integration]

API_URL = os.environ.get("SOMABRAIN_API_URL", "http://127.0.0.1:30101").rstrip("/")

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "live_learning_e2e.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("live_learning_e2e", _SCRIPT)
    if spec is None or spec.loader is None:  # pragma: no cover - import machinery
        raise ImportError(f"cannot load {_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _api_available() -> bool:
    try:
        request = urllib.request.Request(f"{API_URL}/health", method="GET")
        with urllib.request.urlopen(request, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


@pytest.mark.skipif(
    not _api_available(),
    reason=f"SomaBrain API not reachable at {API_URL} — live proof requires the stack",
)
def test_live_learning_weights_move_on_feedback():
    """Feedback must apply and move alpha/lambda on the live brain."""
    script = _load_script()
    result = script.run_proof()
    report = script.format_evidence(result)
    print("\n" + report)
    assert result.ok, f"live learning proof FAILED:\n{report}"

    deltas = next((e.detail for e in result.evidence if e.step == "delta"), None)
    assert deltas is not None, "no delta evidence captured"

    before = next(e.detail for e in result.evidence if e.step == "state_before")
    after = next(e.detail for e in result.evidence if e.step == "state_after")

    assert after["alpha"] != before["alpha"], "alpha did not move"
    assert after["lambda_"] != before["lambda_"], "lambda_ did not move"
    assert after["history_len"] > before["history_len"], "history_len did not grow"

    applied_steps = [e for e in result.evidence if e.step.startswith("feedback_")]
    assert applied_steps, "no feedback evidence"
    assert all(
        e.detail.get("adaptation_applied") is True for e in applied_steps
    ), f"adaptation_applied not true on every round: {[e.detail for e in applied_steps]}"
