#!/usr/bin/env python3
"""SomaBrain Vault seeder — generate-in-memory → Vault only.

R-SEC-01 / Covenant Art 26 / Rule 164. Secrets never touch argv, shell vars,
or the filesystem. Idempotent: skip-if-present unless --force.
"""
from __future__ import annotations
import json, os, secrets as py_secrets, sys, time, urllib.error, urllib.request

VAULT_ADDR = (os.environ.get("SOMABRAIN_VAULT_ADDR") or os.environ.get("VAULT_ADDR") or "").rstrip("/")
T0_DIR = os.environ.get("T0_DIR")
FORCE = "--force" in sys.argv

def log(m): print(m, file=sys.stderr, flush=True)

def load_token() -> str:
    env = os.environ.get("VAULT_TOKEN")
    if env and env.strip():
        return env.strip()
    if T0_DIR:
        p = os.path.join(T0_DIR, "vault_root_token")
        if os.path.isfile(p):
            v = open(p).read().strip()
            if v: return v
    raise SystemExit("ERROR: no Vault token (R-SEC-03 one-shot env or T0_DIR custodian)")

VAULT_TOKEN = load_token()

def vault(method, path, body=None):
    url = f"{VAULT_ADDR}/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Vault-Token", VAULT_TOKEN)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw) if raw else {}
        except Exception: return e.code, {}
    except Exception as e:
        raise SystemExit(f"ERROR: {method} {path} -> {type(e).__name__}")

def kv_write(mount, path, data):
    st, _ = vault("POST", f"{mount}/data/{path}", {"data": data})
    if st not in (200, 204):
        raise SystemExit(f"ERROR: write {mount}/{path} HTTP {st}")

def kv_read(mount, path):
    st, payload = vault("GET", f"{mount}/data/{path}")
    if st == 404: return {}
    if st != 200: raise SystemExit(f"ERROR: read {mount}/{path} HTTP {st}")
    return (payload.get("data") or {}).get("data") or {}

def gen(key):
    o = os.environ.get(f"SOMA_SECRET_{key.upper()}")
    if o and o.strip(): return o.strip()
    return py_secrets.token_urlsafe(32)

def seed(mount, path, key, value=None, required=True):
    existing = kv_read(mount, path)
    if existing.get(key) and not FORCE:
        log(f"   – skipped (in Vault): {mount}/{path}[{key}]")
        return
    v = value if value is not None else gen(key)
    if not v:
        if required: raise SystemExit(f"ERROR: empty {key}")
        return
    kv_write(mount, path, {key: v})
    back = kv_read(mount, path).get(key)
    if back != v:
        raise SystemExit(f"ERROR: read-back mismatch {path}[{key}]")
    log(f"   ✔ seeded {mount}/{path}[{key}] (memory→Vault only)")

def main():
    if not VAULT_ADDR: raise SystemExit("ERROR: VAULT_ADDR required")
    for _ in range(30):
        try:
            vault("GET", "sys/health"); break
        except SystemExit: time.sleep(1)
    # Ensure mounts
    for m in ("somabrain", "secret"):
        vault("POST", "sys/mounts/" + m, {"type": "kv-v2"})
    # Shared memory token from T0 if present (else generate)
    shared = None
    if T0_DIR:
        p = os.path.join(T0_DIR, "somabrain_memory_http_token")
        if os.path.isfile(p):
            shared = open(p).read().strip()
    seed("somabrain", "database", "password")
    seed("somabrain", "database", "username", value=os.environ.get("POSTGRES_USER", "somabrain"))
    seed("somabrain", "auth", "jwt_secret")
    seed("somabrain", "runtime", "supervisor_http_pass")
    seed("somabrain", "runtime", "api_token")
    seed("secret", "agent/credentials", "somabrain_memory_http_token", value=shared, required=False)
    log("✅ SomaBrain Vault seeded — values ONLY in Vault.")
    print("SEED_OK=1", flush=True)

if __name__ == "__main__":
    main()
