from __future__ import annotations
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from somabrain.constitution.storage import ConstitutionRecord, ConstitutionStorage
from common.logging import logger
from somabrain import audit as _audit
import base64
import hvac
from cryptography.hazmat.primitives.serialization import (
from cryptography.hazmat.primitives.serialization import (
import requests
import subprocess
import tempfile

"""Constitution engine package.

This package exposes the `ConstitutionEngine` and related helpers. The full
implementation was previously a top-level module; to support imports of the
form ``from somabrain.constitution import ConstitutionEngine`` we keep the
implementation here in the package __init__.

Keep the implementation deliberately self-contained and import-light so tests
and import-time checks remain stable.
"""





try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    # prefer existing project audit helper if available

    # publish_event returns bool; log_admin_action is kept for admin paths
    _PUBLISH_EVENT = getattr(_audit, "publish_event", None)
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise

LOGGER = logging.getLogger("somabrain.constitution")


class ConstitutionError(Exception):
    pass


def _decode_signature(sig: str) -> bytes:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return bytes.fromhex(sig)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        return base64.b64decode(sig)


class ConstitutionEngine:
    """Load and validate the AI‑Human Constitution.

    Responsibilities:
        pass
    - load JSON from Redis (key: SOMA_CONSTITUTION_KEY or default 'soma:constitution')
    - compute a stable SHA256 checksum string used for versioning
    - expose `validate(instance: dict) -> dict` that returns {'allowed': bool, 'explain': ...}
    """

def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
        storage: Optional[ConstitutionStorage] = None,
        db_url: Optional[str] = None, ):
            pass
        self._storage = storage or ConstitutionStorage(
            redis_url=redis_url,
            redis_client=redis_client,
            db_url=db_url, )
        self._constitution: Optional[Dict[str, Any]] = None
        self._checksum: Optional[str] = None
        self._signature: Optional[str] = None
        self._signatures: List[Dict[str, str]] = []
        self._metadata: Optional[Dict[str, Any]] = None
        self._pubkey_map = self._load_pubkey_map()
        self._key = self._storage._redis_key
        self._sig_key = self._storage._redis_sig_key

def _load_pubkey_map(self) -> Dict[str, str]:
        """
        Load public key map for signature verification.
        If Vault integration is enabled (VAULT_ADDR, VAULT_TOKEN, SOMABRAIN_VAULT_PUBKEY_PATH),
        fetch keys from Vault. Otherwise, use env/PATH as before.
        """
        mapping: Dict[str, str] = {}
        vault_addr = getattr(settings, "vault_addr", None)
        vault_token = getattr(settings, "vault_token", None)
        vault_path = getattr(settings, "vault_pubkey_path", None)
        if vault_addr and vault_token and vault_path:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise

                client = hvac.Client(url=vault_addr, token=vault_token)
                secret = client.secrets.kv.v2.read_secret_version(path=vault_path)
                data = secret["data"]["data"]
                # Expecting {"signer_id": "PEM_CONTENT"}
                for k, v in data.items():
                    mapping[str(k)] = v
                LOGGER.info("Loaded public keys from Vault path %s", vault_path)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
        # Use env/PATH
        if not mapping:
            env_value = getattr(settings, "constitution_pubkeys", None)
            single = getattr(settings, "constitution_pubkey_path", None)
            if env_value:
                try:
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    data = json.loads(env_value)
                    if isinstance(data, dict):
                        mapping = {str(k): str(v) for k, v in data.items()}
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    parts = [p for p in env_value.split(",") if ":" in p]
                    for part in parts:
                        signer, path = part.split(":", 1)
                        mapping[signer.strip()] = path.strip()
            if single and "default" not in mapping:
                mapping["default"] = single
        return mapping

def load(self) -> Dict[str, Any]:
        """Load the constitution JSON from Redis. Raises ConstitutionError on failure.

        If Redis is unavailable, raises ConstitutionError to avoid silently using an empty constitution.
        """
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            record = self._storage.load_active()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise ConstitutionError(str(exc))
        self._apply_record(record)
        LOGGER.info("Loaded constitution version %s", self._checksum[:8])
        return self._constitution  # type: ignore[return-value]

def save(self, constitution: Dict[str, Any]) -> None:
        """Save a constitution dict to Redis and update internal state.

        This writes the JSON representation to the configured Redis key, recomputes the
        checksum, stores it in ``self._checksum`` and updates ``self._constitution``.
        If a signature key is configured and a signature already exists, the signature
        is preserved (the caller can invoke ``self.sign`` afterwards if a new signature
        is required).
        """
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            checksum = self._storage.save_new(constitution)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise ConstitutionError(f"Failed to persist constitution: {exc}")
        self._constitution = constitution
        self._checksum = checksum
        self._signatures = []
        self._signature = None
        self._metadata = None
        self._storage.snapshot(constitution, checksum, metadata=self._metadata)
        LOGGER.info("Saved constitution version %s", self._checksum[:8])

def get_checksum(self) -> Optional[str]:
        return self._checksum

def get_signature(self) -> Optional[str]:
        """Return the optional signature associated with the loaded constitution (if any)."""
        return self._signature

def get_signatures(self) -> List[Dict[str, str]]:
        return list(self._signatures)

def verify_signature(self, pubkey_path: Optional[str] = None) -> bool:
        """Attempt to verify the stored signature using a PEM public key at `pubkey_path`,
        or a PEM string from Vault if configured.
        """
        if not self._checksum:
            return False
        signatures = self._signatures or self._storage.get_signatures(self._checksum)
        if not signatures:
            signature = self._signature
            if signature:
                signatures = [{"signer_id": "default", "signature": signature}]
        if not signatures:
            return False

        if pubkey_path:
            key_map = {"default": pubkey_path}
        else:
            key_map = self._pubkey_map
        if not key_map:
            LOGGER.debug("No public keys configured for constitution verification")
            return False

        required = int(getattr(settings, "constitution_threshold", 1))
        valid = 0
        errors: List[str] = []
        for sig in signatures:
            signer_id = sig.get("signer_id") or "default"
            signature = sig.get("signature")
            key_val = key_map.get(signer_id) or key_map.get("default")
            if not key_val or not signature:
                errors.append(f"missing key/signature for signer {signer_id}")
                continue
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                    load_pem_public_key, )

                if key_val.startswith("-----BEGIN "):
                    # PEM string (from Vault or env)
                    pub = load_pem_public_key(key_val.encode("utf-8"))
                else:
                    # Assume file path
                    with open(key_val, "rb") as fh:
                        pub = load_pem_public_key(fh.read())
                sig_bytes = _decode_signature(signature)
                pub.verify(sig_bytes, self._checksum.encode("utf-8"))
                valid += 1
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
        if valid < required:
            LOGGER.debug(
                "Constitution signature threshold not met: %s valid/%s required (%s)",
                valid,
                required,
                "; ".join(errors), )
            return False
        self._signatures = signatures
        self._signature = signatures[0]["signature"] if signatures else None
        return True

