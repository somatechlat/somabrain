import os
import builtins
import pytest


def test_integrator_main_gates_on_flags(monkeypatch, capsys):
    # Import locally to ensure monkeypatching applies to the correct module
    import somabrain.services.integrator_hub as ih

    # Ensure per-service flag is off and composite disabled
    monkeypatch.setenv("SOMABRAIN_FF_COG_INTEGRATOR", "0")
    monkeypatch.delenv("ENABLE_COG_THREADS", raising=False)

    # Dummy run_forever that should NOT be called in this mode
    called = {"run": False}

    def _no_run(self):  # noqa: ARG001
        called["run"] = True

    monkeypatch.setattr(ih.IntegratorHub, "run_forever", _no_run)

    # Should return without running
    ih.main()
    assert called["run"] is False

    # Now enable composite and ensure main attempts to run
    monkeypatch.setenv("ENABLE_COG_THREADS", "1")

    def _exit(self):  # noqa: ARG001
        raise SystemExit(0)

    monkeypatch.setattr(ih.IntegratorHub, "run_forever", _exit)
    with pytest.raises(SystemExit):
        ih.main()


def test_segmentation_main_gates_on_flags(monkeypatch):
    import somabrain.services.segmentation_service as ss

    # Ensure per-service flag is off and composite disabled
    monkeypatch.setenv("SOMABRAIN_FF_COG_SEGMENTATION", "0")
    monkeypatch.delenv("ENABLE_COG_THREADS", raising=False)

    ran = {"run": False}

    def _no_run(self):  # noqa: ARG001
        ran["run"] = True

    monkeypatch.setattr(ss.SegmentationService, "run_forever", _no_run)

    # Should short-circuit without running
    ss.main()
    assert ran["run"] is False

    # With composite enabled, service should attempt to run
    monkeypatch.setenv("ENABLE_COG_THREADS", "1")

    def _exit(self):  # noqa: ARG001
        raise SystemExit(0)

    monkeypatch.setattr(ss.SegmentationService, "run_forever", _exit)

    with pytest.raises(SystemExit):
        ss.main()
