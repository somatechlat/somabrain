Configuration
=============

This page documents the canonical configuration options for SomaBrain. It is
kept intentionally small; see the top-level `CONFIGURATION.md` in the repository
for a more detailed, narrative explanation. The configuration options mirror
the fields defined in the `somabrain.config.Config` dataclass.

Key entries include memory backend selection, networking options, journal and
outbox settings, and feature flags used for autonomous operation.

Strict-real and full-stack flags
--------------------------------

These flags harden the application to run only with real services:

- ``SOMABRAIN_STRICT_REAL=1`` — disable stubs/mocks and require real backends.
- ``SOMABRAIN_FORCE_FULL_STACK=1`` — expect all managed dependencies to be reachable.
- ``SOMABRAIN_REQUIRE_MEMORY=1`` — fail startup if the external memory API is not reachable.

Service endpoints and ports can be customized, but the canonical defaults are:

- API: ``http://127.0.0.1:9696``
- Memory endpoint: ``http://127.0.0.1:9595``
- Redis: ``redis://127.0.0.1:6379/0``
- Postgres: ``postgresql://localhost:15432/postgres`` (or forwarded ``55432``)

Test harness overrides
----------------------

To run tests against a live API without spawning a local server:

.. code-block:: bash

	export SOMA_API_URL_LOCK_BYPASS=1
	export SOMA_API_URL=http://127.0.0.1:9696
	pytest -q

See also :doc:`strict_real` for end-to-end guidance.

Persistence verification
------------------------

When running the local developer stack some services use host bind-mounts or
named Docker volumes for persistent storage. A simple, non-disruptive test to
verify persistence is to write a marker file into the host path or volume and
read it back from another container mounting the same location. Example (host
path):

.. code-block:: bash

	marker="sb_persist_test_$(date +%s)_$RANDOM"
	printf "%s\n" "$marker" > ./data/redis/${marker}.txt
	docker run --rm -v "$(pwd)/data/redis":/mnt:ro busybox cat /mnt/${marker}.txt

For Docker volumes use an ephemeral container to write/read from the volume:

.. code-block:: bash

	docker run --rm -v somabrain_redis_data:/data busybox sh -c "printf '%s\n' ${marker} > /data/${marker}.txt"
	docker run --rm -v somabrain_redis_data:/data:ro busybox cat /data/${marker}.txt

If you see Redis errors about failing to open temp RDB files after confirming
the host path exists, the container may need a restart so the bind-mount is
properly visible to the process inside the container.
