# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 ARCHITECTURE: COLIMA + TILT + MINIKUBE 🚨
# ═══════════════════════════════════════════════════════════════════════════════
# SomaBrain Tilt Development Configuration
# VIBE Rule 113: Port Sovereignty - 30xxx Range (Cognitive Tier L3)
# VIBE Rule 102: Shared-Nothing Architecture (Island Mandate)
# RAM BUDGET: 10GB Maximum (VIBE Rule 108)
# ═══════════════════════════════════════════════════════════════════════════════

print("""
+==============================================================+
|             SOMABRAIN - ISOLATED K8S DEPLOYMENT              |
+==============================================================+
|  Tilt Dashboard:   http://localhost:10352                    |
|  Brain API:        http://localhost:30101                    |
|  Minikube Profile: brain                                     |
+==============================================================+
|  RAM BUDGET: 10GB Maximum | ARCHITECTURE: Colima+Tilt+Minikube |
+==============================================================+
""")

# Ensure we're using the brain minikube profile
allow_k8s_contexts('brain')

# Build the SomaBrain API image
docker_build(
    'somabrain-api',
    '.',
    dockerfile='Dockerfile',
    live_update=[
        sync('.', '/app'),
    ]
)

# Deploy resilient K8s manifests
k8s_yaml('infra/k8s/brain-resilient.yaml')

# Resource configuration with port forwards
k8s_resource(
    'somabrain-api',
    port_forwards=['20020:20020'],
    labels=['app'],
    resource_deps=['postgres', 'redis', 'milvus', 'kafka']
)

k8s_resource(
    'postgres',
    port_forwards=['30106:5432'],
    labels=['infra']
)

k8s_resource(
    'redis',
    port_forwards=['30100:6379'],
    labels=['infra']
)

k8s_resource(
    'kafka',
    port_forwards=['30102:9092'],
    labels=['infra']
)

k8s_resource(
    'milvus',
    port_forwards=['30119:19530'],
    labels=['infra']
)
