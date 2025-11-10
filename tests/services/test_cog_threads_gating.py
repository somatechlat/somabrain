import builtins
import pytest
from dataclasses import replace


def test_integrator_main_gates_on_flags(monkeypatch, capsys):
    # Import locally to ensure monkeypatching applies to the correct module
    import somabrain.services.integrator_hub as ih

    # Ensure per-service flag is off via centralized mode config
    import somabrain.modes as modes
    base = modes.get_mode_config()
    monkeypatch.setattr(modes, "get_mode_config", lambda: replace(base, enable_integrator=False))

    # Dummy run_forever that should NOT be called in this mode
    called = {"run": False}

    def _no_run(self):  # noqa: ARG001
        called["run"] = True

    monkeypatch.setattr(ih.IntegratorHub, "run_forever", _no_run)

    # Should return without running
    ih.main()
    assert called["run"] is False

    # Enable integrator via centralized mode config and bypass infra readiness
    monkeypatch.setattr(ih, "assert_ready", lambda **kwargs: None)
    monkeypatch.setattr(modes, "get_mode_config", lambda: replace(base, enable_integrator=True))

    def _exit(self):  # noqa: ARG001
        raise SystemExit(0)

    monkeypatch.setattr(ih.IntegratorHub, "run_forever", _exit)
    with pytest.raises(SystemExit):
        ih.main()


def test_segmentation_main_gates_on_flags(monkeypatch):
    import somabrain.services.segmentation_service as ss
    import somabrain.modes as modes

    # Ensure per-service flag is off via centralized config
    base = modes.get_mode_config()
    monkeypatch.setattr(modes, "get_mode_config", lambda: replace(base, enable_segmentation=False))

    ran = {"run": False}

    def _no_run(self):  # noqa: ARG001
        ran["run"] = True

    monkeypatch.setattr(ss.SegmentationService, "run_forever", _no_run)

    # Should short-circuit without running
    ss.main()
    assert ran["run"] is False

    # Enable via centralized config and bypass infra readiness
    monkeypatch.setattr(ss, "assert_ready", lambda **kwargs: None)
    monkeypatch.setattr(modes, "get_mode_config", lambda: replace(base, enable_segmentation=True))

    def _exit(self):  # noqa: ARG001
        raise SystemExit(0)

    monkeypatch.setattr(ss.SegmentationService, "run_forever", _exit)

    with pytest.raises(SystemExit):
        ss.main()
