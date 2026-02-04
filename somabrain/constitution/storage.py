"""Redis + Postgres backed constitution storage helpers - Django ORM version.

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import logging
import pathlib
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import transaction

from somabrain.admin.core.models import ConstitutionSignature, ConstitutionVersion

try:  # pragma: no cover - redis is optional during unit tests
    import redis
except Exception:  # pragma: no cover
    redis = None

LOGGER = logging.getLogger("somabrain.constitution.storage")


@dataclasses.dataclass(slots=True)
class ConstitutionRecord:
    """Constitutionrecord class implementation."""

    document: Dict[str, Any]
    checksum: str
    created_at: dt.datetime
    metadata: Optional[Dict[str, Any]] = None
    signatures: Optional[List[Dict[str, str]]] = None


class ConstitutionStorageError(RuntimeError):
    """Raised when the constitution store cannot fulfil a request."""


class ConstitutionStorage:
    """Persist constitutions to Redis (hot) and Postgres (historical)."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
        redis_key: str = "soma:constitution",
        redis_sig_key: str = "soma:constitution:signatures",
        db_url: Optional[str] = None,  # Ignored, Django uses settings.DATABASES
    ) -> None:
        """Initialize the instance."""

        self._redis_client = redis_client
        self._redis_url = redis_url or settings.SOMABRAIN_REDIS_URL
        self._redis_key = redis_key
        self._redis_sig_key = redis_sig_key
        self._redis_checksum_key = f"{redis_key}:checksum"
        self._redis_meta_key = f"{redis_key}:meta"
        self._db_url = db_url  # Not used with Django

    # ------------------------------------------------------------------
    @transaction.atomic
    def save_new(
        self, document: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute save new.

        Args:
            document: The document.
            metadata: The metadata.
        """

        checksum = self._compute_checksum(document)
        metadata = metadata or {}
        now = dt.datetime.now(dt.timezone.utc)

        # Deactivate all existing versions
        ConstitutionVersion.objects.update(is_active=False)

        # Create or update version
        version, created = ConstitutionVersion.objects.update_or_create(
            checksum=checksum,
            defaults={
                "document": document,
                "metadata": metadata,
                "is_active": True,
                "created_at": now,
            },
        )

        self._write_redis(document, checksum, signatures=[])
        self._write_redis_metadata(metadata, now)
        return checksum

    def load_active(self) -> ConstitutionRecord:
        """Execute load active."""

        try:
            # Try to get active version
            version = (
                ConstitutionVersion.objects.filter(is_active=True)
                .order_by("-created_at")
                .first()
            )

            if version is None:
                # Fall back to latest version
                version = ConstitutionVersion.objects.order_by("-created_at").first()

            if version is not None:
                signatures = self.get_signatures(version.checksum)
                return ConstitutionRecord(
                    document=version.document or {},
                    checksum=version.checksum,
                    metadata=version.metadata or {},
                    created_at=self._ensure_datetime(version.created_at),
                    signatures=signatures or None,
                )
        except Exception as exc:
            LOGGER.debug("DB load failed, falling back to Redis: %s", exc)

        record = self._load_from_redis()
        if record is not None:
            return record
        raise ConstitutionStorageError("No constitution document available")

    @transaction.atomic
    def record_signature(self, checksum: str, signer_id: str, signature: str) -> None:
        """Execute record signature.

        Args:
            checksum: The checksum.
            signer_id: The signer_id.
            signature: The signature.
        """

        now = dt.datetime.now(dt.timezone.utc)
        sig_id = f"{checksum}:{signer_id}"

        try:
            ConstitutionSignature.objects.update_or_create(
                id=sig_id,
                defaults={
                    "checksum": checksum,
                    "signer_id": signer_id,
                    "signature": signature,
                    "created_at": now,
                },
            )
        except Exception as exc:
            LOGGER.warning("Failed to persist constitution signature: %s", exc)

        self._sync_redis_signatures(checksum)

    def get_signatures(self, checksum: str) -> List[Dict[str, str]]:
        """Retrieve signatures.

        Args:
            checksum: The checksum.
        """

        try:
            rows = ConstitutionSignature.objects.filter(checksum=checksum).order_by(
                "created_at"
            )

            results = [
                {
                    "signer_id": row.signer_id,
                    "signature": row.signature,
                    "checksum": row.checksum,
                    "created_at": self._ensure_datetime(row.created_at).isoformat(),
                }
                for row in rows
            ]
            if results:
                return results
        except Exception:
            pass

        # Fall back to Redis cache
        client = self._connect_redis()
        if client is None:
            return []
        raw = client.get(self._redis_sig_key)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except Exception:
            LOGGER.debug("Unable to decode redis signature cache")
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []

    def snapshot(
        self,
        document: Dict[str, Any],
        checksum: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Write a constitution snapshot to local dir (if set) and/or S3 (if configured).
        Returns the local file path or S3 URI, whichever is used/preferred.
        """
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "checksum": checksum,
            "document": document,
            "metadata": metadata or {},
            "created_at": timestamp,
        }
        # Local snapshot
        local_path = None
        target = getattr(settings, "CONSTITUTION_SNAPSHOT_DIR", None)
        if target:
            path = pathlib.Path(target)
            path.mkdir(parents=True, exist_ok=True)
            outfile = path / f"constitution_{timestamp}_{checksum[:12]}.json"
            outfile.write_text(json.dumps(payload, indent=2, sort_keys=True))
            LOGGER.info("wrote constitution snapshot to %s", outfile)
            local_path = str(outfile)
        # S3 snapshot
        s3_bucket = getattr(settings, "CONSTITUTION_S3_BUCKET", None)
        s3_uri = None
        if s3_bucket:
            try:
                import boto3

                s3 = boto3.client("s3")
                s3_key = f"constitution/constitution_{timestamp}_{checksum[:12]}.json"
                s3.put_object(
                    Bucket=s3_bucket,
                    Key=s3_key,
                    Body=json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"),
                    ContentType="application/json",
                )
                s3_uri = f"s3://{s3_bucket}/{s3_key}"
                LOGGER.info("uploaded constitution snapshot to %s", s3_uri)
            except Exception as exc:
                LOGGER.warning("S3 snapshot upload failed: %s", exc)
        return s3_uri or local_path

    # ------------------------------------------------------------------
    def _connect_redis(self):
        """Execute connect redis."""

        if self._redis_client is not None:
            return self._redis_client
        if not self._redis_url or redis is None:
            return None
        try:
            self._redis_client = redis.from_url(self._redis_url)
        except Exception as exc:
            LOGGER.debug("Redis connection failed: %s", exc)
            self._redis_client = None
        return self._redis_client

    def _write_redis(
        self,
        document: Dict[str, Any],
        checksum: str,
        signatures: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """Execute write redis.

        Args:
            document: The document.
            checksum: The checksum.
            signatures: The signatures.
        """

        client = self._connect_redis()
        if client is None:
            return
        payload = json.dumps(document, sort_keys=True)
        try:
            client.set(self._redis_key, payload)
            client.set(self._redis_checksum_key, checksum)
            if signatures is not None:
                client.set(self._redis_sig_key, json.dumps(signatures))
        except Exception as exc:
            LOGGER.debug("Failed to write constitution cache to redis: %s", exc)

    def _write_redis_metadata(
        self, metadata: Dict[str, Any], created_at: dt.datetime
    ) -> None:
        """Execute write redis metadata.

        Args:
            metadata: The metadata.
            created_at: The created_at.
        """

        client = self._connect_redis()
        if client is None:
            return
        try:
            client.set(
                self._redis_meta_key,
                json.dumps(
                    {"metadata": metadata, "created_at": created_at.isoformat()}
                ),
            )
        except Exception as exc:
            LOGGER.debug("Failed to write constitution metadata to redis: %s", exc)

    def _load_from_redis(self) -> Optional[ConstitutionRecord]:
        """Execute load from redis."""

        client = self._connect_redis()
        if client is None:
            return None
        try:
            raw_doc = client.get(self._redis_key)
            if not raw_doc:
                return None
            document = json.loads(raw_doc)
        except Exception as exc:
            LOGGER.debug("Redis constitution payload invalid: %s", exc)
            return None
        checksum_raw = client.get(self._redis_checksum_key)
        checksum = (
            checksum_raw.decode("utf-8")
            if checksum_raw
            else self._compute_checksum(document)
        )
        raw_meta = client.get(self._redis_meta_key)
        metadata: Optional[Dict[str, Any]] = None
        created_at = dt.datetime.now(dt.timezone.utc)
        if raw_meta:
            try:
                meta_payload = json.loads(raw_meta)
                metadata = meta_payload.get("metadata")
                ts = meta_payload.get("created_at")
                if ts:
                    created_at = self._ensure_datetime(ts)
            except Exception:
                LOGGER.debug("Unable to parse redis constitution metadata")
        signatures = self.get_signatures(checksum)
        return ConstitutionRecord(
            document=document,
            checksum=checksum,
            metadata=metadata,
            created_at=created_at,
            signatures=signatures or None,
        )

    def _sync_redis_signatures(self, checksum: str) -> None:
        """Execute sync redis signatures.

        Args:
            checksum: The checksum.
        """

        client = self._connect_redis()
        if client is None:
            return
        signatures = self.get_signatures(checksum)
        if not signatures:
            return
        try:
            client.set(self._redis_sig_key, json.dumps(signatures))
        except Exception as exc:
            LOGGER.debug("Failed to sync signatures to redis: %s", exc)

    @staticmethod
    def _compute_checksum(document: Dict[str, Any]) -> str:
        """Execute compute checksum.

        Args:
            document: The document.
        """

        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha3_512(payload).hexdigest()

    @staticmethod
    def _ensure_datetime(value: Any) -> dt.datetime:
        """Execute ensure datetime.

        Args:
            value: The value.
        """

        if isinstance(value, dt.datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=dt.timezone.utc)
            return value.astimezone(dt.timezone.utc)
        if isinstance(value, str):
            try:
                parsed = dt.datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                return parsed.astimezone(dt.timezone.utc)
            except ValueError:
                pass
        return dt.datetime.now(dt.timezone.utc)


__all__ = ["ConstitutionStorage", "ConstitutionRecord", "ConstitutionStorageError"]
