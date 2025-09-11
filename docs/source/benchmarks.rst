Benchmarks
==========

.. note::
    Use the `benchmarks/bench_numerics.py` harness to reproduce results. The harness
    writes `benchmarks/bench_numerics_results.json` and plots to `benchmarks/plots/`.

Reproducing the canonical sweep::

     source .venv/bin/activate
     python benchmarks/bench_numerics.py \
         --unbind-current somabrain.quantum.unbind_exact \
         --unbind-proposed somabrain.quantum.unbind_exact_unitary \
         --normalize-current somabrain.numerics.normalize_array \
         --normalize-proposed somabrain.numerics.normalize_array \
         --dtype f32 f64 --D 256 1024 4096 --trials 200 --roles unitary nonunitary --postnorm
