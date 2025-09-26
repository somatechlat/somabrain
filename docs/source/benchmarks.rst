9797Benchmarks
=================

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

RAG Learning Bench (End-to-End)
--------------------------------

Goal: demonstrate truthful, end-to-end “learning” from retrieval persistence and graph linking, and its impact on both retrieval quality and planning.

What it measures
- Retrieval uplift: Recall@K proxy (hit-rate against a ground-truth set) before vs. after persisting a RAG session.
- Planning uplift: fraction of goal-aligned steps returned by the planner after RAG adds graph edges (``rag_session``, ``retrieved_with``).
- Latency: wall-clock for each retrieval phase.

How it works
1. Seeds a small synthetic corpus of “tool” documents (e.g., FastAPI, uvicorn, virtualenv) via ``/remember``.
2. Baseline: calls ``/rag/retrieve`` with ``retrievers=["vector"]`` and no persistence.
3. Persisted session: calls ``/rag/retrieve`` with ``retrievers=["vector","wm"]`` and ``persist=true``; this stores a session and creates graph edges (query→session, session→docs).
4. Post-persist graph: calls ``/rag/retrieve`` with ``retrievers=["graph"]`` to leverage the new edges.
5. Planning: calls ``/plan/suggest`` with and without the RAG edges in ``rel_types``.

Run it
::

   source .venv/bin/activate
   python benchmarks/agent_coding_bench.py --base http://localhost:9696 --tenant benchdev --out benchmarks/results_agent_coding.json

Interpreting results
- Baseline vector-only hit-rate is a proxy for pre-RAG orchestration.
- Post-persist graph-only hit-rate should increase; if it returns only the session node, set ``graph_hops=2`` in config to allow query→session→docs in one hop.
- Planning post-persist should include more goal-aligned steps when ``rel_types`` includes ``rag_session`` and ``retrieved_with``.

Artifacts
- JSON results: ``benchmarks/results_agent_coding.json`` (per run)
- Metrics: exposed at ``/metrics`` (e.g., ``somabrain_rag_requests_total``, ``somabrain_rag_retrieve_latency_seconds``)
