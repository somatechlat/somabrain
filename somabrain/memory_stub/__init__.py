"""Memory stub module intentionally disabled.

Importing this package raises so developers are forced to rely on the real
memory service instead of an in-process mock.
"""

from __future__ import annotations

import typing as _t


def __getattr__(name: str) -> _t.Any:  # pragma: no cover
	raise RuntimeError(
		"somabrain.memory_stub is disabled. Configure SOMABRAIN_MEMORY_HTTP_ENDPOINT "
		"to point at the real memory backend."
	)


__all__: list[str] = []
