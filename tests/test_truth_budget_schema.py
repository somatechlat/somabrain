import os

from somabrain.config import load_config, load_truth_budget, _validate_and_map_truth_budget, TruthBudget


def test_truth_budget_example_loads():
    path = os.path.join(os.getcwd(), "docs", "truth_budget_example.yaml")
    assert os.path.isfile(path), "example YAML missing"
    cfg = load_config()
    cfg.truth_budget_path = path
    load_truth_budget(cfg)
    assert cfg.truth_budget is not None
    tb = _validate_and_map_truth_budget(cfg, cfg.truth_budget)
    assert isinstance(tb, TruthBudget)
    # sanity checks
    assert 0.0 < tb.epsilon_total < 1.0
    assert tb.density_ev_target >= 0.5 and tb.density_ev_target <= 1.0
    assert tb.chebyshev_order_K >= 4
