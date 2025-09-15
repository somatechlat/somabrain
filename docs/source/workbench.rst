Numerics Workbench
==================

This workbench provides a simple, deterministic script to exercise numeric
primitives and produce a JSON summary for release artifacts.

How to run
----------

Activate your venv and run:

.. code-block:: sh

    . venv/bin/activate
    python benchmarks/numerics_workbench.py

The script writes: ``benchmarks/workbench_numerics_results.json``

What it checks
--------------

- tiny-floor across float32/float64 and multiple dimensions
- unitary FFT roundtrip error
- role generation and renormalization
- bind/unbind sanity via exact unbinding for unitary roles

Where to find it
----------------

- script: ``benchmarks/numerics_workbench.py``
- test: ``tests/test_numerics_contract.py``
- docs: this page
