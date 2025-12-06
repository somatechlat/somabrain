"""Celery application configuration.

This module initializes the Celery app using the centralized settings from
``common.config.settings``. It avoids ``os.getenv`` and uses real broker/backend
URLs.
"""

from __future__ import annotations

from celery import Celery
from common.config.settings import settings

# Initialize Celery app
celery_app = Celery("somabrain")

# Load configuration from settings
celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,  # Use Redis for results as well
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker configuration
    worker_prefetch_multiplier=1,  # Fair dispatch
    worker_concurrency=settings.workers,  # Respect worker count setting
    # Task routing (optional, but good practice)
    task_routes={
        "somabrain.tasks.core.*": {"queue": "default"},
    },
)

# Auto-discover tasks in the somabrain package
celery_app.autodiscover_tasks(["somabrain.tasks.core"])
