import sys
from importlib import import_module


def main():
    sup_mod = import_module("somabrain.supervisor")
    nm_mod = import_module("somabrain.neuromodulators")
    sup = sup_mod.Supervisor(sup_mod.SupervisorConfig(gain=0.5, limit=0.05))
    nm = nm_mod.NeuromodState(
        dopamine=0.4, acetylcholine=0.01, noradrenaline=0.01, serotonin=0.5
    )
    nm2, F, mag = sup.adjust(nm, novelty=0.8, pred_error=0.2)
    assert F > 0
    assert mag > 0
    # dopamine and ACh should increase given novelty/error
    assert nm2.dopamine >= nm.dopamine
    assert nm2.acetylcholine >= nm.acetylcholine
    print("Supervisor test passed.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    main()
