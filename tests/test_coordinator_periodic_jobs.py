from somabrain.autonomous import AutonomousConfig, AutonomousCoordinator


def test_coordinator_periodic_rollback_and_probe(monkeypatch):
    cfg = AutonomousConfig()
    cfg.enabled = False  # avoid starting subcomponents threads
    coord = AutonomousCoordinator(cfg)

    # Replace learner.experiment_manager with a dummy that records calls
    class DummyEM:
        def __init__(self):
            self.called = False

        def analyze_experiment(self, *args, **kwargs):
            return None

    dem = DummyEM()
    coord.learner.experiment_manager = dem

    # Patch adaptive_manager.monitor_promotions_and_rollback to mark called
    def fake_monitor(em):
        fake_monitor.called = True
        return 0

    fake_monitor.called = False
    coord.adaptive_manager.monitor_promotions_and_rollback = fake_monitor

    # Patch circuit_breaker_manager.auto_probe_all
    def fake_probe(_):
        fake_probe.called = True
        return 0

    fake_probe.called = False
    coord.healer.circuit_breaker_manager.auto_probe_all = fake_probe

    # Run a single iteration of the coordinator loop body by calling private method
    # We invoke _evaluate_healing_triggers indirectly by setting monitor health
    coord.monitor.health_checker.health_status = {}
    # Call the coordinator loop in a controlled way: run one cycle by invoking _run_coordinator in a thread and signaling shutdown
    import threading

    def run_one():
        # Allow one loop iteration by clearing shutdown, running, then setting shutdown
        coord.shutdown_event.clear()
        # Set very small interval so the loop proceeds quickly
        coord.config.monitoring.health_check_interval = 0.01
        # Ensure healing is active
        coord.healer.is_healing = True
        coord.monitor.is_running = False
        coord.learner.is_learning = False

        try:
            # Run coordinator loop in this thread until shutdown_event is set externally
            coord._run_coordinator()
        except Exception:
            pass

    t = threading.Thread(target=run_one)
    t.start()
    # Let the coordinator run one cycle
    import time as _time

    _time.sleep(0.05)
    coord.shutdown_event.set()
    t.join(timeout=2.0)

    assert fake_monitor.called is True
    assert fake_probe.called is True
