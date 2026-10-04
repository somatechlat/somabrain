#!/usr/bin/env python3
"""Vault lifecycle for the standalone stack — init once, unseal on every boot.

This is what makes the deployment *resilient*. Vault server mode stores secrets
on disk and starts SEALED: until it is unsealed every read fails. Dev mode
avoids that by keeping secrets in RAM, which means a container restart silently
discards every credential and the whole stack fail-closes for no visible reason.

Responsibilities, in order:

1. **Init, exactly once.** If Vault reports it has never been initialised, run
   ``sys/init`` with a 1-of-1 threshold and persist the root token and unseal
   key into ``./secrets/``. Those two values are generated here, never invented
   by a human and never written anywhere else.
2. **Unseal, on every start.** If Vault is initialised but sealed, unseal it
   with the key from ``./secrets/brain_vault_unseal_key``.
3. **No-op when already up.** Safe to re-run at any time.

Properties this script must have — the same ones ``init_vault.py`` has:

* **Never prints a secret value.** Not on success, not on failure, not in an
  exception. Error messages name files and HTTP status codes only.
* **Fails closed.** A sealed Vault it cannot unseal is a hard error. The
  deployment must not proceed on a secrets store that cannot answer.
* **Idempotent.** Re-running never rotates a key that already exists.
* **No shell interpolation.** Keys travel as bytes from file to HTTP body.

Usage::

    python3 vault_unseal.py            # init if needed, then unseal
    python3 vault_unseal.py --status   # report state, change nothing

Environment::

    VAULT_ADDR   default http://localhost:20882
    SECRETS_DIR  default ./secrets next to this file
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

SCRIPT_DIR = Path(__file__).resolve().parent
SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", SCRIPT_DIR / "secrets"))
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:20882").rstrip("/")

# Brain-stack lifecycle credentials live in the shared t=0 directory under
# their OWN names. `vault_root_token` there is the AGENT stack's credential
# (and is an hvs. service token, not a root token) — overwriting it would
# destroy the agent's Vault access, and adopting it as this Vault's root is
# a minted second root of trust for a store it does not unlock.
UNSEAL_KEY_FILE = "brain_vault_unseal_key"
ROOT_TOKEN_FILE = "brain_vault_root_token"

# 1-of-1: one operator, one laptop. Production uses m-of-n shares and auto-unseal
# against a KMS — the custodian changes, this script's job does not.
SECRET_SHARES = 1
SECRET_THRESHOLD = 1

# sys/health status codes.
STATUS_ACTIVE = 200
STATUS_STANDBY = 429
STATUS_PERF_STANDBY = 472
STATUS_DR_STANDBY = 473
STATUS_NOT_INITIALIZED = 501
STATUS_SEALED = 503


class LifecycleError(Exception):
    """A condition that must stop the deployment. Never carries a secret."""


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def die(msg: str) -> NoReturn:
    raise LifecycleError(msg)


def _request(method: str, path: str, body: bytes | None = None, timeout: float = 10.0):
    """One HTTP call to Vault. Response bodies are returned raw-parsed and are
    never logged: sys/init and sys/unseal responses contain key material."""
    url = f"{VAULT_ADDR}/v1/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    except urllib.error.URLError as exc:
        # exc.reason can embed the URL; the URL carries no secret.
        die(f"cannot reach Vault at {VAULT_ADDR}: {exc.reason}")

    if not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return status, None


def health_status() -> int:
    status, _ = _request("GET", "sys/health")
    return status


def read_secret_file(name: str) -> bytes | None:
    full = SECRETS_DIR / name
    if not full.is_file():
        return None
    return full.read_bytes().strip() or None


def write_secret_file(name: str, value: str) -> Path:
    """Persist generated key material with owner-only permissions."""
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    full = SECRETS_DIR / name
    full.write_text(value + "\n", encoding="utf-8")
    os.chmod(full, 0o600)
    return full


def init_vault() -> None:
    """Initialise Vault and persist the generated root token and unseal key.

    Generates — it does not fabricate. A root token and an unseal key are
    supposed to come into existence here; that is Vault's own protocol, not an
    invented credential standing in for a missing one (VIBE Rule 4 / 164).
    """
    existing_token = read_secret_file(ROOT_TOKEN_FILE)
    existing_key = read_secret_file(UNSEAL_KEY_FILE)
    if existing_token or existing_key:
        die(
            f"Vault reports it is not initialised, but {SECRETS_DIR} already "
            f"holds {ROOT_TOKEN_FILE} and/or {UNSEAL_KEY_FILE}.\n"
            f"   Refusing to overwrite key material. If the Vault volume was "
            f"wiped, remove those two files deliberately and run again."
        )

    body = json.dumps(
        {"secret_shares": SECRET_SHARES, "secret_threshold": SECRET_THRESHOLD}
    ).encode("utf-8")
    status, data = _request("PUT", "sys/init", body)
    if status != 200 or not isinstance(data, dict):
        die(f"Vault refused sys/init (HTTP {status}). Nothing was written.")

    keys = data.get("keys_base64") or data.get("keys") or []
    root_token = data.get("root_token")
    if not keys or not root_token:
        die("Vault sys/init returned no key material; refusing to continue.")

    write_secret_file(ROOT_TOKEN_FILE, str(root_token))
    write_secret_file(UNSEAL_KEY_FILE, str(keys[0]))
    log(
        f"   Vault initialised. Key material written to {SECRETS_DIR}/ "
        f"({ROOT_TOKEN_FILE}, {UNSEAL_KEY_FILE}) with mode 0600."
    )
    log("   These two files are gitignored and are the ONLY copy. Back them up.")


def unseal_vault() -> None:
    key = read_secret_file(UNSEAL_KEY_FILE)
    if not key:
        die(
            f"Vault is sealed and {SECRETS_DIR / UNSEAL_KEY_FILE} is missing.\n"
            f"   Supply the unseal key to unseal it. It is never generated here: "
            f"generating one would not unseal this Vault, it would just look "
            f"like it worked."
        )
    body = json.dumps({"key": key.decode("utf-8")}).encode("utf-8")
    status, data = _request("PUT", "sys/unseal", body)
    if status != 200:
        die(
            f"Vault rejected the unseal key (HTTP {status}). The key was not "
            f"logged; check {SECRETS_DIR / UNSEAL_KEY_FILE} against this Vault."
        )
    if isinstance(data, dict) and data.get("sealed"):
        die("Vault is still sealed after unseal; threshold not met.")


def main() -> int:
    status_only = "--status" in sys.argv

    status = health_status()
    if status == STATUS_NOT_INITIALIZED:
        log("Vault: not initialised.")
        if status_only:
            return 0
        init_vault()
        status = health_status()

    if status in (STATUS_ACTIVE, STATUS_STANDBY, STATUS_PERF_STANDBY, STATUS_DR_STANDBY):
        log("Vault: unsealed and ready.")
        return 0

    if status == STATUS_SEALED:
        log("Vault: sealed.")
        if status_only:
            return 0
        unseal_vault()
        status = health_status()
        if status in (STATUS_ACTIVE, STATUS_STANDBY, STATUS_PERF_STANDBY, STATUS_DR_STANDBY):
            log("Vault: unsealed and ready.")
            return 0
        die(f"Vault still not ready after unseal (HTTP {status}).")

    die(
        f"Vault at {VAULT_ADDR} is in an unusable state (HTTP {status}). "
        f"Not initialised, not sealed-when-expected — refusing to continue."
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LifecycleError as exc:
        log(f"ERROR: {exc}")
        sys.exit(1)
