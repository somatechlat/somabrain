"""Core Celery tasks for SomaBrain.

These tasks provide the execution layer for agents.
"""

import time
from typing import Dict, Any, Optional
from celery import shared_task
from celery.utils.log import get_task_logger
from somabrain.storage.task_registry import TaskRegistryStore
from somabrain.db.models.task import TaskRegistry

logger = get_task_logger(__name__)

@shared_task(bind=True, name="somabrain.tasks.core.health_check")
def health_check(self) -> Dict[str, Any]:
    """Simple task to verify the worker is alive and processing."""
    logger.info("Health check task executed")
    return {"status": "ok", "timestamp": time.time(), "worker": self.request.hostname}

@shared_task(bind=True, name="somabrain.tasks.core.register_task_dynamic")
def register_task_dynamic(self, task_name: str, schema: Dict[str, Any], description: Optional[str] = None) -> Dict[str, Any]:
    """
    Dynamically register a task in the TaskRegistry database.
    This allows agents to self-register capabilities asynchronously.
    """
    logger.info(f"Registering dynamic task: {task_name}")

    # Use the real store to persist the task definition
    store = TaskRegistryStore()

    # Check if exists
    existing = store.get_by_name(task_name)
    if existing:
        logger.info(f"Task {task_name} already exists, updating...")
        from somabrain.api.schemas.task import TaskUpdate
        updated = store.update(existing.id, TaskUpdate(description=description, schema=schema))
        return {"action": "updated", "id": updated.id, "name": updated.name}
    else:
        from somabrain.api.schemas.task import TaskCreate
        # Provide defaults for required fields if missing
        task_data = TaskCreate(
            name=task_name,
            description=description,
            schema=schema,
            version="1.0.0" # Default version
        )
        created = store.create(task_data)
        return {"action": "created", "id": created.id, "name": created.name}
