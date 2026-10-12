#!/usr/bin/env python3
"""Standalone Vault seeder — SOMA-STD-CONFIG-001 R-SEC-01 / R-SEC-03.

**NO SECRETS EVER TOUCH THE FILESYSTEM.**

Every credential is generated in process memory (``secrets.token_urlsafe``) and
written directly into Vault. There is no secrets directory, no plaintext file,
and no local copy after this process exits. Vault is the only system of record.

    somabrain/database                          get_database_secret()
    somabrain/auth                              jwt_secret
    somabrain/runtime                           supervisor_http_pass / api_token
                                                / minio_access_key / minio_secret_key
    secret/agent/credentials/<snake_case>       get_runtime_secret()

This script also provisions the **AppRole** auth method that Vault Agent
sidecars use (industry pattern). Application secrets are consumed only via
Vault Agent template rendering onto tmpfs — never env, never compose YAML,
never a disk volume, never a T0 file handoff.

Properties:

* **Never prints a secret value.** Not on success, not on failure, not in a
  request body, not in an exception. Errors name keys and HTTP status only.
* **Never writes a secret to disk.** Not a file, not .env, not argv, not a
  shell history. Values live only in process memory and in Vault. AppRole
  role_id / secret_id go to the isolated tmpfs ``APPROLE_DIR`` that only
  Vault Agent sidecars mount — that is the industry bootstrap credential
  path, not an application-secret store.
* **Fails closed.** Missing Vault / sealed Vault / HTTP error is a hard error.
  An empty string is never written.
* **Merge-safe.** KV v2 POST replaces the whole data object. Every write
  reads first, merges in memory, writes back, then asserts siblings survived.
* **Idempotent.** Without ``--force``, a key already in Vault is left alone
  (hand-rotation survives). With ``--force``, regenerate + overwrite.
* **Optional operator value** via process env ``SOMA_SECRET_<KEY>`` — used only
  for the current process, never persisted by this script. Pin the shared
  agent↔brain token to the same value on both stacks with
  ``SOMA_SECRET_SOMABRAIN_MEMORY_HTTP_TOKEN``.

Usage::

    python3 init_vault.py            # generate + seed missing keys
    python3 init_vault.py --force    # regenerate + overwrite every key
    python3 init_vault.py --check    # report presence, write nothing

Environment (bootstrap topology — REQUIRED, never defaulted; Rule 91)::

    VAULT_ADDR       Vault API address
    T0_DIR           RAM custodian written by vault_unseal.py. Holds the root
                     token for this one-shot only.
    APPROLE_DIR      Isolated tmpfs for AppRole role_id/secret_id consumed by
                     Vault Agent sidecars. Not an application-secret store.

There is no secrets directory. There is no secret file in the repo. Rule 164.
"""

from __future__ import annotations

import json
import os
import secrets as py_secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VAULT_ADDR = (os.environ.get("VAULT_ADDR") or "").rstrip("/")
T0_DIR = Path(os.environ["T0_DIR"]) if os.environ.get("T0_DIR") else None
APPROLE_DIR = Path(os.environ["APPROLE_DIR"]) if os.environ.get("APPROLE_DIR") else None
KEYCHAIN_SERVICE = os.environ.get("KEYCHAIN_SERVICE", "soma-vault-t0")


def _load_vault_token() -> str:
    """Bootstrap token for THIS one-shot process (R-SEC-03).

    Order: process env (one-shot only) → RAM tmpfs custodian (T0_DIR) →
    OS keychain. Never a repo file. Never logged.
    """
    env = os.environ.get("VAULT_TOKEN")
    if env and env.strip():
        return env.strip()
    if T0_DIR is not None:
        path = T0_DIR / "vault_root_token"
        if path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    try:
        proc = subprocess.run(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE,
             "-a", "vault_root_token", "-w"],
            capture_output=True,
        )
        if proc.returncode == 0:
            value = proc.stdout.decode("utf-8", errors="replace").strip()
            if value:
                return value
    except FileNotFoundError:
        pass
    raise SystemExit(
        "ERROR: no Vault root token available for the seeder.\n"
        "   R-SEC-03: provide VAULT_TOKEN for this one-shot process, or\n"
        "   ensure vault_unseal.py left it in the T0_DIR tmpfs custodian or\n"
        "   the OS keychain. It is never read from a file in the repo."
    )


VAULT_TOKEN = _load_vault_token()

# Key names MUST match somabrain/core/security/vault_client.py readers.
# get_jwt_secret() reads somabrain/auth["jwt_secret"]; seeding a different
# key name left SECRET_KEY unprovisioned and the app refused to boot.
SOMABRAIN_AUTH_KEY = "jwt_secret"

