"""
Memory Sync Worker for SomaBrain

This background service provides proactive, resilient synchronization of memories
that were queued locally while the remote memory service was unavailable.
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

import httpx

from somabrain import journal, metrics as M
from somabrain.memory_pool import MultiTenantMemory
from somabrain.infrastructure import get_memory_http_endpoint, require

LOGGER = logging.getLogger(__name__)


class MemorySyncWorker:
    """
    A background worker that monitors the memory service and replays queued
    memories from the local journal when the service is online.
    """

    def __init__(self, mt_memory: MultiTenantMemory, config: Any):
        self.mt_memory = mt_memory
        self.config = config
        self.poll_interval_seconds = int(getattr(config, "sync_worker_poll_interval", 30))
        self.batch_size = int(getattr(config, "sync_worker_batch_size", 100))
        self.delay_between_batches_seconds = float(getattr(config, "sync_worker_batch_delay", 1.0))
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._memory_service_healthy = False
        
        endpoint = require(
            get_memory_http_endpoint()
            or os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
            or os.getenv("MEMORY_SERVICE_URL"),
            message="Configure SOMABRAIN_MEMORY_HTTP_ENDPOINT for MemorySyncWorker.",
        )
        self._http_client = httpx.Client(base_url=endpoint, timeout=5.0)

    def start(self):
        """Starts the worker in a background thread."""
        LOGGER.info("Starting MemorySyncWorker...")
        self._thread.start()

    def stop(self):
        """Stops the worker."""
        LOGGER.info("Stopping MemorySyncWorker...")
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._http_client.close()

    def _run_loop(self):
        """The main loop for the worker thread."""
        while not self._stop_event.is_set():
            try:
                self._check_health_and_process_journals()
            except Exception:
                LOGGER.exception("Unhandled error in MemorySyncWorker loop.")
            
            self._stop_event.wait(self.poll_interval_seconds)

    def _check_health_and_process_journals(self):
        """Checks memory service health and processes journals if healthy."""
        try:
            response = self._http_client.get("/health")
            response.raise_for_status()
            if not self._memory_service_healthy:
                 LOGGER.info("Memory service is now healthy. Checking for journals to sync.")
            self._memory_service_healthy = True
            self._process_all_journals()
        except httpx.RequestError:
            if self._memory_service_healthy:
                LOGGER.warning("Memory service has gone offline. Will retry later.")
            self._memory_service_healthy = False

    def _process_all_journals(self):
        """Scans the journal directory and processes each namespace's journal."""
        journal_dir = getattr(self.config, "journal_dir", "./data/somabrain")
        if not os.path.isdir(journal_dir):
            return

        for filename in os.listdir(journal_dir):
            if self._stop_event.is_set():
                break
            if filename.endswith(".jsonl"):
                namespace = filename[:-len(".jsonl")]
                self._process_journal_for_namespace(namespace, journal_dir)

    def _process_journal_for_namespace(self, namespace: str, journal_dir: str):
        """Processes the journal for a single namespace, with rate limiting."""
        events = list(journal.iter_events(journal_dir, namespace))
        if not events:
            return

        LOGGER.info(f"Found {len(events)} events to sync for namespace '{namespace}'.")
        M.MEMORY_OUTBOX_PENDING_ITEMS.set(len(events))

        client = self.mt_memory.for_namespace(namespace)
        pending_events = list(events)
        
        while pending_events:
            if self._stop_event.is_set():
                break

            batch = pending_events[:self.batch_size]
            items_to_remember = []
            
            for event in batch:
                if event.get("type") == "mem":
                    items_to_remember.append((event["key"], event["payload"]))

            if items_to_remember:
                try:
                    # Sync memories to the real service
                    for key, payload in items_to_remember:
                        client.remember(key, payload)
                    
                    M.MEMORY_OUTBOX_SYNC_TOTAL.labels(status="success").inc(len(items_to_remember))
                    # Successfully synced - remove these events from pending
                    pending_events = pending_events[self.batch_size:]
                    LOGGER.info(f"Successfully synced {len(items_to_remember)} memories for namespace '{namespace}'.")
                except Exception:
                    LOGGER.exception(f"Failed to sync batch for namespace '{namespace}'. Will retry.")
                    M.MEMORY_OUTBOX_SYNC_TOTAL.labels(status="failure").inc(len(items_to_remember))
                    break  # Stop processing this namespace on failure to avoid data loss

            time.sleep(self.delay_between_batches_seconds)

        # Compact journal - only keep failed events, archive successful ones
        journal_path = journal.journal_path(journal_dir, namespace)
        
        # If we successfully processed everything, we can clear the journal
        if not pending_events:
            # Archive the old journal before clearing
            import shutil
            import time
            archive_path = f"{journal_path}.{int(time.time())}.processed"
            try:
                shutil.move(str(journal_path), archive_path)
                LOGGER.info(f"Archived processed journal for namespace '{namespace}' to {archive_path}")
            except Exception:
                # If archive fails, just truncate the journal
                with open(journal_path, "w") as f:
                    pass
        else:
            # Rewrite journal with only failed/pending events
            with open(journal_path, "w") as f:
                for event in pending_events:
                    f.write(json.dumps(event) + "\n")
        
        M.MEMORY_OUTBOX_PENDING_ITEMS.set(len(pending_events))


def setup_memory_sync_worker(mt_memory, config):
    """Setup and start the memory sync worker."""
    worker = MemorySyncWorker(mt_memory, config)
    worker.start()
    return worker
