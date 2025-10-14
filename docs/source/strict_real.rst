Strict-real and full-stack mode
===============================

SomaBrain supports an enterprise "strict-real" mode that disables any internal
stubs or fallbacks and requires all external services to be available. This mode
is used for live development, CI, and production.

What strict-real enforces
-------------------------

- External memory HTTP endpoint only (no in-process or stub memory).
- Real metrics only (no synthetic/shim increments); Prometheus exposes counters
  produced by real middleware paths.
- Consolidation (/sleep) uses a bounded time budget to avoid long request hangs.
- Full dependency graph must be reachable at startup when SOMABRAIN_REQUIRE_MEMORY=1
  and SOMABRAIN_FORCE_FULL_STACK=1 are set.

Canonical ports
---------------

- Somabrain API: 9696
- Memory endpoint: 9595
- Redis: 6379
- Postgres: 15432 (or forwarded 55432 when tunneling)
- Kafka: 9092
- Prometheus: 9090
- OPA: 8181

Recommended environment
-----------------------

Set the following variables for strict-real local runs:

.. code-block:: bash

   export SOMABRAIN_STRICT_REAL=1
   export SOMABRAIN_FORCE_FULL_STACK=1
   export SOMABRAIN_REQUIRE_MEMORY=1
   export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://127.0.0.1:9595
   # Dev determinism for read-your-writes
   export SOMABRAIN_WORKERS=1

Tests against a running API
---------------------------

The test harness can target a live API instead of spawning its own server. To do so:

.. code-block:: bash

   export SOMA_API_URL_LOCK_BYPASS=1
  export SOMA_API_URL=http://127.0.0.1:9696
   pytest -q

Notes:

- Live tests assume the external memory endpoint and Redis are healthy; health checks will
  skip tests if dependencies are unavailable.
- In dev Docker, the API runs with a single worker; production deployments use
  multiple workers as configured by the orchestrator.

Related topics
--------------

- :doc:`configuration`
- :doc:`memory_modes`
- :doc:`api`
