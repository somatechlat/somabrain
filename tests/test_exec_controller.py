from somabrain.exec_controller import ExecConfig, ExecutiveController


def test_exec_controller_use_graph_when_conflict_exceeds_threshold():
    cfg = ExecConfig(window=4, conflict_threshold=0.7, use_bandits=False)
    ec = ExecutiveController(cfg)
    # Low recall -> high conflict (1 - mean)
    for _ in range(4):
        ec.observe("t1", 0.2)  # mean=0.2 => conflict=0.8
    pol = ec.policy("t1", base_top_k=3)
    assert pol.use_graph is True
    assert pol.adj_top_k >= 3  # boosted when using graph


def test_exec_controller_no_graph_when_conflict_low():
    cfg = ExecConfig(window=4, conflict_threshold=0.7, use_bandits=False)
    ec = ExecutiveController(cfg)
    # High recall -> low conflict
    for _ in range(4):
        ec.observe("t2", 0.9)  # mean=0.9 => conflict=0.1
    pol = ec.policy("t2", base_top_k=3)
    assert pol.use_graph is False
    assert pol.adj_top_k == 3


def test_exec_controller_inhibit_when_conflict_extreme():
    cfg = ExecConfig(window=4, conflict_threshold=0.7, use_bandits=False)
    ec = ExecutiveController(cfg)
    # Very low recall -> conflict >= 0.9
    for _ in range(4):
        ec.observe("t3", 0.05)  # mean=0.05 => conflict=0.95
    pol = ec.policy("t3", base_top_k=3)
    assert pol.inhibit_act is True
    assert pol.inhibit_store is True
