"""
Local Journal Module for SomaBrain

This module provides a local journaling system that ensures durable event storage.
The journal provides reliable local storage for all events with redundant persistence
and comprehensive operational capabilities.

Key Features:
- Local journaling with file-based storage
- Configurable rotation and retention policies
- Integration with outbox system for redundant persistence
- Thread-safe operations for concurrent access
- JSON-based event serialization for readability

Classes:
    LocalJournal: Main local journal implementation
    JournalConfig: Configuration for journal behavior
    JournalEvent: Journal event data structure

Functions:
    get_journal: Get or create the global journal instance
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from dataclasses import dataclass, asdict
import logging

# NOTE: The journal configuration pulls values from the global ``settings``
# object defined in ``common.config.settings``. The original implementation
# referenced ``settings`` without importing it, which caused a ``NameError``
# when the journal was first used (e.g., during degradation mode). The
# exception was silently swallowed in ``_queue_degraded`` leading to the
# appearance that events were queued, while in reality nothing was persisted.
# Importing the settings module fixes the issue and ensures the journal
# directory (default ``/tmp/somabrain_journal``) is created correctly.
# Import the concrete ``settings`` instance used throughout the project.
# Individual modules typically import ``settings`` via
# ``from common.config.settings import settings``.  Using the same import
# here guarantees the environment‑variable defaults (e.g. ``SOMABRAIN_JOURNAL_DIR``)
# are respected and avoids a ``NameError`` during journal initialisation.
from common.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class JournalConfig:
    """Configuration for local journal behavior."""

    journal_dir: str = "/tmp/somabrain_journal"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_files: int = 10
    rotation_interval: int = 86400  # 24 hours in seconds
    retention_days: int = 7
    compression: bool = True
    sync_writes: bool = True  # fsync for durability

    @classmethod
    def from_env(cls) -> JournalConfig:
        """Create configuration from environment variables safely.

        Mirrors the robust helpers used in ``common.config.settings`` –
        stripping comments and handling conversion errors gracefully.
        """

        # Helper to parse int env vars with comment stripping
        def _int(name: str, default: int) -> int:
            # Access Settings attribute directly; fallback to provided default.
            raw = getattr(settings, name.lower(), str(default))
            raw = raw.split("#", 1)[0].strip()
            try:
                return int(raw)
            except Exception:
                return default

        def _bool(name: str, default: bool) -> bool:
            raw = getattr(settings, name.lower(), None)
            if raw is None:
                return default
            raw = raw.split("#", 1)[0].strip()
            return raw.lower() in {"1", "true", "yes", "on"}

        return cls(
            journal_dir=(
                getattr(settings, "journal_dir", None)
                if hasattr(settings, "journal_dir")
                else "/tmp/somabrain_journal"
            ),
            max_file_size=_int("SOMABRAIN_JOURNAL_MAX_FILE_SIZE", 104_857_600),
            max_files=_int("SOMABRAIN_JOURNAL_MAX_FILES", 10),
            rotation_interval=_int("SOMABRAIN_JOURNAL_ROTATION_INTERVAL", 86_400),
            retention_days=_int("SOMABRAIN_JOURNAL_RETENTION_DAYS", 7),
            compression=_bool("SOMABRAIN_JOURNAL_COMPRESSION", True),
            sync_writes=_bool("SOMABRAIN_JOURNAL_SYNC_WRITES", True),
        )


@dataclass
class JournalEvent:
    """Journal event data structure."""

    id: str
    topic: str
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    dedupe_key: Optional[str] = None
    timestamp: datetime = None
    status: str = "pending"  # pending, sent, failed
    retries: int = 0
    last_error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JournalEvent:
        """Create event from dictionary."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class LocalJournal:
    """Local file-based journal implementation."""

    def __init__(self, config: JournalConfig):
        self.config = config
        self.journal_dir = Path(config.journal_dir)
        self.current_file: Optional[Path] = None
        self.current_file_handle = None
        self.current_file_size = 0
        self.last_rotation = time.time()
        self._lock = threading.RLock()
        self._initialized = False

        self._initialize()

    def _initialize(self) -> None:
        """Initialize the journal directory and current file."""
        try:
            # Create journal directory if it doesn't exist
            self.journal_dir.mkdir(parents=True, exist_ok=True)

            # Clean up old files based on retention policy
            self._cleanup_old_files()

            # Find or create current journal file
            self._rotate_if_needed()

            self._initialized = True
            logger.info(f"Local journal initialized at {self.journal_dir}")

        except Exception as e:
            logger.error(f"Failed to initialize local journal: {e}")
            raise

    def _cleanup_old_files(self) -> None:
        """Clean up journal files older than retention period."""
        if not self.journal_dir.exists():
            return

        cutoff_time = datetime.utcnow() - timedelta(days=self.config.retention_days)

        for file_path in self.journal_dir.glob("journal_*.json*"):
            try:
                # Extract timestamp from filename
                if file_path.stem.startswith("journal_"):
                    timestamp_str = file_path.stem[8:]  # Remove "journal_" prefix
                    try:
                        file_time = datetime.fromisoformat(
                            timestamp_str.replace("_", ":")
                        )
                        if file_time < cutoff_time:
                            file_path.unlink()
                            logger.info(f"Cleaned up old journal file: {file_path}")
                    except ValueError:
                        # If we can't parse the timestamp, keep the file
                        continue
            except Exception as e:
                logger.warning(f"Failed to clean up journal file {file_path}: {e}")

    def _rotate_if_needed(self) -> None:
        """Rotate journal file if needed based on size or time."""
        current_time = time.time()

        # Check if rotation is needed
        needs_rotation = (
            not self._initialized
            or self.current_file is None
            or not self.current_file.exists()
            or self.current_file_size >= self.config.max_file_size
            or current_time - self.last_rotation >= self.config.rotation_interval
        )

        if not needs_rotation:
            return

        # Close current file if open
        if self.current_file_handle:
            try:
                self.current_file_handle.close()
            except Exception:
                pass
            self.current_file_handle = None

        # Create new journal file
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        new_file = self.journal_dir / f"journal_{timestamp}.json"

        try:
            self.current_file = new_file
            self.current_file_handle = open(new_file, "a", encoding="utf-8")
            self.current_file_size = new_file.stat().st_size if new_file.exists() else 0
            self.last_rotation = current_time
            logger.info(f"Rotated to new journal file: {new_file}")
        except Exception as e:
            logger.error(f"Failed to create new journal file {new_file}: {e}")
            raise

    def _write_event(self, event: JournalEvent) -> bool:
        """Write a single event to the journal file."""
        if not self._initialized:
            return False

        try:
            with self._lock:
                self._rotate_if_needed()

                if not self.current_file_handle:
                    return False

                # Serialize event to JSON
                event_data = event.to_dict()
                json_line = json.dumps(event_data, ensure_ascii=False) + "\n"

                # Write to file
                if self.config.sync_writes:
                    self.current_file_handle.write(json_line)
                    self.current_file_handle.flush()
                    os.fsync(self.current_file_handle.fileno())
                else:
                    self.current_file_handle.write(json_line)

                self.current_file_size += len(json_line.encode("utf-8"))

                return True

        except Exception as e:
            logger.error(f"Failed to write event to journal: {e}")
            return False

    def append_event(self, event: JournalEvent) -> bool:
        """Append an event to the journal."""
        return self._write_event(event)

    def append_events(self, events: Sequence[JournalEvent]) -> int:
        """Append multiple events to the journal."""
        written = 0
        for event in events:
            if self._write_event(event):
                written += 1
        return written

    def read_events(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        topic: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> List[JournalEvent]:
        """Read events from journal files with filtering."""

        events = []

        try:
            # Read from all journal files, newest first
            journal_files = sorted(
                self.journal_dir.glob("journal_*.json*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            for file_path in journal_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                event_data = json.loads(line)
                                event = JournalEvent.from_dict(event_data)

                                # Apply filters
                                if tenant_id and event.tenant_id != tenant_id:
                                    continue
                                if status and event.status != status:
                                    continue
                                if topic and event.topic != topic:
                                    continue
                                if since and event.timestamp < since:
                                    continue

                                events.append(event)

                                # Apply limit
                                if limit and len(events) >= limit:
                                    return events[:limit]

                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"Failed to parse journal event: {e}")
                                continue

                except Exception as e:
                    logger.warning(f"Failed to read journal file {file_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to read journal events: {e}")

        return events

    def mark_events_sent(self, event_ids: Sequence[str]) -> int:
        """Mark events as sent in the journal."""

        # For file-based journal, we need to rewrite the files
        # This is expensive but ensures consistency
        updated = 0

        try:
            with self._lock:
                # Read all events
                all_events = self.read_events()

                # Update status for matching events
                for event in all_events:
                    if event.id in event_ids and event.status != "sent":
                        event.status = "sent"
                        updated += 1

                if updated > 0:
                    # Rewrite all journal files
                    self._rewrite_journal_files(all_events)

        except Exception as e:
            logger.error(f"Failed to mark events as sent: {e}")

        return updated

    def _rewrite_journal_files(self, events: List[JournalEvent]) -> None:
        """Rewrite all journal files with updated events."""
        # Close current file
        if self.current_file_handle:
            try:
                self.current_file_handle.close()
            except Exception:
                pass
            self.current_file_handle = None

        # Remove existing journal files
        for file_path in self.journal_dir.glob("journal_*.json*"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove journal file {file_path}: {e}")

        # Reset rotation state and rewrite events
        self.current_file = None
        self.current_file_size = 0
        self.last_rotation = time.time()

        # Write events in chronological order
        events.sort(key=lambda x: x.timestamp)
        for event in events:
            self._write_event(event)

    def get_stats(self) -> Dict[str, Any]:
        """Get journal statistics."""
        try:
            stats = {
                "journal_dir": str(self.journal_dir),
                "current_file": str(self.current_file) if self.current_file else None,
                "current_file_size": self.current_file_size,
                "max_file_size": self.config.max_file_size,
                "last_rotation": self.last_rotation,
            }

            # Count files and total size
            journal_files = list(self.journal_dir.glob("journal_*.json*"))
            stats["file_count"] = len(journal_files)
            stats["total_size"] = sum(
                f.stat().st_size for f in journal_files if f.exists()
            )

            # Count events by status
            events = self.read_events()
            stats["total_events"] = len(events)
            stats["pending_events"] = sum(1 for e in events if e.status == "pending")
            stats["sent_events"] = sum(1 for e in events if e.status == "sent")
            stats["failed_events"] = sum(1 for e in events if e.status == "failed")

            return stats

        except Exception as e:
            logger.error(f"Failed to get journal stats: {e}")
            return {"error": str(e)}

    def close(self) -> None:
        """Close the journal and cleanup resources."""
        with self._lock:
            if self.current_file_handle:
                try:
                    self.current_file_handle.close()
                except Exception:
                    pass
                self.current_file_handle = None
            self._initialized = False


# Global journal instance
_journal: Optional[LocalJournal] = None


def get_journal() -> LocalJournal:
    """Get or create the global journal instance."""
    global _journal
    if _journal is None:
        config = JournalConfig.from_env()
        _journal = LocalJournal(config)
    return _journal


def init_journal(config: Optional[JournalConfig] = None) -> LocalJournal:
    """Initialize the global journal with specific configuration."""
    global _journal
    if config is None:
        config = JournalConfig.from_env()
    _journal = LocalJournal(config)
    return _journal
