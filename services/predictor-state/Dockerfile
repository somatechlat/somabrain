# syntax=docker/dockerfile:1.6
###############################
# DEPRECATED – DO NOT USE
# This repository builds a single canonical image from the root Dockerfile.
# This per-service Dockerfile is intentionally invalid to prevent accidental use.
# Build the root image instead (Dockerfile at repo root), which is what CI, Helm,
# and docker-compose use.

ERROR DO_NOT_USE_THIS_DOCKERFILE

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/opt/somabrain

WORKDIR ${APP_HOME}

COPY . .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir . \
    && find . -name "__pycache__" -prune -exec rm -rf {} +

ENV PYTHONPATH=${APP_HOME}

CMD ["python", "services/predictor-state/main.py"]