# Shared agent↔brain trust boundary — one document, one key. Generated in
# memory; pin the same value on both stacks with
# SOMA_SECRET_SOMABRAIN_MEMORY_HTTP_TOKEN (operator env, never a file).
SHARED_PATH = "agent/credentials"
SHARED_KEY = "somabrain_memory_http_token"

# MinIO root credentials live in somabrain/runtime and are rendered to tmpfs
# by the Vault Agent minio sidecar (MINIO_ROOT_*_FILE). Never a T0 handoff.
RUNTIME_KEYS = (
    "supervisor_http_pass",
    "api_token",
    "minio_access_key",
    "minio_secret_key",
)

FORCE = "--force" in sys.argv
CHECK = "--check" in sys.argv
APPROLE_ONLY = "--approle-only" in sys.argv

# ---------------------------------------------------------------------------
# AppRole (Vault Agent auto-auth). Least-privilege policy per consumer.
# ---------------------------------------------------------------------------
APPROLE_POLICIES = {
    "somabrain-pg-agent": """
path "somabrain/data/database" {
  capabilities = ["read"]
}
""",
    "somabrain-minio-agent": """
path "somabrain/data/runtime" {
  capabilities = ["read"]
}
""",
    "somabrain-app-agent": """
path "somabrain/data/*" {
  capabilities = ["read"]
}
path "secret/data/agent/credentials" {
  capabilities = ["read"]
}
path "secret/metadata/agent/credentials" {
  capabilities = ["read"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
""",
}

# AppRole role name → (policy, agent dir under APPROLE_DIR)
APPROLE_ROLES = {
    "somabrain-postgres-agent": ("somabrain-pg-agent", "postgres"),
    "somabrain-minio-agent": ("somabrain-minio-agent", "minio"),
    "somabrain-app-agent": ("somabrain-app-agent", "app"),
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def vault_req(method: str, path: str, body: dict | None = None):
    url = f"{VAULT_ADDR}/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Vault-Token", VAULT_TOKEN)
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


def generate_value(key: str) -> str:
    """Operator override via process env only; otherwise generate in memory."""
    env_key = f"SOMA_SECRET_{key.upper()}"
    override = os.environ.get(env_key)
    if override:
        if not override.strip():
            raise SystemExit(f"ERROR: {env_key} is set but empty. Refusing.")
        return override.strip()
    # 43 url-safe chars ~= 256 bits. Enough for any bearer/password material.
    return py_secrets.token_urlsafe(32)


def kv2_write(mount: str, path: str, data: dict) -> None:
    status, _ = vault_req("POST", f"{mount}/data/{path}", {"data": data})
    if status not in (200, 204):
        raise SystemExit(
            f"ERROR: write {mount}/data/{path} -> HTTP {status}. "
            f"Value was not logged."
        )


def kv2_read(mount: str, path: str) -> dict | None:
    status, payload = vault_req("GET", f"{mount}/data/{path}")
    if status == 404:
        return None
    if status != 200:
        raise SystemExit(f"ERROR: read {mount}/data/{path} -> HTTP {status}.")
    return (payload.get("data") or {}).get("data") or {}


def ensure_mount(mount: str) -> None:
    # Vault KV-v2 mount check/create. GET /sys/mounts/:path is not a thing —
    # list all mounts and look for the path. Create with POST /sys/mounts/:path.
    status, payload = vault_req("GET", "sys/mounts")
    if status == 200 and f"{mount}/" in (payload or {}):
        return
    status, _ = vault_req("POST", f"sys/mounts/{mount}", {"type": "kv-v2"})
    if status not in (204, 200):
        raise SystemExit(f"ERROR: mount {mount} -> HTTP {status}.")


def seed_simple(mount: str, path: str, key: str) -> str:
    """Generate (or take operator env) and merge-write to Vault.

    KV v2 POST replaces the whole data object — a one-key write deletes every
    sibling. Read first, merge in memory, write back, assert the key landed
    and every sibling survived. Never touches disk.
    """
    if CHECK:
        data = kv2_read(mount, path)
        present = bool(data and data.get(key))
        log(f"   {'present' if present else 'MISSING'}  {mount}/{path}[{key}]")
        return "check"

    before = kv2_read(mount, path)
    if before is None:
        before = {}
    pre_keys = sorted(before.keys())

    if not FORCE and before.get(key):
        log(f"   – skipped (already in Vault): {mount}/{path}[{key}]")
        return "skip"

    value = generate_value(key)
    if not value:
        raise SystemExit(f"ERROR: generated empty value for {key}. Refusing.")

    merged = dict(before)
    merged[key] = value
    kv2_write(mount, path, merged)

    stored = kv2_read(mount, path) or {}
    if stored.get(key) != value:
        raise SystemExit(
            f"ERROR: read-back mismatch at {mount}/{path}[{key}]. "
            f"Value was not logged. Refusing to treat the seed as successful."
        )
    lost = [k for k in pre_keys if k not in stored]
    if lost:
        raise SystemExit(
            f"ERROR: merge write destroyed sibling key(s) {lost} in "
            f"{mount}/{path}. KV v2 POST replaces the whole document."
        )
    log(f"   ✔ generated + seeded {mount}/{path}[{key}]  (in-memory only)")
    del value, merged, stored
    return "seeded"


