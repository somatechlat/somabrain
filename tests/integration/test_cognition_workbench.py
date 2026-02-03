"""Module test_cognition_workbench."""

import pytest
from somabrain.planning.exec_controller import ExecutiveController, ExecConfig, Policy


@pytest.fixture
def exec_controller():
    # Use a small window for testing responsiveness
    """Execute exec controller."""

    cfg = ExecConfig(
        window=5, conflict_threshold=0.5, explore_boost_k=2, use_bandits=False
    )
    # Manually run post_init defaults if needed, but the class does it.
    # We need to mock settings or provide non-None values to avoid default lookup failure?
    # ExecConfig usage: fields default to None, triggering Settings lookup.
    # But if we provide values, it shouldn't hit Settings.
    return ExecutiveController(cfg)


@pytest.mark.unit
class TestCognitionWorkbench:
    """Workbench for verifying Executive Control (Cognition) logic."""

    def test_conflict_detection(self):
        """Verify that low recall strength triggers conflict state."""
        # Explicitly set ALL fields to avoid Settings lookup failure
        cfg = ExecConfig(
            window=5,
            conflict_threshold=0.5,
            explore_boost_k=2,
            use_bandits=False,
            bandit_eps=0.1,
        )

        ctrl = ExecutiveController(cfg)

        # 1. Observe perfect recall -> Conflict should be 0.0
        for _ in range(5):
            ctrl.observe("tenant_1", 1.0)

        c = ctrl.conflict("tenant_1")
        assert c == 0.0

        p = ctrl.policy("tenant_1", base_top_k=5)
        assert p.use_graph is False
        assert p.inhibit_act is False

        # 2. Observe terrible recall -> Conflict should rise
        for _ in range(5):
            ctrl.observe("tenant_1", 0.1)

        c = ctrl.conflict("tenant_1")
        assert c > 0.8  # 1 - 0.1 = 0.9 approx

        p = ctrl.policy("tenant_1", base_top_k=5)
        assert p.use_graph is True
        # If conflict >= 0.9, inhibit triggers
        if c >= 0.9:
            assert p.inhibit_act is True
            assert p.inhibit_store is True

    def test_bandit_exploration(self):
        """Verify bandit logic explores graph augmentation."""
        # Enable bandits with high epsilon to force exploration occasionally
        # Or force deterministic checks.
        cfg = ExecConfig(
            window=10,
            use_bandits=True,
            bandit_eps=0.5,
            conflict_threshold=0.5,  # Required
            explore_boost_k=2,
        )
        ctrl = ExecutiveController(cfg)

        # We can't deterministically test random choice, but we can verify state updates.
        ctrl.update_bandit("tenant_1", arm=0, reward=1.0)
        c, r = ctrl._bandit_state("tenant_1")
        assert c[0] == 1
        assert r[0] == 1.0

        ctrl.update_bandit("tenant_1", arm=1, reward=0.5)
        c, r = ctrl._bandit_state("tenant_1")
        assert c[1] == 1
        assert r[1] == 0.5

        # Policy Request should trigger arm choice
        # We can spy on it or just run it.
        p = ctrl.policy("tenant_1", base_top_k=5)
        assert isinstance(p, Policy)
        # If use_graph (arm 1) is chosen, k should be boosted
        if p.use_graph:
            assert p.adj_top_k == 5 + cfg.explore_boost_k
        else:
            assert p.adj_top_k == 5

    def test_universe_switching(self):
        """Verify switching universe under extreme conflict."""
        cfg = ExecConfig(
            window=2,
            conflict_threshold=0.5,
            explore_boost_k=2,
            use_bandits=False,
            bandit_eps=0.1,
        )
        ctrl = ExecutiveController(cfg)

        # Max conflict
        ctrl.observe("tenant_1", 0.0)
        ctrl.observe("tenant_1", 0.0)

        p = ctrl.policy("tenant_1", base_top_k=5, switch_threshold=0.8)
        assert p.target_universe is not None, "Should suggest switching universe"
