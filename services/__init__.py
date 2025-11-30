from common.logging import logger

"""Service entry points for the Soma stack.

This package provides lightweight wrappers around the individual
application services so they can be referenced consistently by tooling
and deployment manifests.  Each subpackage exposes a ``main`` accessor
that aligns with the consolidated architecture document.
"""

__all__ = ["sa01", "sb", "sah", "smf", "integrator_leader"]