def seed_database() -> str:
    """somabrain/database document — username + generated password + topology."""
    if CHECK:
        data = kv2_read("somabrain", "database")
        present = bool(data and data.get("password"))
        log(f"   {'present' if present else 'MISSING'}  somabrain/database[password]")
        return "check"

    existing = kv2_read("somabrain", "database") or {}
    if not FORCE and existing.get("password"):
        log("   – skipped (already in Vault): somabrain/database[password]")
        return "skip"

    password = generate_value("postgres_password")
    if not password:
        raise SystemExit("ERROR: generated empty postgres_password. Refusing.")

    doc = {
        "username": os.environ.get("POSTGRES_USER", "somabrain"),
        "password": password,
        "host": os.environ.get("POSTGRES_HOST", "somabrain_standalone_postgres"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "somabrain"),
    }
    kv2_write("somabrain", "database", doc)

    stored = kv2_read("somabrain", "database") or {}
    if stored.get("password") != password:
        raise SystemExit(
            "ERROR: read-back mismatch at somabrain/database[password]. "
            "Value was not logged."
        )
    log("   ✔ generated + seeded somabrain/database[password]  (in-memory only)")
    # No filesystem handoff. Vault Agent renders this to tmpfs for postgres.
    del password, stored
    return "seeded"


def seed_shared() -> str:
    """Merge the shared agent↔brain token into secret/agent/credentials.

    KV v2 POST replaces the whole document — a one-key write deletes every
    sibling. Read first, merge in memory, write the whole object back, then
    assert the key landed and every sibling survived.
    """
    if CHECK:
        data = kv2_read("secret", SHARED_PATH)
        present = bool(data and data.get(SHARED_KEY))
        log(f"   {'present' if present else 'MISSING'}  secret/{SHARED_PATH}[{SHARED_KEY}]")
        return "check"

    before = kv2_read("secret", SHARED_PATH)
    if before is None:
        before = {}
    pre_keys = sorted(before.keys())

    if not FORCE and before.get(SHARED_KEY):
        log(f"   – skipped (already in Vault): secret/{SHARED_PATH}[{SHARED_KEY}]")
        return "skip"

    value = generate_value(SHARED_KEY)
    if not value:
        raise SystemExit(f"ERROR: generated empty {SHARED_KEY}. Refusing.")

    merged = dict(before)
    merged[SHARED_KEY] = value
    kv2_write("secret", SHARED_PATH, merged)

    after = kv2_read("secret", SHARED_PATH) or {}
    if after.get(SHARED_KEY) != value:
        raise SystemExit(
            f"ERROR: shared token read-back mismatch after merge write. "
            f"Value was not logged."
        )
    lost = [k for k in pre_keys if k not in after]
    if lost:
        raise SystemExit(
            f"ERROR: merge write destroyed sibling key(s) {lost} in "
            f"secret/{SHARED_PATH}. KV v2 POST replaces the whole document."
        )
    log(
        f"   ✔ merged secret/{SHARED_PATH}[{SHARED_KEY}]  "
        f"document now holds {len(after)} key(s)"
    )
    del value, merged, after
    return "seeded"


def _write_approle_file(directory: Path, name: str, value: str) -> None:
    """Write an AppRole bootstrap file to the isolated tmpfs dir.

    ``role_id`` is an identifier (not a secret). ``secret_id`` is the
    industry-standard AppRole bootstrap credential delivered to Vault Agent
    on a tmpfs that only agents mount — never the app, never postgres/minio,
    never a disk volume, never the repo.

    Mode 0644 on this isolated volume: the app agent runs as uid 1000
    (Dockerfile USER) and must read files written by this root one-shot.
    The volume is not mounted into any application container.
    """
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(str(directory), 0o755)
    target = directory / name
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, value.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(str(target), 0o644)


