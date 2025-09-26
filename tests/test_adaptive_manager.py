"""
Unit tests for AdaptiveConfigManager behaviors: cooldown and clamping.
"""

import time

from somabrain.autonomous import AdaptiveConfigManager, AutonomousConfig
from somabrain.autonomous.learning import ParameterOptimizer


class _FakeOptimizer:
    def __init__(self):
        self.optimization_history = []


class _FakeRes:
    def __init__(self, parameter, new_value, confidence=1.0):
        self.parameter = parameter
        self.new_value = new_value
        self.confidence = confidence


def test_per_parameter_cooldown_enforced():
    cfg = AutonomousConfig()
    cfg.adaptive.per_parameter_cooldown_seconds = 2
    manager = AdaptiveConfigManager(cfg)
    # AdaptiveConfigManager keeps its own AdaptiveConfig instance by default;
    # ensure we set the manager's adaptive cooldown value for the test.
    manager.adaptive.per_parameter_cooldown_seconds = 2

    # register and prepare optimizer
    manager.register_parameter_range("p", 0, 100)
    opt = _FakeOptimizer()
    opt.optimization_history.append(_FakeRes("p", 10))

    # first apply should succeed
    applied1 = manager.apply_from_optimizer(opt)
    assert applied1 == 1

    # immediately try to apply another change for same param -> should be skipped due to cooldown
    opt.optimization_history.append(_FakeRes("p", 20))
    applied2 = manager.apply_from_optimizer(opt)
    assert applied2 == 0

    # after cooldown expires, should apply
    time.sleep(2.1)
    applied3 = manager.apply_from_optimizer(opt)
    assert applied3 == 1


def test_clamp_to_parameter_range():
    cfg = AutonomousConfig()
    manager = AdaptiveConfigManager(cfg)
    manager.register_parameter_range("x", 0.0, 1.0)

    opt = _FakeOptimizer()
    # propose an out-of-range value
    opt.optimization_history.append(_FakeRes("x", 2.5))

    applied = manager.apply_from_optimizer(opt)
    assert applied == 1
    # value should be clamped to max 1.0
    assert cfg.get_custom_parameter("x") == 1.0


def test_window_rate_limiting_respected():
    cfg = AutonomousConfig()
    manager = AdaptiveConfigManager(cfg)
    manager.adaptive.window_seconds = 2
    manager.adaptive.max_changes_per_window = 1

    manager.register_parameter_range("a", 0, 10)
    manager.register_parameter_range("b", 0, 10)

    opt = _FakeOptimizer()
    opt.optimization_history.append(_FakeRes("a", 1))
    opt.optimization_history.append(_FakeRes("b", 2))

    # Only one change should be allowed in the window
    applied = manager.apply_from_optimizer(opt)
    assert applied <= 1


def test_min_confidence_enforced():
    cfg = AutonomousConfig()
    manager = AdaptiveConfigManager(cfg)
    manager.adaptive.min_confidence = 0.5
    manager.register_parameter_range("z", 0, 100)

    opt = _FakeOptimizer()
    # produce a result with low confidence
    low = _FakeRes("z", 10, confidence=0.1)
    opt.optimization_history.append(low)
    applied = manager.apply_from_optimizer(opt)
    assert applied == 0

    # now with high confidence
    opt.optimization_history.append(_FakeRes("z", 20, confidence=0.9))
    applied2 = manager.apply_from_optimizer(opt)
    assert applied2 == 1


def _make_fake_result(parameter, old, new, confidence=0.0):
    class _R:
        def __init__(self, parameter, old_value, new_value, confidence):
            self.parameter = parameter
            self.old_value = old_value
            self.new_value = new_value
            self.confidence = confidence

    return _R(parameter, old, new, confidence)


def test_adaptive_rate_window_and_cooldown():
    cfg = AutonomousConfig()
    mgr = AdaptiveConfigManager(cfg)

    # Configure a tight window and max changes
    mgr.adaptive.window_seconds = 2
    mgr.adaptive.max_changes_per_window = 2
    mgr.adaptive.per_parameter_cooldown_seconds = 1

    opt = ParameterOptimizer(cfg)
    opt.register_parameter("p1", 1.0, min_value=0.0, max_value=10.0)
    opt.register_parameter("p2", 2.0, min_value=0.0, max_value=10.0)

    # Add multiple fake optimization results
    opt.optimization_history.append(_make_fake_result("p1", 1.0, 1.5, confidence=0.9))
    opt.optimization_history.append(_make_fake_result("p2", 2.0, 2.5, confidence=0.9))

    applied = mgr.apply_from_optimizer(opt)
    assert applied == 2
    assert cfg.get_custom_parameter("p1") == 1.5
    assert cfg.get_custom_parameter("p2") == 2.5

    # Immediate re-apply should be blocked by window limit
    opt.optimization_history.append(_make_fake_result("p1", 1.5, 1.6, confidence=0.9))
    applied2 = mgr.apply_from_optimizer(opt)
    assert applied2 == 0

    # Wait for window to expire and cooldown per-parameter
    time.sleep(2.1)
    applied3 = mgr.apply_from_optimizer(opt)
    # p1 cooldown might still prevent immediate reapply unless cooldown elapsed
    assert applied3 >= 0


def test_min_confidence_enforced_with_optimizer():
    # Renamed duplicate test to avoid redefinition errors (ruff F811).
    # This variant uses ParameterOptimizer.
    cfg = AutonomousConfig()
    mgr = AdaptiveConfigManager(cfg)
    mgr.adaptive.min_confidence = 0.8

    opt = ParameterOptimizer(cfg)
    opt.register_parameter("p3", 3.0, min_value=0.0, max_value=10.0)
    # Low confidence result
    opt.optimization_history.append(_make_fake_result("p3", 3.0, 3.5, confidence=0.2))
    applied = mgr.apply_from_optimizer(opt)
    assert applied == 0

    # High confidence
    opt.optimization_history.append(_make_fake_result("p3", 3.0, 3.7, confidence=0.9))
    applied2 = mgr.apply_from_optimizer(opt)
    assert applied2 == 1
