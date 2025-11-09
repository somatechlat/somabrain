from somabrain.integrator.consistency import consistency_score


def test_consistency_feasible():
    assert consistency_score({"intent": "browse"}, {"next_action": "search"}) == 1.0


def test_consistency_infeasible():
    assert consistency_score({"intent": "browse"}, {"next_action": "checkout"}) == 0.0


def test_consistency_unknown():
    assert consistency_score({"intent": "unknown"}, {"next_action": "search"}) is None
    assert consistency_score(None, {"next_action": "search"}) is None
    assert consistency_score({"intent": "browse"}, None) is None
