"""OPA policy builder utilities.

This module provides a simple function to generate an OPA Rego policy
from a constitution dictionary. At the moment the policy is static and
read from the template file ``ops/opa/policies/constitution.rego``.
Future versions may render dynamic rules based on the constitution
contents.
"""

from __future__ import annotations

import pathlib
from typing import Dict


def build_policy(constitution: Dict) -> str:
    """Return a Rego policy string for the given ``constitution``.

    The current implementation loads a static template located at
    ``ops/opa/policies/constitution.rego`` relative to the repository root.
    ``constitution`` is accepted for API compatibility – callers can pass
    the loaded constitution dict, and the function could later interpolate
    values into the template.
    """
    # Resolve path relative to repository root (two levels up from this file)
    template_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "ops"
        / "opa"
        / "policies"
        / "constitution.rego"
    )
    try:
        return template_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(
            f"Failed to read OPA policy template at {template_path}: {e}"
        )


__all__ = ["build_policy"]