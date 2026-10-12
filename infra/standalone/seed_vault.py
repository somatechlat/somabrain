#!/usr/bin/env python3
"""SomaBrain Vault seeder — t=0 files → process memory → Vault HTTP body.

R-SEC-01 / Rule 164 / SOMA-STD-BOOTSTRAP-001 F-06 + F-15.

**Secrets never touch argv, shell vars, or a durable filesystem.**

This replaces the former ``curl -d '{...password...}'`` seeder, which put every
credential on the ``curl`` command line (visible in ``ps`` / ``/proc/*/cmdline``
for the life of the process). Here every value is read into process memory and
sent as an HTTP request body via ``urllib`` — the body is never an argv token.

Properties (mirrors ``somaAgent01/infra/standalone/init_vault.py``):

* **Never prints a secret value.** Not on success, not on failure, not in an
  exception. Errors name keys and HTTP status only.
* **Never places a secret in argv.** No ``curl -d``, no ``-H "X-Vault-Token: …"``.
  The token rides in an in-memory header object.
* **Fails closed.** Missing t=0 file, empty value, sealed Vault, or HTTP error
  is a hard error. An empty string is never written (F-6 / F-8).
* **Idempotent.** Without ``--force``, a secret key already in Vault is left
  alone so hand-rotation survives ``compose up``. Topology keys are refreshed
  (they are not rotated). With ``--force``, every key is rewritten.
* **Merge-safe.** KV v2 POST replaces the whole ``data`` object. Every write
  reads first, merges in memory, writes the whole object back, then asserts
  the key landed and every sibling survived (F-20 / the real data-loss incident).

Usage::

    python3 seed_vault.py            # seed missing secret keys (idempotent)
    python3 seed_vault.py --force    # rewrite every key
    python3 seed_vault.py --check    # report presence, write nothing

Environment (paths and topology only — never secret values)::

    SOMABRAIN_VAULT_ADDR              Vault API address
    SOMABRAIN_VAULT_TOKEN_FILE        path to the root/bootstrap token file
    POSTGRES_PASSWORD_FILE            path to the DB password
    SOMABRAIN_JWT_SECRET_FILE         path to the JWT signing secret
    SUPERVISOR_HTTP_PASS_FILE         path to the supervisor password
    SOMABRAIN_API_TOKEN_FILE          path to the API token (optional)
    SOMABRAIN_MEMORY_HTTP_TOKEN_FILE  path to the shared agent↔brain token
    POSTGRES_USER / POSTGRES_DB / POSTGRES_HOST / POSTGRES_PORT   topology
    SOMABRAIN_REDIS_URL                                              topology
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

FORCE = "--force" in sys.argv
CHECK = "--check" in sys.argv


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"ERROR: required environment variable {name} is not set.\n"
            f"   Bootstrap topology is required and never defaulted (Rule 91)."
        )
    return value


def read_secret_file(env_name: str, *, required: bool = True) -> str | None:
    """Read one credential from a t=0 file into process memory.

    The env var names a PATH (topology). The VALUE never enters ENV, argv, or
    a log line. Trailing newlines are stripped — the same trim every consumer
    applies — so Vault stores what readers will actually see.
    """
    path = os.environ.get(env_name)
    if not path:
        if required:
            raise SystemExit(
                f"ERROR: {env_name} is not set. It must name a t=0 secret file "
                f"path (R-SEC-01: the value never lives in ENV)."
            )
        return None
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        if required:
            raise SystemExit(
                f"ERROR: cannot read secret file for {env_name} "
                f"({type(e).__name__}). Value was not logged."
            )
        log(f"  (no t=0 file at {path}; leaving any existing Vault value untouched)")
        return None
    value = raw.decode("utf-8", errors="strict").replace("\r", "").replace("\n", "").strip()
    if not value:
        if required:
            raise SystemExit(
                f"ERROR: secret file for {env_name} is empty after trimming. "
                f"Refusing to invent a substitute (Rule 91 / Rule 164)."
            )
        log(f"  (t=0 file for {env_name} is blank; leaving Vault value untouched)")
        return None
    return value


class Vault:
    """Minimal KV v2 client. Token and bodies live only in this process."""

    def __init__(self, addr: str, token: str) -> None:
        self.addr = addr.rstrip("/")
        self.token = token

    def req(self, method: str, path: str, body: dict | None = None):
        url = f"{self.addr}/v1/{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        # Header object — NOT argv. The token is never a process argument.
        req.add_header("X-Vault-Token", self.token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw) if raw else {}
            except Exception:
                payload = {}
            return e.code, payload
        except Exception as e:
            raise SystemExit(
                f"ERROR: Vault request {method} {path} failed: {type(e).__name__}"
            )

    def wait_healthy(self, attempts: int = 30) -> None:
        for _ in range(attempts):
            try:
                status, _ = self.req("GET", "sys/health")
                return
            except SystemExit:
                time.sleep(1)
        raise SystemExit(f"ERROR: Vault at {self.addr} is unreachable.")

    def ensure_mount(self, mount: str) -> None:
        status, _ = self.req("POST", f"sys/mounts/{mount}", {"type": "kv-v2"})
        # 204 = created, 400 = already mounted. Both are fine (idempotent).
        if status not in (204, 400):
            raise SystemExit(f"ERROR: mount {mount} -> HTTP {status}.")

    def kv2_read(self, mount: str, path: str) -> dict:
        status, payload = self.req("GET", f"{mount}/data/{path}")
        if status == 404:
            return {}
        if status != 200:
            raise SystemExit(f"ERROR: read {mount}/{path} -> HTTP {status}.")
        return (payload.get("data") or {}).get("data") or {}

    def kv2_write(self, mount: str, path: str, data: dict) -> None:
        status, _ = self.req("POST", f"{mount}/data/{path}", {"data": data})
        if status not in (200, 204):
            # F-6: a rejected write is a hard error. Never continue as if saved.
            raise SystemExit(
                f"ERROR: write {mount}/{path} -> HTTP {status}. Value was not logged."
            )


def seed_document(
    vault: Vault,
    mount: str,
    path: str,
    *,
    secrets: dict[str, str],
    topology: dict[str, object] | None = None,
) -> None:
    """Merge-seed one KV v2 document.

    * Secret keys: skip-if-present unless ``--force`` (rotation survives).
    * Topology keys: always refreshed (not a secret, not rotated).
    * The write is always a full read-merge-write so siblings never die.
    """
    label = f"{mount}/{path}"
    existing = vault.kv2_read(mount, path)

    if CHECK:
        for key in secrets:
            present = bool(existing.get(key))
            log(f"   {'present' if present else 'MISSING'}  {label}[{key}]")
        return

    data = dict(existing)
    wrote_any = False
    skipped: list[str] = []

    for key, value in secrets.items():
        if not value:
            raise SystemExit(
                f"ERROR: empty value for {label}[{key}]. Refusing (F-8)."
            )
        if not FORCE and existing.get(key):
            skipped.append(key)
            continue
        data[key] = value
        wrote_any = True

    if topology:
        for key, value in topology.items():
            if data.get(key) != value:
                data[key] = value
                wrote_any = True

    if skipped:
        log(f"   – skipped (already in Vault): {label}[{', '.join(skipped)}]")

    if not wrote_any:
        log(f"   – unchanged: {label}")
        return

    # Snapshot key set BEFORE the write so we can prove no sibling died.
    pre_keys = set(existing.keys())

    vault.kv2_write(mount, path, data)

    # Read-back assert — compare in memory only. F-7.
    stored = vault.kv2_read(mount, path)
    for key, value in secrets.items():
        if key not in data:
            continue
        if stored.get(key) != data.get(key):
            raise SystemExit(
                f"ERROR: read-back mismatch at {label}[{key}]. "
                f"Value was not logged. Refusing to treat the seed as successful."
            )
    lost = pre_keys - set(stored.keys())
    if lost:
        raise SystemExit(
            f"ERROR: merge write destroyed sibling key(s) {sorted(lost)} in {label}. "
            f"KV v2 POST replaces the whole document. F-20."
        )
    log(f"   ✔ seeded {label}  ({len(stored)} key(s); values in memory→Vault only)")


def main() -> int:
    vault_addr = require_env("SOMABRAIN_VAULT_ADDR")
    token_path = require_env("SOMABRAIN_VAULT_TOKEN_FILE")

    try:
        token = open(token_path, "rb").read().decode("utf-8").strip()
    except OSError as e:
        raise SystemExit(
            f"ERROR: cannot read Vault bootstrap token file ({type(e).__name__}). "
            f"R-SEC-03: the token is a FILE, never an ENV value."
        )
    if not token:
        raise SystemExit("ERROR: Vault bootstrap token file is empty.")

    # --- Credentials: values enter this process as Python strings only. ------
    postgres_password = read_secret_file("POSTGRES_PASSWORD_FILE")
    jwt_secret = read_secret_file("SOMABRAIN_JWT_SECRET_FILE")
    supervisor_pass = read_secret_file("SUPERVISOR_HTTP_PASS_FILE")
    api_token = read_secret_file("SOMABRAIN_API_TOKEN_FILE", required=False)
    memory_token = read_secret_file("SOMABRAIN_MEMORY_HTTP_TOKEN_FILE")

    vault = Vault(vault_addr, token)
    vault.wait_healthy()

    # Mount KV v2 — `somabrain` for this service's own secrets, `secret` for
    # the shared agent/credentials document the reader expects.
    vault.ensure_mount("somabrain")
    vault.ensure_mount("secret")

    log("📝 Credentials → somabrain/*  (t=0 file → memory → HTTP body)")

    # 1. Database. Password is a secret (skip-if-present); topology refreshed.
    seed_document(
        vault,
        "somabrain",
        "database",
        secrets={"password": postgres_password},
        topology={
            "username": require_env("POSTGRES_USER"),
            "host": require_env("POSTGRES_HOST"),
            "port": require_env("POSTGRES_PORT"),
            "dbname": require_env("POSTGRES_DB"),
        },
    )

    # 2. Redis URL is topology (no credential in this stack's URL).
    seed_document(
        vault,
        "somabrain",
        "redis",
        secrets={},
        topology={"url": require_env("SOMABRAIN_REDIS_URL")},
    )

    # 3. JWT signing secret.
    seed_document(
        vault,
        "somabrain",
        "auth",
        secrets={"jwt_secret": jwt_secret},
    )

    # 4. Runtime service secrets — this service's OWN keys only. The shared
    #    memory token deliberately does NOT live here.
    runtime_secrets: dict[str, str] = {"supervisor_http_pass": supervisor_pass}
    if api_token:
        runtime_secrets["api_token"] = api_token
    seed_document(vault, "somabrain", "runtime", secrets=runtime_secrets)

    # 5. SHARED agent↔brain trust boundary. Exactly the document and key
    #    vault_client reads (SHARED_CREDENTIALS_PATH / MEMORY_HTTP_TOKEN_KEY).
    #    MERGE, never replace — a one-key write deletes every sibling.
    seed_document(
        vault,
        "secret",
        "agent/credentials",
        secrets={"somabrain_memory_http_token": memory_token},
    )

    # Drop references. The values lived only in this process and in Vault.
    del postgres_password, jwt_secret, supervisor_pass, api_token, memory_token

    if CHECK:
        log("✅ check complete — nothing written.")
    else:
        log("✅ Vault seeded — values exist ONLY in Vault. Nothing was written to argv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
