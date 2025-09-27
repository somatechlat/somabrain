"""Redis + Postgres backed constitution storage helpers."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import logging
import os
import pathlib
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    JSON,
    String,
    UniqueConstraint,
    func,
    select,
    update,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from somabrain.storage import db as storage_db

try:  # pragma: no cover - redis is optional during unit tests
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore[assignment]

LOGGER = logging.getLogger("somabrain.constitution.storage")


@dataclasses.dataclass(slots=True)
class ConstitutionRecord:
    document: Dict[str, Any]
    checksum: str
    created_at: dt.datetime
    metadata: Optional[Dict[str, Any]] = None
    signatures: Optional[List[Dict[str, str]]] = None


class ConstitutionStorageError(RuntimeError):
    """Raised when the constitution store cannot fulfil a request."""


class ConstitutionVersion(storage_db.Base):
    __tablename__ = "constitution_versions"

    checksum = Column(String(128), primary_key=True)
    document = Column(JSON, nullable=False)
    meta = Column("metadata", JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active = Column(Boolean, nullable=False, default=True)


class ConstitutionSignature(storage_db.Base):
    __tablename__ = "constitution_signatures"
    __table_args__ = (
        UniqueConstraint("checksum", "signer_id", name="uq_constitution_signature"),
    )

    id = Column(String(256), primary_key=True)
    checksum = Column(String(128), nullable=False, index=True)
    signer_id = Column(String(128), nullable=False)
    signature = Column(String(1024), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConstitutionStorage:
    """Persist constitutions to Redis (hot) and Postgres/SQLite (historical)."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
        redis_key: str = "soma:constitution",
        redis_sig_key: str = "soma:constitution:signatures",
        db_url: Optional[str] = None,
    ) -> None:
        self._redis_client = redis_client
        self._redis_url = redis_url or os.getenv("SOMABRAIN_REDIS_URL")
        self._redis_key = redis_key
        self._redis_sig_key = redis_sig_key
        self._redis_checksum_key = f"{redis_key}:checksum"
        self._redis_meta_key = f"{redis_key}:meta"
        self._db_url = db_url
        self._ensure_schema()

    # ------------------------------------------------------------------
    def save_new(
        self, document: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        checksum = self._compute_checksum(document)
        metadata = metadata or {}
        now = dt.datetime.now(dt.timezone.utc)
        with self._session_scope() as session:
            session.execute(update(ConstitutionVersion).values(is_active=False))
            version = session.get(ConstitutionVersion, checksum)
            if version is None:
                version = ConstitutionVersion(
                    checksum=checksum, document=document, meta=metadata
                )
                session.add(version)
            else:
                version.document = document
                version.meta = metadata
            version.is_active = True
            version.created_at = now
        self._write_redis(document, checksum, signatures=[])
        self._write_redis_metadata(metadata, now)
        return checksum

    def load_active(self) -> ConstitutionRecord:
        try:
            with self._session_scope(readonly=True) as session:
                version = (
                    session.execute(
                        select(ConstitutionVersion)
                        .where(ConstitutionVersion.is_active.is_(True))
                        .order_by(ConstitutionVersion.created_at.desc())
                    )
                    .scalars()
                    .first()
                )
                if version is None:
                    version = (
                        session.execute(
                            select(ConstitutionVersion).order_by(
                                ConstitutionVersion.created_at.desc()
                            )
                        )
                        .scalars()
                        .first()
                    )
                if version is not None:
                    signatures = self.get_signatures(version.checksum, session=session)
                    return ConstitutionRecord(
                        document=version.document or {},
                        checksum=version.checksum,
                        metadata=version.meta or {},
                        created_at=self._ensure_datetime(version.created_at),
                        signatures=signatures or None,
                    )
        except SQLAlchemyError as exc:
            LOGGER.debug("DB load failed, falling back to Redis: %s", exc)

        record = self._load_from_redis()
        if record is not None:
            return record
        raise ConstitutionStorageError("No constitution document available")

    def record_signature(self, checksum: str, signer_id: str, signature: str) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        sig_id = f"{checksum}:{signer_id}"
        try:
            with self._session_scope() as session:
                session.merge(
                    ConstitutionSignature(
                        id=sig_id,
                        checksum=checksum,
                        signer_id=signer_id,
                        signature=signature,
                        created_at=now,
                    )
                )
        except SQLAlchemyError as exc:
            LOGGER.warning("Failed to persist constitution signature: %s", exc)
        self._sync_redis_signatures(checksum)

    def get_signatures(
        self, checksum: str, session: Optional[Session] = None
    ) -> List[Dict[str, str]]:
        owns_session = session is None
        if session is None:
            session_factory = storage_db.get_session_factory(self._db_url)
            session = session_factory()
        try:
            rows = (
                session.execute(
                    select(ConstitutionSignature)
                    .where(ConstitutionSignature.checksum == checksum)
                    .order_by(ConstitutionSignature.created_at.asc())
                )
                .scalars()
                .all()
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
        finally:
            if owns_session and session is not None:
                session.close()
        # fall back to Redis cache
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
        import json
        import os
        import datetime as dt

        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "checksum": checksum,
            "document": document,
            "metadata": metadata or {},
            "created_at": timestamp,
        }
        # Local snapshot
        local_path = None
        target = os.getenv("SOMABRAIN_CONSTITUTION_SNAPSHOT_DIR")
        if target:
            path = pathlib.Path(target)
            path.mkdir(parents=True, exist_ok=True)
            outfile = path / f"constitution_{timestamp}_{checksum[:12]}.json"
            outfile.write_text(json.dumps(payload, indent=2, sort_keys=True))
            LOGGER.info("wrote constitution snapshot to %s", outfile)
            local_path = str(outfile)
        # S3 snapshot
        s3_bucket = os.getenv("SOMABRAIN_CONSTITUTION_S3_BUCKET")
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
    @contextmanager
    def _session_scope(self, readonly: bool = False) -> Generator[Session, None, None]:
        session_factory = storage_db.get_session_factory(self._db_url)
        session = session_factory()
        try:
            yield session
            if readonly:
                session.rollback()
            else:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _ensure_schema(self) -> None:
        engine = storage_db.get_engine(self._db_url)
        storage_db.Base.metadata.create_all(engine)

    def _connect_redis(self):  # type: ignore[override]
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
        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha3_512(payload).hexdigest()

    @staticmethod
    def _ensure_datetime(value: Any) -> dt.datetime:
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
