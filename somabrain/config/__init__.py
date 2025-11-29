"""Legacy config compatibility layer.

The original code expected a ``Config`` dataclass providing attribute access to
configuration values.  The project now uses a ``pydantic`` ``Settings`` object
(``common.config.settings.settings``).  Attempting to convert that ``Settings``
instance with ``asdict`` raised ``TypeError: asdict() should be called on
dataclass instances``.

To maintain backward compatibility while avoiding the error, we expose the
``Settings`` instance directly via ``get_config`` and ``load_config``.  Existing
code that accesses attributes on the returned object will continue to work because
the ``Settings`` instance provides attribute access.
"""

from __future__ import annotations

from typing import Any
from types import SimpleNamespace

from common.config.settings import settings as _settings, Settings as _Settings


def load_config() -> _Settings:
    """Return the global ``Settings`` instance.

    This function mirrors the previous ``load_config`` signature but simply
    returns the shared ``Settings`` object.
    """
    return _settings


def get_config() -> Config:
    """Legacy accessor returning a ``Config`` instance.

    expose an ``http`` attribute. The ``Config`` subclass defined below provides
    this attribute via a property. To maintain backward compatibility we create a
    ``Config`` instance populated with the current settings values.
    """
    # ``_settings`` is a ``Settings`` (BaseSettings) instance. Converting it to a
    # ``dict`` respects any validation and defaults, then we instantiate ``Config``
    # which inherits from ``Settings`` and therefore retains the same fields.
    try:
        data = _settings.dict()
    except Exception as exc: raise
        # Fallback: use ``model_dump`` for pydantic v2 compatibility.
        data = getattr(_settings, "model_dump", lambda: dict(_settings))()
    return Config(**data)


# Compatibility alias for callers that import ``Settings`` directly.
Settings = _Settings


# Backward‑compatible ``Config`` alias
# Some modules (e.g., ``memory_client``) import ``Config`` expecting a dataclass
# with attribute access.  The modern ``Settings`` instance provides the same
# interface, so we expose a thin subclass that inherits from ``Settings``.  This
# satisfies ``isinstance`` checks and attribute lookups without re‑introducing
# the problematic ``asdict`` logic.
class Config(_Settings):
    """Legacy alias for the global ``Settings`` instance.

    Instances of ``Config`` behave exactly like ``Settings``.  Existing code that
    creates a ``Config`` object will receive a ``Settings`` subclass instance.
    """

    """Legacy alias for the global ``Settings`` instance.

    Provides a ``http`` attribute for compatibility with older code that
    expects ``cfg.http`` to contain ``token`` and ``endpoint`` fields. The
    underlying ``Settings`` stores these values as ``memory_http_token`` and
    ``memory_http_endpoint``. This property constructs a lightweight object
    exposing the expected attribute names.
    """

    @property
    def http(self) -> SimpleNamespace:
        """Return an object mimicking the old ``http`` config.

        The original implementation accessed ``cfg.http.token`` and
        ``cfg.http.endpoint``. New settings expose these as top‑level fields.
        This property creates a simple namespace with the same attribute names
        populated from the current settings values.
        """

        return SimpleNamespace(
            token=getattr(self, "memory_http_token", None),
            endpoint=getattr(self, "memory_http_endpoint", ""),
        )
