"""
SomaBrain Package Initialization.
# Force Rebuild 2026-02-02 Cycle 2
SomaBrain is a comprehensive brain-inspired cognitive architecture for AI systems.
It implements advanced memory systems, neural processing, and cognitive functions
modeled after biological brain structures and processes.

This package provides the core functionality for:

- Multi-modal memory systems (episodic, semantic, working memory)
- Brain-inspired neural processing (thalamus, amygdala, prefrontal cortex)
- Advanced mathematical computations (quantum cognition, fractal analysis)
- Cognitive control and decision making
- Personality and neuromodulation systems
- Memory consolidation and replay
- Tool integration and action execution

The system is designed to provide human-like cognitive capabilities to AI agents,
with particular emphasis on memory, learning, and adaptive behavior.

Usage:
    from somabrain import *
    # Access version information
    print(__version__)

See the documentation for detailed API usage and configuration options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .version import PACKAGE_VERSION as __version__

if TYPE_CHECKING:
    from .controls import audit as audit

__all__ = ["__version__", "audit"]


def __getattr__(name: str) -> Any:
    """Resolve heavyweight package exports lazily.

    Importing ``somabrain`` should not eagerly pull in the controls and metrics
    subsystems because that makes tooling imports fragile and creates circular
    dependencies during Django/settings initialization.
    """

    if name == "audit":
        from .controls import audit as audit_module

        return audit_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
