# SomaBrain Tilt Development Configuration
# VIBE Rule 113: Port Sovereignty - 30xxx Range (Cognitive Tier L3)
# VIBE Rule 102: Shared-Nothing Architecture (Island Mandate)
# RAM BUDGET: 10GB Maximum (VIBE Rule 108)

print("""
+==============================================================+
|         SOMABRAIN - ISOLATED LOCAL DEVELOPMENT               |
+==============================================================+
|  Tilt Dashboard:   http://localhost:10352                    |
|  Brain API:        http://localhost:30101                    |
|  Postgres:         localhost:30106                           |
|  Redis:            localhost:30100                           |
|  Kafka:            localhost:30102                           |
|  Milvus:           localhost:30119                           |
+==============================================================+
|  RAM BUDGET: 10GB Maximum                                    |
+==============================================================+
""")

# Load existing docker-compose.yml infrastructure
docker_compose('./docker-compose.yml')

# Development server with live reload
local_resource(
    'somabrain-dev',
    serve_cmd='.venv/bin/uvicorn somabrain.asgi:application --host 0.0.0.0 --port 30101 --reload',
    serve_dir='.',
    env={
        'SA01_DEPLOYMENT_MODE': 'PROD',
        'SOMABRAIN_HOST': '0.0.0.0',
        'SOMABRAIN_PORT': '30101',
    },
    links=['http://localhost:30101/health'],
    labels=['app'],
    resource_deps=['somabrain_postgres', 'somabrain_redis', 'somabrain_kafka'],
)

# Database migrations
local_resource(
    'db-migrate',
    cmd='''
        set -e
        echo "⏳ Waiting for Postgres..."
        until pg_isready -h localhost -p 30106; do sleep 1; done
        echo "🔄 Running migrations..."
        .venv/bin/python manage.py migrate --noinput
        echo "✅ Migrations complete"
    ''',
    resource_deps=['somabrain_postgres'],
    labels=['setup'],
)
