from importlib import import_module


def _run(modname: str):
    mod = import_module(modname)
    assert hasattr(mod, "main"), f"{modname} lacks main()"
    mod.main()


def test_endpoints_basic():
    _run("tests.test_endpoints_basic")


def test_hrr_cleanup():
    _run("tests.test_hrr_cleanup")


def test_memory_client():
    _run("tests.test_memory_client")


def test_reflection_v2():
    _run("tests.test_reflection_v2")


def test_graph_reasoning():
    _run("tests.test_graph_reasoning")


def test_personality():
    _run("tests.test_personality")


def test_predictor_budget():
    _run("tests.test_predictor_budget")


def test_migration():
    _run("tests.test_migration")


def test_semantic_graph():
    _run("tests.test_semantic_graph")


def test_microcircuits():
    _run("tests.test_microcircuits")


def test_micro_diag():
    _run("tests.test_micro_diag")


def test_universes():
    _run("tests.test_universes")


def test_hrr_first():
    _run("tests.test_hrr_first")


def test_soft_salience():
    _run("tests.test_soft_salience")


def test_supervisor():
    _run("tests.test_supervisor")


def test_consolidation():
    _run("tests.test_consolidation")


def test_drift_monitor():
    _run("tests.test_drift_monitor")


def test_neuromodulators():
    _run("tests.test_neuromodulators")


def test_reality():
    _run("tests.test_reality")


def test_strategy_switch():
    _run("tests.test_strategy_switch")


def test_planner():
    _run("tests.test_planner")


def test_provenance():
    _run("tests.test_provenance")


def test_provenance_strict():
    _run("tests.test_provenance_strict")
