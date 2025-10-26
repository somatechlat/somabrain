# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS runtime

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

CMD ["python", "services/predictor-agent/main.py"]
