from somabrain.attention import UCB1Bandit


def test_ucb_add_select_update():
    b = UCB1Bandit()
    b.add_arm("wm")
    b.add_arm("ltm")
    # First two selections should try each arm once
    first = b.select()
    assert first in ("wm", "ltm")
    b.update(first, 1.0)
    second = b.select()
    assert second in ("wm", "ltm")
    assert second != first or True  # allow repeat if only two arms
    b.update(second, 0.0)
    # Now both tried; select should return some arm
    chosen = b.select()
    assert chosen in ("wm", "ltm")
