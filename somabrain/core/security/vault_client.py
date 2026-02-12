"""Vault Client - Centralized Secret Management.

ALL secrets fetched from HashiCorp Vault. NO secrets in ENV or DB.
Secrets: API keys, tokens, JWT secrets, private keys, passwords.

Usage:
    from somabrain.core.security.vault_client import get_secret

    jwt_secret = get_secret("jwt/secret")
    api_key = get_secret("api/key")
"""

import logging
from typing import Any, Optional
from functools import lru_cache

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class VaultNotConfigured(ImproperlyConfigured):
    """Vault not configured - secrets cannot be fetched."""
    pass


class SecretNotFound(ImproperlyConfigured):
    """Secret not found in Vault."""
    pass


@lru_cache(maxsize=1)
def _get_vault_client():
    """Get Vault client singleton. FAILS if not configured.

    Reads directly from os.environ to allow usage within settings.py.
    """
    import os
    vault_addr = os.environ.get("SOMABRAIN_VAULT_ADDR") or os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("SOMABRAIN_VAULT_TOKEN") or os.environ.get("VAULT_TOKEN")

    if not vault_addr or not vault_token:
        # Fallback: check if we are in a test environment where we might mock this
        if os.environ.get("DJANGO_SETTINGS_MODULE") and "test" in str(os.environ.get("DJANGO_SETTINGS_MODULE")):
             logger.warning("Vault not configured in test environment.")
             return None

        raise VaultNotConfigured(
            "Vault not configured. Set VAULT_ADDR and VAULT_TOKEN environment variables."
        )

    try:
        import hvac
        client = hvac.Client(url=vault_addr, token=vault_token)
        if not client.is_authenticated():
            raise VaultNotConfigured("Vault authentication failed.")
        logger.info(f"Vault client connected to {vault_addr}")
        return client
    except ImportError:
        raise VaultNotConfigured("hvac library not installed. Run: pip install hvac")
    except Exception as e:
        raise VaultNotConfigured(f"Vault connection failed: {e}")


def get_secret(path: str, key: Optional[str] = None) -> Any:
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

    try:
        # Read from KV v2 secrets engine
        secret = client.secrets.kv.v2.read_secret_version(path=path)
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


def get_private_key(name: str) -> str:
    """Get private key PEM from Vault."""
    return get_secret(f"somabrain/keys/{name}", "private_key")


def get_public_key(name: str) -> str:
    """Get public key PEM from Vault."""
    return get_secret(f"somabrain/keys/{name}", "public_key")


# =========== Secret Path Constants ===========

VAULT_PATHS = {
    "jwt_secret": "somabrain/auth",
    "constitution_keys": "somabrain/constitution",
    "api_keys": "somabrain/api-keys",
    "database": "somabrain/database",
    "oauth": "somabrain/oauth",
    "email": "somabrain/email",
}
