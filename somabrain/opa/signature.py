"""Utilities for signing and verifying OPA policies.

The policy is signed with a PEM private key and verified against a PEM
public key. Signatures are returned as hex strings for storage in Redis.
"""

from __future__ import annotations

import base64
import pathlib
from typing import Any, cast  # noqa: E402

# Cryptography is an optional dependency; import lazily with alternative.
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key,
        load_pem_public_key,
    )
except Exception:  # pragma: no cover
    hashes = None
    padding = None
    load_pem_private_key = None
    load_pem_public_key = None


def sign_policy(policy: str, private_key_path: str) -> str:
    """Sign ``policy`` using a PEM private key.

    The heavy ``cryptography`` imports are performed lazily so the module can be
    imported even when the library is not installed (e.g., in minimal test
    environments). If the required classes are unavailable, an informative
    ``ImportError`` is raised.
    """
    # A valid private key path is required; no stand-ins or alternatives.
    if not private_key_path:
        raise ValueError("private_key_path is required for OPA policy signing")
    # Import lazily – raise if missing.
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
    except Exception as e:
        raise ImportError("cryptography library required for signing OPA policies") from e

    key_path = pathlib.Path(private_key_path).expanduser()
    with key_path.open("rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)
    # ``sign`` is defined on concrete private‑key classes (e.g., RSAPrivateKey).
    # The exact runtime type depends on the key format; we silence static
    # checking here because the attribute is guaranteed by the ``cryptography``
    # library at runtime.
    # To avoid positional‑argument mismatches we cast the key to ``Any``.
    from typing import (
        Any,
        cast,
    )  # noqa: E402  (import after top‑level imports is acceptable here)

    private_key_any = cast(Any, private_key)
    signature = private_key_any.sign(
        policy.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return signature.hex()


def verify_policy(policy: str, signature_hex: str, public_key_path: str) -> bool:
    """Verify a hex/base64 ``signature_hex`` for ``policy`` using a PEM public key.

    Performs lazy imports of ``cryptography`` similar to :func:`sign_policy`.
    Returns ``True`` on successful verification, ``False`` otherwise.
    """
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except Exception as e:
        raise ImportError("cryptography library required for verifying OPA policies") from e

    key_path = pathlib.Path(public_key_path).expanduser()
    with key_path.open("rb") as f:
        public_key = load_pem_public_key(f.read())
    try:
        signature = bytes.fromhex(signature_hex)
    except Exception:
        # try base64 alternative
        try:
            signature = base64.b64decode(signature_hex)
        except Exception:
            return False
    try:
        # ``verify`` exists on concrete public‑key classes. We silence static
        # checking for the same reason as in ``sign_policy``.
        # ``verify`` has a variable signature depending on the concrete key
        # class.  Suppress the argument‑count check for the same reason as
        # ``sign`` above.
        # Cast to ``Any`` to silence argument‑count checking.
        public_key_any = cast(Any, public_key)
        public_key_any.verify(
            signature,
            policy.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


__all__ = ["sign_policy", "verify_policy"]