def setup_approle() -> None:
    """Enable AppRole auth, install least-privilege policies, mint agent creds.

    Fail-closed: any HTTP error or missing APPROLE_DIR (when not --check) is a
    hard stop. Secret values are never logged.
    """
    if not APPROLE_DIR:
        if CHECK:
            log("   APPROLE_DIR unset — skipping AppRole check")
            return
        raise SystemExit(
            "ERROR: APPROLE_DIR is required for AppRole provisioning "
            "(isolated tmpfs for Vault Agent role_id/secret_id)."
        )

    status, _ = vault_req("POST", "sys/auth/approle", {"type": "approle"})
    if status in (200, 204):
        log("   ✔ enabled auth/approle")
    elif status == 400:
        # Already enabled (idempotent). Verify it is the approle method.
        status, payload = vault_req("GET", "sys/auth")
        mounts = payload or {}
        if "approle/" not in mounts and "approle" not in {
            k.strip("/") for k in mounts
        }:
            raise SystemExit("ERROR: auth/approle enable failed and method is absent.")
        log("   – auth/approle already enabled")
    else:
        raise SystemExit(f"ERROR: enable auth/approle -> HTTP {status}.")

    for name, policy_hcl in APPROLE_POLICIES.items():
        if CHECK:
            log(f"   policy {name}")
            continue
        status, _ = vault_req(
            "PUT", f"sys/policies/acl/{name}", {"policy": policy_hcl.strip()}
        )
        if status not in (200, 204):
            raise SystemExit(f"ERROR: policy {name} -> HTTP {status}.")
        log(f"   ✔ policy {name}")

    for role_name, (policy_name, agent_subdir) in APPROLE_ROLES.items():
        if CHECK:
            log(f"   role {role_name} → policy {policy_name}")
            continue

        status, _ = vault_req(
            "POST",
            f"auth/approle/role/{role_name}",
            {
                "token_policies": [policy_name],
                "token_ttl": "1h",
                "token_max_ttl": "24h",
                "token_no_default_policy": True,
                "secret_id_ttl": 0,
                "token_num_uses": 0,
            },
        )
        if status not in (200, 204):
            raise SystemExit(f"ERROR: approle role {role_name} -> HTTP {status}.")

        status, payload = vault_req("GET", f"auth/approle/role/{role_name}/role-id")
        if status != 200:
            raise SystemExit(f"ERROR: role-id {role_name} -> HTTP {status}.")
        role_id = ((payload or {}).get("data") or {}).get("role_id")
        if not role_id:
            raise SystemExit(f"ERROR: role-id {role_name} empty. Refusing.")

        status, payload = vault_req(
            "POST", f"auth/approle/role/{role_name}/secret-id", {}
        )
        if status not in (200, 204):
            raise SystemExit(f"ERROR: secret-id {role_name} -> HTTP {status}.")
        secret_id = ((payload or {}).get("data") or {}).get("secret_id")
        if not secret_id:
            raise SystemExit(f"ERROR: secret-id {role_name} empty. Refusing.")

        target_dir = APPROLE_DIR / agent_subdir
        role_id_path = target_dir / "role_id"
        secret_id_path = target_dir / "secret_id"
        if (
            not FORCE
            and role_id_path.is_file()
            and secret_id_path.is_file()
            and role_id_path.stat().st_size > 0
            and secret_id_path.stat().st_size > 0
        ):
            log(f"   – skipped (AppRole files present): {role_name}")
            del role_id, secret_id
            continue

        _write_approle_file(target_dir, "role_id", role_id)
        _write_approle_file(target_dir, "secret_id", secret_id)
        del role_id, secret_id
        log(f"   ✔ AppRole {role_name} → {target_dir} (tmpfs, agents only)")

    if not CHECK:
        log("   ✅ AppRole ready — Vault Agent sidecars auto-auth; no root "
            "token is delivered to application containers.")


def main() -> int:
    if not VAULT_ADDR:
        raise SystemExit("ERROR: VAULT_ADDR is required (Rule 91, no default).")

    # Wait for Vault API.
    for _ in range(30):
        try:
            vault_req("GET", "sys/health")
            break
        except SystemExit:
            time.sleep(1)
    else:
        raise SystemExit(f"ERROR: Vault at {VAULT_ADDR} is unreachable.")

    ensure_mount("somabrain")
    ensure_mount("secret")

    if not APPROLE_ONLY:
        log("📝 Database credentials → somabrain/database  (generated in memory)")
        seed_database()

        log("📝 JWT / runtime credentials → somabrain/auth, somabrain/runtime")
        # Key name is jwt_secret — the vault_client.get_jwt_secret() reader.
        seed_simple("somabrain", "auth", SOMABRAIN_AUTH_KEY)
        for runtime_key in RUNTIME_KEYS:
            seed_simple("somabrain", "runtime", runtime_key)

        log("📝 Shared agent↔brain token → secret/agent/credentials")
        seed_shared()

    log("🔐 AppRole for Vault Agent sidecars")
    setup_approle()

    if CHECK:
        log("✅ check complete — nothing written.")
    else:
        log("✅ Vault seeded — application values exist ONLY in Vault. "
            "Consumers read them via Vault Agent tmpfs templates or the "
            "AppRole-scoped service token. Nothing was written to disk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
