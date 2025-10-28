"""
Memory Integrity Worker for SomaBrain (S3 Sprint)

This background service consumes memory events (e.g., from Kafka or polling) and verifies that
Redis, Postgres, and the vector store remain in sync. It periodically checks for discrepancies
and emits alerts or attempts reconciliation if mismatches are found.
"""

import os
import time
import logging
from typing import Optional, Set
import argparse
import sqlite3
import json

from somabrain.infrastructure import get_redis_url

# Optional: import Kafka consumer, Redis, Postgres, and vector store clients
try:
    import redis  # type: ignore
except ImportError:
    redis = None

# Placeholder imports for Postgres and vector store
# from somabrain.storage.db import get_postgres_session
# from somabrain.vector_client import VectorStoreClient

LOGGER = logging.getLogger("somabrain.services.memory_integrity_worker")


class MemoryIntegrityWorker:
    def __init__(self, redis_url: Optional[str] = None, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self._use_redis = False
        if redis is not None:
            url = redis_url or get_redis_url()
            try:
                if url:
                    self._redis = redis.from_url(url)
                    self._redis.ping()
                    self._use_redis = True
                else:
                    self._redis = None
            except Exception as e:
                LOGGER.warning(f"Redis unavailable: {e}")
                self._redis = None
        else:
            self._redis = None
        # Try Postgres (psycopg2) if available
        self._pg = None
        try:
            import psycopg2

            pg_dsn = os.getenv("SOMABRAIN_PG_DSN") or os.getenv("SOMABRAIN_PG_URL")
            if pg_dsn:
                try:
                    self._pg = psycopg2.connect(pg_dsn)
                except Exception as e:
                    LOGGER.warning("Failed to connect to Postgres: %s", e)
        except Exception:
            # psycopg2 not installed or not configured
            self._pg = None

        # Try vector store client if available (optional integration)
        self._vector = None
        try:
            from somabrain.vector_client import VectorStoreClient

            try:
                self._vector = VectorStoreClient.from_env()
            except Exception:
                self._vector = None
        except Exception:
            self._vector = None

        # As a lightweight fallback for testing/run-on-host we can point at a local
        # sqlite DB (MEMORY_DB_PATH) which holds a simple table `memories(id TEXT)`.
        self._sqlite = None
        db_path = os.getenv("MEMORY_DB_PATH", "./data/memory.db")
        try:
            if os.path.exists(db_path):
                self._sqlite = sqlite3.connect(db_path, check_same_thread=False)
        except Exception:
            self._sqlite = None

    def poll_and_check(self):
        """Poll memory stores and check for consistency."""
        LOGGER.info("Polling memory stores for consistency...")
        # Example: fetch keys from Redis
        redis_keys: Set[str] = set()
        if self._use_redis and self._redis is not None:
            try:
                raw = self._redis.keys("mem:*")
                # normalize bytes/strings
                redis_keys = set(
                    k.decode("utf-8") if isinstance(k, (bytes, bytearray)) else str(k)
                    for k in raw
                )
            except Exception as e:
                LOGGER.error(f"Failed to fetch Redis keys: {e}")
        # TODO: Fetch keys from Postgres and vector store
        pg_keys: Set[str] = set()
        vector_keys: Set[str] = set()
        # Postgres keys
        if self._pg is not None:
            try:
                cur = self._pg.cursor()
                cur.execute("SELECT id FROM memories")
                rows = cur.fetchall()
                pg_keys = set(str(r[0]) for r in rows)
            except Exception as e:
                LOGGER.warning("Failed to fetch Postgres keys: %s", e)

        # SQLite fallback
        if not pg_keys and self._sqlite is not None:
            try:
                cur = self._sqlite.cursor()
                cur.execute("SELECT id FROM memories")
                rows = cur.fetchall()
                pg_keys = set(str(r[0]) for r in rows)
            except Exception as e:
                LOGGER.debug("SQLite read failed: %s", e)

        # Vector store keys
        if self._vector is not None:
            try:
                vector_keys = set(self._vector.list_ids())
            except Exception as e:
                LOGGER.warning("Failed to list vector store ids: %s", e)
        # Compare sets
        missing_in_pg = redis_keys - pg_keys
        missing_in_redis = pg_keys - redis_keys
        missing_in_vector = redis_keys - vector_keys
        # Log/report discrepancies
        if missing_in_pg:
            LOGGER.warning(
                "Keys in Redis but missing in Postgres: %s", list(missing_in_pg)[:20]
            )
        if missing_in_redis:
            LOGGER.warning(
                "Keys in Postgres but missing in Redis: %s", list(missing_in_redis)[:20]
            )
        if missing_in_vector:
            LOGGER.warning(
                "Keys in Redis but missing in vector store: %s",
                list(missing_in_vector)[:20],
            )

        # Emit a short report via logging for CI/dev usage
        report = {
            "redis_count": len(redis_keys),
            "pg_count": len(pg_keys),
            "vector_count": len(vector_keys),
            "missing_in_pg": list(missing_in_pg)[:50],
            "missing_in_redis": list(missing_in_redis)[:50],
            "missing_in_vector": list(missing_in_vector)[:50],
        }
        try:
            serialized = json.dumps(report)
        except Exception:
            serialized = None
        if serialized is not None:
            LOGGER.info("Memory integrity report: %s", serialized)
        else:
            LOGGER.info("Memory integrity report: %s", report)
        # TODO: Add reconciliation logic if desired
        return report

    def run(self):
        LOGGER.info("Starting Memory Integrity Worker...")
        # Support both continuous and one-shot CLI usage
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--once", action="store_true", help="Run one check and exit"
        )
        args, _ = parser.parse_known_args()
        if args.once:
            self.poll_and_check()
            return
        while True:
            self.poll_and_check()
            time.sleep(self.poll_interval)


def main_cli():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    args = parser.parse_args()
    worker = MemoryIntegrityWorker()
    if args.once:
        worker.poll_and_check()
    else:
        worker.run()


if __name__ == "__main__":
    main_cli()
