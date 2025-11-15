"""
Journal Module for SomaBrain

This module provides optional local journaling capabilities for the SomaBrain system.
The journal serves as a durable local storage mechanism for events when the database
is unavailable or for debugging/troubleshooting purposes.

Features:
- Optional local file-based journaling
- Configurable rotation and retention policies
- Thread-safe operations
- Integration with outbox system
- JSON-based event serialization

Usage:
    from somabrain.journal import get_journal, init_journal
    
    # Get the global journal instance
    journal = get_journal()
    
    # Initialize with custom config
    config = JournalConfig(enabled=True, journal_dir="/custom/path")
    journal = init_journal(config)
    
    # Append an event
    event = JournalEvent(
        id="event-123",
        topic="user.created",
        payload={"user_id": "user-456"},
        tenant_id="tenant-789"
    )
    journal.append_event(event)
    
    # Read events with filtering
    events = journal.read_events(tenant_id="tenant-789", status="pending")
"""

from .local_journal import (
    JournalConfig,
    JournalEvent,
    LocalJournal,
    get_journal,
    init_journal,
)

__all__ = [
    "JournalConfig",
    "JournalEvent", 
    "LocalJournal",
    "get_journal",
    "init_journal",
]