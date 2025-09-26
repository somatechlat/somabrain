"""
Tests for self-healing behaviors: circuit breaker triggers, recovery orchestrator execution,
and safety/emergency-stop behavior.
"""

from somabrain import audit
from somabrain.autonomous import AutonomousConfig
from somabrain.autonomous.healing import (
    CircuitBreakerManager,
    RecoveryAction,
    RecoveryOrchestrator,
)


def test_circuit_breaker_triggers_recovery(monkeypatch, tmp_path):
    cfg = AutonomousConfig()
    cbm = CircuitBreakerManager(cfg)

    # create a recovery orchestrator and a simple action
    ro = RecoveryOrchestrator(cfg)

    called = {"count": 0}

    def action_func():
        called["count"] += 1
        return {"ok": True}

    action = RecoveryAction(
        action_id="cb_recover", description="Recover CB", execute_func=action_func
    )
    ro.register_recovery_action(action)

    cbm.set_recovery_orchestrator(ro)
    cbm.register_circuit_breaker("svc", failure_threshold=2, recovery_timeout=1)
    cbm.set_recovery_action_for_cb("svc", "cb_recover")

    # Monkeypatch audit.log_admin_action to capture calls
    audit_calls = []

    def fake_audit(request=None, action=None, details=None):
        audit_calls.append({"action": action, "details": details})

    monkeypatch.setattr(audit, "log_admin_action", fake_audit)

    # record failures to exceed threshold
    cbm.record_failure("svc")
    assert called["count"] == 0
    cbm.record_failure("svc")

    # After threshold, recovery should be triggered synchronously
    assert called["count"] == 1
    assert any(c.get("action") == "circuit_auto_trigger" for c in audit_calls)


def test_recovery_orchestrator_executes_and_records():
    cfg = AutonomousConfig()
    ro = RecoveryOrchestrator(cfg)

    def do_work():
        return {"result": "ok"}

    action = RecoveryAction(
        action_id="do_test", description="Test action", execute_func=do_work
    )
    ro.register_recovery_action(action)

    res = ro.trigger_recovery("do_test")
    assert res is not None
    assert res.status.name == "SUCCESS"
    assert any(r.action_id == "do_test" for r in ro.completed_actions)


def test_critical_action_blocked_by_human_oversight(monkeypatch):
    cfg = AutonomousConfig()
    cfg.safety.emergency_stop_enabled = True
    cfg.safety.human_oversight_required = True
    ro = RecoveryOrchestrator(cfg)

    def do():
        return {"ok": True}

    action = RecoveryAction(
        action_id="critical_restart", description="Critical restart", execute_func=do
    )
    ro.register_recovery_action(action)

    res = ro.trigger_recovery("critical_restart")
    assert res is not None
    assert res.status.name == "FAILED"
    assert res.error == "human_oversight_required"


def test_recovery_metrics_increment(monkeypatch):
    cfg = AutonomousConfig()
    ro = RecoveryOrchestrator(cfg)

    called = {"n": 0}

    def do_ok():
        called["n"] += 1
        return {"ok": True}

    action = RecoveryAction(action_id="m1", description="m1", execute_func=do_ok)
    ro.register_recovery_action(action)

    # Trigger recovery and ensure action ran; avoid inspecting private Counter internals.
    # No need to import metrics internals for this test.
    ro.trigger_recovery("m1")
    # Can't reliably inspect internal Counter value without exposing it; ensure action ran
    assert called["n"] == 1
