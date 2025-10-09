"""Minimal stub for the :pypi:`PyJWT` package used in tests.

The production code imports ``jwt.decode`` and ``jwt.exceptions.PyJWTError``.
The real library is not installed in the CI environment, so this stub provides
the required symbols with permissive behaviour – any token decodes to an empty
payload and no verification is performed.  Authentication is effectively
disabled, which is acceptable because the test suite sets ``SOMABRAIN_DISABLE_AUTH``
or skips auth‑related tests.
"""

def decode(token: str, key, algorithms=None, options=None, **kwargs):  # noqa: D401
    """Return an empty payload for any JWT token.

    The signature is not verified; this implementation exists solely to keep
    imports working during test execution.
    """
    return {}

# The ``jwt.exceptions`` submodule is provided in ``jwt/exceptions.py``.
# No additional attribute is needed here; the import system will load that
# module when ``from jwt.exceptions import PyJWTError`` is executed.
