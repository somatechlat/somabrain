from somabrain.sleep import SleepState, SleepStateManager


def test_eta_zero_deep_freeze():
    mgr = SleepStateManager()
    deep = mgr.compute_parameters(SleepState.DEEP)
    freeze = mgr.compute_parameters(SleepState.FREEZE)
    assert deep['eta'] == 0.0
    assert freeze['eta'] == 0.0


def test_monotonic_scaling():
    mgr = SleepStateManager()
    active = mgr.compute_parameters(SleepState.ACTIVE)
    light = mgr.compute_parameters(SleepState.LIGHT)
    deep = mgr.compute_parameters(SleepState.DEEP)
    # K decreases, t decreases, tau decreases, B increases
    assert active['K'] >= light['K'] >= deep['K']
    assert active['t'] >= light['t'] >= deep['t']
    assert active['tau'] >= light['tau'] >= deep['tau']
    assert active['B'] <= light['B'] <= deep['B']
