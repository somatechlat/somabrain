from somabrain.autonomous import AdaptiveConfigManager, AutonomousConfig
from somabrain.autonomous.learning import ExperimentManager


def test_canary_promotion_flow():
    cfg = AutonomousConfig()
    mgr = AdaptiveConfigManager(cfg)

    # Stage a canary value
    cfg.set_custom_parameter("canary::test_param", 0.8)

    # Create an experiment that proves the canary improves latency
    em = ExperimentManager(cfg)
    eid = em.create_experiment(
        "canary_test_param", "canary for test_param", {}, control_group="control"
    )
    em.add_experiment_group(eid, "variant", {})
    em.start_experiment(eid)

    # control samples (higher latency)
    for v in [1.0, 1.1, 0.95, 1.05, 1.0]:
        em.record_experiment_result(eid, "control", "latency", v)

    # variant samples (lower latency)
    for v in [0.7, 0.75, 0.8, 0.78, 0.76]:
        em.record_experiment_result(eid, "variant", "latency", v)

    promoted = mgr.promote_canaries(em, alpha=0.1, min_effect=0.1)
    assert promoted >= 1
    assert cfg.get_custom_parameter("test_param") == 0.8
