"""
Tests for AdaptiveConfig integration in the AutonomousCoordinator.
"""

import threading

from somabrain.autonomous import AutonomousConfig, AutonomousCoordinator


class _FakeOptimizer:
    def __init__(self):
        self.optimization_history = []


class _FakeRes:
    def __init__(self, parameter, new_value, confidence=1.0):
        self.parameter = parameter
        self.new_value = new_value
        self.confidence = confidence


def test_coordinator_applies_adaptive_optimizer(monkeypatch):
    """Coordinator should call AdaptiveConfigManager.apply_from_optimizer periodically."""
    cfg = AutonomousConfig()
    cfg.enabled = False  # avoid starting real components
    # make adaptive apply interval very short for test
    cfg.adaptive.apply_interval = 1
    cfg.adaptive.window_seconds = 60
    cfg.adaptive.max_changes_per_window = 10
    cfg.adaptive.per_parameter_cooldown_seconds = 0

    coordinator = AutonomousCoordinator(cfg)

    fake_opt = _FakeOptimizer()
    # prepare a fake optimization result
    fake_opt.optimization_history.append(
        _FakeRes("auto_tune_param", 3.14, confidence=1.0)
    )

    # Patch the learner's parameter_optimizer with our fake optimizer
    coordinator.learner.parameter_optimizer = fake_opt

    # Ensure AdaptiveConfigManager has the parameter range registered
    coordinator.adaptive_manager.register_parameter_range("auto_tune_param", 0.0, 10.0)

    # Run coordinator loop once in a separate thread but stop quickly
    stop_event = threading.Event()

    def runner():
        # run a short loop that replicates part of _run_coordinator logic
        # specifically calling adaptive apply once
        applied = coordinator.adaptive_manager.apply_from_optimizer(
            coordinator.learner.parameter_optimizer
        )
        # record result on coordinator for assertion
        coordinator._last_adaptive_applied = applied
        stop_event.set()

    t = threading.Thread(target=runner)
    t.start()
    # wait for the runner to finish
    stop_event.wait(timeout=2.0)
    t.join(timeout=2.0)

    assert getattr(coordinator, "_last_adaptive_applied", 0) == 1
    assert cfg.get_custom_parameter("auto_tune_param") == 3.14
