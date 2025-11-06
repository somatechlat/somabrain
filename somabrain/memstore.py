"""This module has been removed.

Historical in-memory/Redis memstore fallback is not supported under the
project's strict "no mocks/no fallbacks" policy. Use the real external
memory service via the HTTP client.
"""

raise ImportError("somabrain.memstore has been removed; use external memory service")
