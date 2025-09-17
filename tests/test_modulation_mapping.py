from somabrain.persona_store import PersonaStore


class FakeNeuromodState:
    def __init__(
        self,
        dopamine=0.5,
        serotonin=0.4,
        noradrenaline=0.05,
        acetylcholine=0.02,
        timestamp=0,
    ):
        self.dopamine = dopamine
        self.serotonin = serotonin
        self.noradrenaline = noradrenaline
        self.acetylcholine = acetylcholine
        self.timestamp = timestamp


def test_modulation_numeric_values():
    base = FakeNeuromodState()
    store = PersonaStore()

    # Max curiosity -> acetylcholine should be clamped to 0.1
    s = store.modulate_neuromods(base, {"curiosity": 1.0})
    assert abs(s.acetylcholine - 0.1) < 1e-6

    # High risk tolerance -> noradrenaline reduced to 0.0
    s = store.modulate_neuromods(base, {"risk_tolerance": 1.0})
    assert abs(s.noradrenaline - 0.0) < 1e-6

    # Max reward seeking -> dopamine near 0.7 (0.4 + 0.3*1.0)
    s = store.modulate_neuromods(base, {"reward_seeking": 1.0})
    assert abs(s.dopamine - 0.7) < 1e-6

    # Calm increases serotonin by 0.2 * calm
    s = store.modulate_neuromods(base, {"calm": 0.5})
    assert abs(s.serotonin - (base.serotonin + 0.2 * 0.5)) < 1e-6

    # Combined example: curiosity=1.0, risk=1.0, reward=1.0, calm=1.0
    s = store.modulate_neuromods(
        base,
        {"curiosity": 1.0, "risk_tolerance": 1.0, "reward_seeking": 1.0, "calm": 1.0},
    )
    assert abs(s.acetylcholine - 0.1) < 1e-6
    assert abs(s.noradrenaline - 0.0) < 1e-6
    assert abs(s.dopamine - 0.7) < 1e-6
    assert abs(s.serotonin - (base.serotonin + 0.2 * 1.0)) < 1e-6
