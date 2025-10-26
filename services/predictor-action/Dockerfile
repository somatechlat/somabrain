# syntax=docker/dockerfile:1.6
###############################
# DEPRECATED – DO NOT USE
# Use the root-level Dockerfile to build the canonical image.
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

CMD ["python", "services/predictor-action/main.py"]
