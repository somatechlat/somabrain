from somabrain.autonomous import AutonomousConfig
from somabrain.autonomous.healing import CircuitBreakerManager, RecoveryAction


def test_circuit_auto_reset_probe_and_recovery_trigger():
    cfg = AutonomousConfig()
    cbm = CircuitBreakerManager(cfg)

    # Register circuit with low thresholds
    cbm.register_circuit_breaker("svc", failure_threshold=2, recovery_timeout=0)

    # create dummy recovery orchestrator to verify trigger call
    from somabrain.autonomous.healing import RecoveryOrchestrator

    ro = RecoveryOrchestrator(cfg)

    called = {"recovered": False}

    def exec_recover():
        called["recovered"] = True
        return {"ok": True}

    action = RecoveryAction(
        action_id="fix_svc", description="Fix svc", execute_func=exec_recover
    )
    ro.register_recovery_action(action)

    # Wire orchestrator into circuit breaker manager and associate action
    cbm.set_recovery_orchestrator(ro)
    cbm.set_recovery_action_for_cb("svc", "fix_svc")

    # record failures to open the circuit
    cbm.record_failure("svc")
    cbm.record_failure("svc")
    assert cbm.check_circuit_state("svc") in ("open", "half_open")
    # since recovery_timeout=0, check_circuit_state moves it to half_open
    state = cbm.check_circuit_state("svc")
    assert state in ("half_open", "open")

    # Probe that returns True should reset circuit
    def probe_ok():
        return True

    cbm.circuit_breakers["svc"]["state"] = "half_open"
    reset = cbm.probe_and_reset("svc", probe_ok)
    assert reset is True
    assert cbm.check_circuit_state("svc") == "closed"

    # Now force open again and ensure recovery action triggered during open
    cbm.record_failure("svc")
    cbm.record_failure("svc")
    assert called["recovered"] is True
