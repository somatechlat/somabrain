# Minimal Dockerfile for SomaBrain API
FROM python:3.11-slim

WORKDIR /app

# Copy app source
COPY . /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir fastapi uvicorn httpx numpy prometheus-client redis fakeredis qdrant-client networkx somafractalmemory \
    && true

EXPOSE 8000

ENV SOMABRAIN_MEMORY_MODE=local

CMD ["uvicorn", "somabrain.app:app", "--host", "0.0.0.0", "--port", "8000"]
