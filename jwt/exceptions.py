"""Exception definitions for the stubbed ``jwt`` package.

Only the ``PyJWTError`` base class is required by the SomaBrain code. The
real ``PyJWT`` library defines a hierarchy of exceptions; providing this base
class satisfies the ``from jwt.exceptions import PyJWTError`` import used in
``somabrain.auth``.
"""

class PyJWTError(Exception):
    """Base exception for JWT decoding errors (stub)."""