def sign(self, private_key_path: Optional[str] = None) -> Optional[str]:
        """Sign the current constitution checksum using a PEM private key and store the signature.

        Returns the signature encoded as hex string, or None on failure.
        """
        priv_path = private_key_path or settings.constitution_privkey_path
        if not priv_path:
            LOGGER.debug("No private key path configured for constitution signing")
            return None
        if not self._checksum:
            LOGGER.debug("No checksum available to sign")
            return None
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
                load_pem_private_key, )

            with open(priv_path, "rb") as f:
                priv = load_pem_private_key(f.read(), password=None)

            sig_bytes = priv.sign(self._checksum.encode("utf-8"))
            hexsig = sig_bytes.hex()
            signer_id = getattr(settings, "constitution_signer_id", "default")
            self._signature = hexsig
            self._signatures = [
                {
                    "signer_id": signer_id,
                    "signature": hexsig,
                    "checksum": self._checksum,
                }
            ]
            self._storage.record_signature(self._checksum, signer_id, hexsig)
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                client = self._storage._connect_redis()  # type: ignore[attr-defined]
                if client is not None:
                    client.set(self._sig_key, hexsig)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
            return hexsig
        except Exception as e:
            logger.exception("Exception caught: %s", e)
            raise

def get_constitution(self) -> Optional[Dict[str, Any]]:
        return self._constitution

