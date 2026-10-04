"""Vault Client - Centralized Secret Management.

ALL secrets fetched from HashiCorp Vault. NO secrets in ENV or DB.
Secrets: API keys, tokens, JWT secrets, private keys, passwords.

Usage:
    from somabrain.core.security.vault_client import get_secret

    jwt_secret = get_secret("jwt/secret")
    api_key = get_secret("api/key")
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class VaultNotConfigured(ImproperlyConfigured):
    """Vault not configured - secrets cannot be fetched."""



class SecretNotFound(ImproperlyConfigured):
    """Secret not found in Vault."""


class VaultAuthError(VaultNotConfigured):
    """Vault could not be authenticated to.

    This is an infrastructure failure, NOT a missing secret. It must never be
    reported as ``None``: a caller that cannot reach Vault has no idea whether
    the secret exists (VIBE Rule 91 / Rule 164).
    """


# Token is a FILE, never an environment variable (VIBE Rule 164). A path is
# topology; the credential it names is not. There is deliberately no token
# value read from the process environment anywhere in this module — exporting
# a token into a shell leaves it in ``ps``, in ``/proc/*/environ`` and in
# every crash dump.
VAULT_TOKEN_FILE_ENV = "VAULT_TOKEN_FILE"


def _read_vault_token() -> str:
    """Return the Vault token read from ``VAULT_TOKEN_FILE``.

    Raises:
        VaultAuthError: if the path is unset, the file is unreadable, or the
            file is empty. Absence of a token is never "no secrets available".
    """
    token_path = os.environ.get(VAULT_TOKEN_FILE_ENV, "").strip()
    if not token_path:
        raise VaultAuthError(
            f"VIBE Rule 164 VIOLATION: no Vault token available. Point "
            f"{VAULT_TOKEN_FILE_ENV} at a file containing the token. The token "
            f"is a credential and is delivered as a file — it is never read "
            f"from the environment and there is no fallback."
        )
    try:
        resolved = Path(token_path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise VaultAuthError(
            f"VIBE Rule 164 VIOLATION: cannot read the Vault token file named "
            f"by {VAULT_TOKEN_FILE_ENV} at {token_path!r}: "
            f"{exc.strerror or exc}. Fix the path or the file's permissions "
            f"(0600); the token is never read from the environment."
        ) from None
    if not resolved:
        raise VaultAuthError(
            f"VIBE Rule 164 VIOLATION: the Vault token file named by "
            f"{VAULT_TOKEN_FILE_ENV} at {token_path!r} is empty. An empty "
            f"token is not a valid credential and must not be treated as "
            f"'no secrets'."
        )
    return resolved



def _split_secret_path(path: str) -> tuple[str, str]:
    """Split a logical secret path into KV mount point and relative path."""
    import os

    normalized = path.strip("/")
    if not normalized:
        raise SecretNotFound("Vault secret path cannot be empty")

    explicit_mount = (
        os.environ.get("SOMABRAIN_VAULT_KV_MOUNT")
        or os.environ.get("SOMABRAIN_VAULT_MOUNT_POINT")
        or ""
    ).strip("/")
    if explicit_mount:
        prefix = f"{explicit_mount}/"
        if normalized.startswith(prefix):
            return explicit_mount, normalized[len(prefix) :]
        return explicit_mount, normalized

    if "/" not in normalized:
        return "secret", normalized

    mount_point, relative_path = normalized.split("/", 1)
    return mount_point, relative_path


@lru_cache(maxsize=1)
def _get_vault_client() -> Any | None:
    """Get Vault client singleton. FAILS if not configured.

    Vault address is topology and may come from the environment. The token is
    a credential and is read only from the file named by
    ``VAULT_TOKEN_FILE`` (VIBE Rule 164).
    """
    vault_addr = os.environ.get("SOMABRAIN_VAULT_ADDR") or os.environ.get("VAULT_ADDR")
    if not vault_addr:
        raise VaultNotConfigured(
            "Vault not configured. Set VAULT_ADDR to the Vault API address "
            "(topology). The token is supplied via VAULT_TOKEN_FILE, never as "
            "an environment variable."
        )

    vault_token = _read_vault_token()

    try:
        import hvac

        client = hvac.Client(url=vault_addr, token=vault_token)
        if not client.is_authenticated():
            raise VaultAuthError("Vault authentication failed.")
        logger.info(f"Vault client connected to {vault_addr}")
        return client
    except ImportError:
        raise VaultNotConfigured("hvac library not installed. Run: pip install hvac")
    except VaultAuthError:
        raise
    except Exception as e:
        raise VaultNotConfigured(f"Vault connection failed: {e}")


def get_secret(path: str, key: str | None = None) -> Any:
    """Get secret from Vault. FAILS if not found.

    Args:
        path: Vault path (e.g., "somabrain/jwt" or "somabrain/api-keys")
        key: Optional specific key within the secret data

    Returns:
        Secret value (or entire data dict if key not specified)

    Raises:
        SecretNotFound: If path/key doesn't exist
        VaultNotConfigured: If Vault not set up
    """
    client = _get_vault_client()
    if client is None:
        raise VaultNotConfigured("Vault not configured for this environment.")

    try:
        # Read from KV v2 secrets engine
        mount_point, relative_path = _split_secret_path(path)
        secret = client.secrets.kv.v2.read_secret_version(
            path=relative_path,
            mount_point=mount_point,
        )
        data = secret["data"]["data"]

        if key:
            if key not in data:
                raise SecretNotFound(f"Key '{key}' not found at path '{path}'")
            return data[key]
        return data

    except Exception as e:
        if "SecretNotFound" in str(type(e)):
            raise
        raise SecretNotFound(f"Secret at '{path}' not found: {e}")


def get_jwt_secret() -> str:
    """Get JWT secret from Vault."""
    return get_secret("somabrain/auth", "jwt_secret")


def get_api_key(service: str) -> str:
    """Get API key for a service from Vault."""
    return get_secret("somabrain/api-keys", service)


def get_db_credentials() -> dict:
    """Get database credentials from Vault."""
    return get_secret("somabrain/database")


def get_runtime_secrets() -> dict:
    """Get runtime service secrets from Vault.

    ``memory_http_token`` is NOT taken from ``somabrain/runtime``. It is the
    shared agent credential (see :func:`get_runtime_secret`) and is merged in
    from that one authority so this dict cannot disagree with a direct read.
    When ``somabrain/runtime`` itself is absent the other runtime keys stay
    absent; the shared memory token is still resolved (and still raises when
    it is not provisioned).
    """
    data: dict = {}
    try:
        data.update(get_secret("somabrain/runtime") or {})
    except SecretNotFound:
        pass
    data["memory_http_token"] = get_runtime_secret("memory_http_token")
    return data


def get_runtime_secret(key: str) -> Any:
    """Get a specific runtime service secret from Vault.

    The memory HTTP token is the shared credential the agent presents on every
    call. The agent stack seeds it as the key ``somabrain_memory_http_token``
    inside the single KV document at ``agent/credentials`` (mount ``secret``) —
    see somaAgent01 ``infra/standalone/init_vault.py`` and
    ``services/common/unified_secret_manager.get_credential``. Reading one
    value from one authority is the point: two independently seeded tokens is
    exactly the 401 this caused. Everything else stays on this service's own
    path.
    """
    if key == "memory_http_token":
        return get_secret(SHARED_CREDENTIALS_PATH, MEMORY_HTTP_TOKEN_KEY)
    return get_secret("somabrain/runtime", key)


def get_private_key(name: str) -> str:
    """Get private key PEM from Vault."""
    return get_secret(f"somabrain/keys/{name}", "private_key")


def get_public_key(name: str) -> str:
    """Get public key PEM from Vault."""
    return get_secret(f"somabrain/keys/{name}", "public_key")


# =========== Secret Path Constants ===========

# Shared agent-credential document (KV v2). One document, one key per
# credential — the key name is load-bearing and matches
# UnifiedSecretManager.get_credential("somabrain_memory_http_token").
# Path form here is "mount/relative" as _split_secret_path expects.
SHARED_CREDENTIALS_PATH = "secret/agent/credentials"
MEMORY_HTTP_TOKEN_KEY = "somabrain_memory_http_token"

VAULT_PATHS = {
    "jwt_secret": "somabrain/auth",
    "constitution_keys": "somabrain/constitution",
    "api_keys": "somabrain/api-keys",
    "database": "somabrain/database",
    "runtime": "somabrain/runtime",
    "oauth": "somabrain/oauth",
    "email": "somabrain/email",
    "shared_credentials": SHARED_CREDENTIALS_PATH,
}
