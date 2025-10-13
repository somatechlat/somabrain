Memory modes and backend policy
===============================

Somabrain integrates with an external memory API over HTTP in production.
Historically, multiple modes existed (e.g., in-process "local" memory, Redis-only
maps, and HTTP). As of the strict-real policy, the application operates with
"external HTTP memory only" in all real deployments.

Summary
-------

- http (canonical)
	- Description: Reads/writes memory via the external memory API over HTTP.
	- Ports: 9595 by default (e.g., http://127.0.0.1:9595).
	- Production: Required. The application will fail startup if the service is
		not reachable when strict-real is enabled.

- local (deprecated/disabled under strict-real)
	- Description: An in-process memory map useful for early prototyping.
	- Status: Disabled when strict-real is set; not used in CI or production.

- redis-direct (legacy)
	- Description: Direct use of Redis data structures instead of the memory API.
	- Status: Not supported under strict-real; use the memory API which may
		manage Redis internally.

Read-your-writes under dev
--------------------------

For local development, the Docker dev profile runs the API with a single worker
so read-your-writes holds in-process immediately after a /remember. The recall
path includes defensive fallbacks (e.g., working-memory lift) to avoid cold-start
races without introducing mocks or synthetic behavior.

Configuration
-------------

Key environment variables:

- SOMABRAIN_REQUIRE_MEMORY=1
	- Enforces that the external memory API must be available at startup.

- SOMABRAIN_MEMORY_HTTP_ENDPOINT
	- The base URL for the external memory API, e.g., http://127.0.0.1:9595

See also: :doc:`strict_real` and :doc:`configuration` for end-to-end guidance.
