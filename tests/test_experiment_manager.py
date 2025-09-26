from somabrain.autonomous import AutonomousConfig
from somabrain.autonomous.learning import ExperimentManager


def test_assign_to_group_deterministic():
    cfg = AutonomousConfig()
    em = ExperimentManager(cfg)
    eid = em.create_experiment("test", "desc", {}, control_group="control")
    em.add_experiment_group(eid, "variant", {})
    # Deterministic mapping: same subject should map to same group
    g1 = em.assign_to_group(eid, "subject-123")
    g2 = em.assign_to_group(eid, "subject-123")
    assert g1 == g2


def test_analyze_experiment_statistics():
    cfg = AutonomousConfig()
    em = ExperimentManager(cfg)
    eid = em.create_experiment("stat", "desc", {}, control_group="control")
    em.add_experiment_group(eid, "variant", {})
    em.start_experiment(eid)

    # record samples for control and variant
    for v in [1.0, 1.1, 0.9, 1.2, 1.05]:
        em.record_experiment_result(eid, "control", "latency", v)
    for v in [0.8, 0.85, 0.9, 0.95, 0.9]:
        em.record_experiment_result(eid, "variant", "latency", v)

    res = em.analyze_experiment(eid, "latency")
    assert res is not None
    assert "p_value" in res
    assert "effect_size_cohen_d" in res
