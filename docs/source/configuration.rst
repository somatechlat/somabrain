Configuration
=============

This page documents the canonical configuration options for SomaBrain. It is
kept intentionally small; see the top-level `CONFIGURATION.md` in the repository
for a more detailed, narrative explanation. The configuration options mirror
the fields defined in the `somabrain.config.Config` dataclass.

Key entries include memory backend selection, networking options, journal and
outbox settings, and feature flags used for autonomous operation.

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

	docker run --rm -v memory_api_redis_data:/data busybox sh -c "printf '%s\n' ${marker} > /data/${marker}.txt"
	docker run --rm -v memory_api_redis_data:/data:ro busybox cat /data/${marker}.txt

If you see Redis errors about failing to open temp RDB files after confirming
the host path exists, the container may need a restart so the bind-mount is
properly visible to the process inside the container.
