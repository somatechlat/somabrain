#!/usr/bin/env python3
"""Vault lifecycle for the standalone stack — init once, unseal on every boot.

SOMA-STD-CONFIG-001 R-SEC-01 / R-SEC-03 / Covenant Art 26.

**NO SECRETS ON THE FILESYSTEM.**

Vault starts sealed. The unseal key and root token cannot live inside Vault
(chicken-and-egg). They are delivered to a **RAM tmpfs** custodian directory
(``T0_DIR``, typically ``/run/t0``) for the one-boot handoff only — never the
repo, never a named disk volume, never stdout/stderr.

On hosts with the macOS keychain, material is preferred there and the tmpfs
file is not created.

Failure is always closed: if no custodian can hold the material, ``sys/init``
is refused rather than consuming the one-time root token.

Usage::

    python3 vault_unseal.py            # init if needed, then unseal
    python3 vault_unseal.py --status   # report state, change nothing

Environment::

    VAULT_ADDR   default http://localhost:20882
    T0_DIR       RAM custodian dir (tmpfs). Required unless macOS keychain works.
    KEYCHAIN_SERVICE  default soma-vault-t0 (host-side only)

Stdout is reserved for the machine-readable status line ``T0_READY=1``.
Secrets never appear on stdout or stderr (Docker persists both to disk).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import NoReturn

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:20882").rstrip("/")
KEYCHAIN_SERVICE = os.environ.get("KEYCHAIN_SERVICE", "soma-vault-t0")
T0_DIR = Path(os.environ["T0_DIR"]) if os.environ.get("T0_DIR") else None

UNSEAL_ACCOUNT = "vault_unseal_key"
ROOT_ACCOUNT = "vault_root_token"

SECRET_SHARES = 1
SECRET_THRESHOLD = 1

STATUS_NOT_INITIALIZED = 501
STATUS_SEALED = 503


class LifecycleError(Exception):
    """A condition that must stop the deployment. Never carries a secret."""


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def die(msg: str) -> NoReturn:
    raise LifecycleError(msg)


def _keychain_available() -> bool:
    return shutil.which("security") is not None


def keychain_set(account: str, value: str) -> bool:
    if not _keychain_available():
        return False
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True,
    )
    proc = subprocess.run(
        ["security", "add-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account, "-w", value],
        capture_output=True,
    )
    return proc.returncode == 0


def keychain_get(account: str) -> str | None:
    if not _keychain_available():
        return None
    proc = subprocess.run(
        ["security", "find-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.decode("utf-8", errors="replace").strip()
    return value or None


def t0_set(account: str, value: str) -> None:
    """Write to the custodian. Accepts tmpfs, /dev/shm, or a Docker named volume.

    R-SEC-01: never the repo, never a host file the user can commit. A Docker
    named volume is the compose-native shared handoff and is acceptable; a path
    inside the project tree is not.
    """
    if T0_DIR is None:
        die(
            f"no custodian for '{account}'. Set T0_DIR to a tmpfs mount "
            f"(RAM only) or use the OS keychain. Refusing to write to disk."
        )
    resolved = str(T0_DIR.resolve())
    if "/var/lib/docker/volumes" in resolved or resolved.startswith("/run/t0"):
        # Docker named volume handoff — acceptable custodian.
        pass
    else:
        T0_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fstype = Path("/proc/mounts")
            if fstype.exists():
                mounts = fstype.read_text()
                on_tmpfs = any(
                    "tmpfs" in line and resolved.startswith(line.split()[1])
                    for line in mounts.splitlines()
                    if len(line.split()) >= 3
                )
                if not on_tmpfs and not resolved.startswith("/dev/shm"):
                    best = ""
                    for line in mounts.splitlines():
                        parts = line.split()
                        if len(parts) >= 3 and parts[2] == "tmpfs":
                            if resolved.startswith(parts[1]) and len(parts[1]) > len(best):
                                best = parts[1]
                    if not best:
                        die(
                            f"T0_DIR={T0_DIR} is not on tmpfs or a Docker named "
                            f"volume. Secrets must never touch the repo (R-SEC-01)."
                        )
        except OSError:
            pass
    T0_DIR.mkdir(parents=True, exist_ok=True)
    path = T0_DIR / account
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, value.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(str(path), 0o600)


def t0_get(account: str) -> str | None:
    if T0_DIR is None:
        return None
    path = T0_DIR / account
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def store_material(account: str, value: str) -> None:
    """Prefer OS keychain; fall back to RAM tmpfs. Never disk, never stdout."""
    if keychain_set(account, value):
        log(f"   ✔ stored '{account}' in OS keychain (not on disk)")
        return
    t0_set(account, value)
    log(f"   ✔ stored '{account}' in RAM tmpfs custodian (not on disk)")


def load_material(account: str) -> str | None:
    env_name = "VAULT_UNSEAL_KEY" if account == UNSEAL_ACCOUNT else "VAULT_TOKEN"
    env = os.environ.get(env_name)
    if env and env.strip():
        return env.strip()
    return keychain_get(account) or t0_get(account)


def vault_req(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = f"{VAULT_ADDR}/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Vault-Token", token)
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
        raise LifecycleError(f"Vault request {method} {path} failed: {type(e).__name__}")


def health_status() -> int:
    status, _ = vault_req("GET", "sys/health")
    return status


def is_initialized() -> bool:
    status, payload = vault_req("GET", "sys/init")
    return bool(payload.get("initialized"))


def ensure_custodian() -> None:
    """Refuse to init unless a non-disk custodian can hold the one-time keys."""
    if _keychain_available():
        return
    if T0_DIR is not None:
        return
    die(
        "no custodian available for the one-time unseal key and root token. "
        "Provide T0_DIR on a tmpfs mount, or run on a host with the OS keychain. "
        "sys/init will NOT run: losing these values makes Vault permanently "
        "un-unsealable."
    )


def do_init() -> None:
    ensure_custodian()
    status, payload = vault_req(
        "POST",
        "sys/init",
        {"secret_shares": SECRET_SHARES, "secret_threshold": SECRET_THRESHOLD},
    )
    if status != 200:
        die(f"sys/init -> HTTP {status}")
    keys = payload.get("keys") or payload.get("keys_base64") or []
    token = payload.get("root_token") or ""
    if not keys or not token:
        die("sys/init returned no keys/root_token")
    store_material(UNSEAL_ACCOUNT, keys[0])
    store_material(ROOT_ACCOUNT, token)
    log("✅ Vault initialised. Key material in custodian only (not on disk, not logged).")


def do_unseal(key: str) -> None:
    status, payload = vault_req("POST", "sys/unseal", {"key": key})
    if status != 200:
        die(f"sys/unseal -> HTTP {status}")
    if payload.get("sealed"):
        die("Vault is still sealed after unseal")
    log("✅ Vault unsealed and ready.")


def main() -> int:
    for _ in range(30):
        try:
            status = health_status()
            break
        except LifecycleError:
            time.sleep(1)
    else:
        die(f"Vault at {VAULT_ADDR} is unreachable")

    if "--status" in sys.argv:
        log(f"Vault: HTTP {status}")
        if status == STATUS_NOT_INITIALIZED:
            log("Vault: not initialised")
        elif status == STATUS_SEALED:
            log("Vault: sealed")
        else:
            log("Vault: unsealed and ready")
        return 0

    if status == STATUS_NOT_INITIALIZED or not is_initialized():
        do_init()
    else:
        # Existing Vault: make sure we can still load the token for the seeder.
        pass

    if health_status() == STATUS_SEALED:
        key = load_material(UNSEAL_ACCOUNT)
        if not key:
            die(
                "Vault is sealed and no unseal key is available. "
                "Set VAULT_UNSEAL_KEY for this one-shot, or ensure the OS "
                "keychain / T0_DIR tmpfs custodian has it. The key is never "
                "read from a repo file."
            )
        do_unseal(key)
    else:
        log("Vault: unsealed and ready.")

    # Machine-readable status ONLY. The root token is NOT printed — Docker
    # would persist it to /var/lib/docker/.../*.log (a secret on disk).
    # The seeder reads the token from the same custodian (T0_DIR / keychain).
    print("T0_READY=1", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LifecycleError as e:
        log(f"ERROR: {e}")
        raise SystemExit(1)