def validate(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an instance against the constitution.

        If an OPA endpoint is configured via SOMA_OPA_URL, the engine will proxy the validation
        to OPA (`/v1/data/soma/policy/allow`). If OPA is not configured or unreachable, fall
        back to a conservative local check that ensures required top-level keys exist.
        """
        opa_url = getattr(settings, "opa_url", None)
        # Conservative local check
        required = ["version", "rules"]
        if opa_url:
            # try proxying to OPA; do not raise on network errors — return conservative deny
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise

                resp = requests.post(
                    f"{opa_url.rstrip('/')}/v1/data/soma/policy/allow",
                    json={
                        "input": {
                            "constitution": self._constitution,
                            "instance": instance,
                        }
                    },
                    timeout=2, )
                if resp.status_code == 200:
                    body = resp.json()
                    # expected shape: {"result": {"allow": true, "explain": ...}}
                    res = body.get("result") or {}
                    result = {"allowed": bool(res.get("allow")), "explain": res}
                    # emit audit event (best-effort)
                    try:
                        pass
                    except Exception as exc:
                        logger.exception("Exception caught: %s", exc)
                        raise
                        if _PUBLISH_EVENT:
                            evt = {
                                "type": "constitution.validation",
                                "timestamp": time.time(),
                                "decision": bool(res.get("allow")),
                                "explain": res,
                            }
                            # include canonical fields used by audit schema
                            evt["constitution_sha"] = self._checksum
                            if self._signature:
                                evt["constitution_sig"] = self._signature
                            _PUBLISH_EVENT(evt)
                    except Exception as exc:
                        logger.exception("Exception caught: %s", exc)
                        raise
                        LOGGER.debug("audit publish failed for OPA result")
                    return result
                else:
                    LOGGER.debug("OPA returned %s", resp.status_code)
            except Exception as e:
                logger.exception("Exception caught: %s", e)
                raise

        # If HTTP OPA not available, optionally try local opa binary with a bundle
        opa_bundle = getattr(settings, "opa_bundle_path", None)
        if opa_bundle:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise

                # opa eval --format=json --data bundle.tar.gz 'data.soma.policy.allow' --input input.json
                # build a temp input file

                with tempfile.NamedTemporaryFile("w+", delete=False) as t:
                    json.dump(
                        {"constitution": self._constitution, "instance": instance}, t
                    )
                    t.flush()
                    cmd = [
                        "opa",
                        "eval",
                        "--format=json",
                        "--data",
                        opa_bundle,
                        "data.soma.policy.allow",
                        "--input",
                        t.name,
                    ]
                    proc = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=5
                    )
                if proc.returncode == 0:
                    body = json.loads(proc.stdout)
                    # parse expected result shape
                    res = (
                        (body.get("result") or [{}])[0]
                        .get("expressions", [{}])[0]
                        .get("value")
                    )
                    if isinstance(res, dict):
                        result = {"allowed": bool(res.get("allow")), "explain": res}
                    else:
                        # expression returned primitive; treat truthy as allow
                        result = {"allowed": bool(res), "explain": res}
                    try:
                        pass
                    except Exception as exc:
                        logger.exception("Exception caught: %s", exc)
                        raise
                        if _PUBLISH_EVENT:
                            evt = {
                                "type": "constitution.validation",
                                "timestamp": time.time(),
                                "decision": bool(result.get("allowed")),
                                "explain": result.get("explain"),
                            }
                            evt["constitution_sha"] = self._checksum
                            if self._signature:
                                evt["constitution_sig"] = self._signature
                            if self._signatures:
                                evt["constitution_sig_set"] = self._signatures
                            _PUBLISH_EVENT(evt)
                    except Exception as exc:
                        logger.exception("Exception caught: %s", exc)
                        raise
                        LOGGER.debug("audit publish failed for opa bundle result")
                    return result
            except Exception as e:
                logger.exception("Exception caught: %s", e)
                raise

        # Alternative local validation
        if not self._constitution:
            result = {"allowed": False, "explain": "constitution not loaded"}
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                if _PUBLISH_EVENT:
                    evt = {
                        "type": "constitution.validation",
                        "timestamp": time.time(),
                        "decision": False,
                        "explain": result["explain"],
                    }
                    evt["constitution_sha"] = self._checksum
                    if self._signature:
                        evt["constitution_sig"] = self._signature
                    _PUBLISH_EVENT(evt)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                LOGGER.debug("audit publish failed for missing constitution")
            return result

        missing = [k for k in required if k not in self._constitution]
        if missing:
            result = {
                "allowed": False,
                "explain": f"constitution missing keys: {missing}",
            }
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                if _PUBLISH_EVENT:
                    evt = {
                        "type": "constitution.validation",
                        "timestamp": time.time(),
                        "decision": False,
                        "explain": result["explain"],
                    }
                    evt["constitution_sha"] = self._checksum
                    if self._signature:
                        evt["constitution_sig"] = self._signature
                    _PUBLISH_EVENT(evt)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                LOGGER.debug("audit publish failed for missing keys")
            return result

        # Basic rule enforcement: if instance has 'forbidden' flag true and constitution disallows it
        rules = self._constitution.get("rules", {})
        if (
            instance.get("forbidden")
            and rules.get("allow_forbidden", False) is not True
        ):
            result = {
                "allowed": False,
                "explain": "instance marked forbidden by constitution",
            }
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                if _PUBLISH_EVENT:
                    evt = {
                        "type": "constitution.validation",
                        "timestamp": time.time(),
                        "decision": False,
                        "explain": result["explain"],
                    }
                    evt["constitution_sha"] = self._checksum
                    if self._signature:
                        evt["constitution_sig"] = self._signature
                    _PUBLISH_EVENT(evt)
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                LOGGER.debug("audit publish failed for forbidden instance")
            return result

        result = {"allowed": True, "explain": "local-pass"}
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            if _PUBLISH_EVENT:
                evt = {
                    "type": "constitution.validation",
                    "timestamp": time.time(),
                    "decision": True,
                    "explain": result["explain"],
                }
                evt["constitution_sha"] = self._checksum
                if self._signature:
                    evt["constitution_sig"] = self._signature
                if self._signatures:
                    evt["constitution_sig_set"] = self._signatures
                _PUBLISH_EVENT(evt)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            LOGGER.debug("audit publish failed for allow decision")
        return result

    # ------------------------------------------------------------------
def _apply_record(self, record: ConstitutionRecord) -> None:
        self._constitution = record.document
        self._checksum = record.checksum
        self._metadata = record.metadata
        self._signatures = record.signatures or []
        if self._signatures:
            self._signature = self._signatures[0].get("signature")
        else:
            client = self._storage._connect_redis()  # type: ignore[attr-defined]
            if client is not None:
                try:
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    try:
                        pass
                    except Exception as exc:
                        logger.exception("Exception caught: %s", exc)
                        raise
        if self._signatures and self._constitution:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                self._storage._write_redis(
                    self._constitution, self._checksum, self._signatures
                )  # type: ignore[attr-defined]
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
    raise


__all__ = ["ConstitutionEngine", "ConstitutionError"]
