"""Celery worker entrypoint.

This script starts the Celery worker process for SomaBrain.
"""

from somabrain.tasks.celery_app import celery_app

# This file is the entrypoint for the worker process.
# Usage: celery -A somabrain.workers.celery_worker worker --loglevel=info

if __name__ == "__main__":
    celery_app.start()
