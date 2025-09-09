import sys
from importlib import import_module


def main():
    am = import_module("somabrain.amygdala")
    nm_mod = import_module("somabrain.neuromodulators")
    cfg = am.SalienceConfig(
        w_novelty=0.6,
        w_error=0.4,
        threshold_store=0.5,
        threshold_act=0.7,
        hysteresis=0.0,
        use_soft=True,
        soft_temperature=0.1,
    )
    amy = am.AmygdalaSalience(cfg)
    nm = nm_mod.NeuromodState()
    # Increase s and verify gate probabilities increase
    p1 = amy.gate_probs(0.4, nm)
    p2 = amy.gate_probs(0.6, nm)
    assert p2[0] >= p1[0]
    assert p2[1] >= p1[1]
    print("Soft salience test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
