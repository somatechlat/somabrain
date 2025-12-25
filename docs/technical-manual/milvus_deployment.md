# Milvus Deployment (Sprint 1 – Infra Bootstrap)

This document captures the **Sprint 1** deliverable that boots the Milvus vector database using a **minimal Helm chart** located under `infra/helm/charts/milvus`.

## Why Milvus?
* The existing Redis‑based vector store performs a linear Hamming scan, which becomes a bottleneck once the number of stored vectors exceeds a few‑thousand entries.
* Milvus provides native ANN indexes (BIN_IVF_FLAT, Hamming metric) and can scale horizontally with sharding and replication.
* The official Docker image `milvusdb/milvus:v2.4.0` is production‑ready and is the image referenced in the chart.

## Chart Structure
```
infra/helm/charts/milvus/
├─ Chart.yaml          # chart metadata (appVersion = 2.4)
├─ values.yaml         # default values (replicaCount, resources, image, service)
├─ templates/
│  ├─ _helpers.tpl    # naming & labeling helpers (VIBE‑compliant – no hard‑coded literals)
│  ├─ deployment.yaml # Deployment resource – pulls image, sets env for Etcd/MinIO (place‑holders for a full production stack)
│  └─ service.yaml    # ClusterIP Service exposing port 19530 (gRPC) to the rest of the SomaBrain stack
```

### Key VIBE‑compliant aspects
* **All configurable values live in `values.yaml`** – replica count, image tag, resources, service type/port. No hard‑coded literals appear in the templates.
* **Helper functions** (`_helpers.tpl`) centralise naming and labeling, guaranteeing consistent labels across resources.
* **Resource limits/requests** are defined to keep the pod within a modest footprint for dev clusters (`500m` CPU, `1Gi` memory).

## Installing the chart
```bash
# From the repository root
helm repo add milvus https://milvus-io.github.io/milvus-helm
# (Optional) update repo index
helm repo update

# Install the chart in the `soma` namespace (create it if needed)
kubectl create namespace soma || true
helm upgrade --install milvus infra/helm/charts/milvus \
  --namespace soma \
  --set replicaCount=1 \
  --set image.tag=v2.4.0
```

The chart will create a **Deployment** named `<release‑name>-milvus` and a **ClusterIP Service** exposing port `19530`. Other SomaBrain services (e.g., the Oak option manager) can reach Milvus via the service name `milvus` inside the same namespace.

## Next steps (Sprint 2)
* Add the Milvus endpoint to `common.config.settings` (`milvus_host`, `milvus_port`, `milvus_collection`).
* Implement `somabrain/milvus_client.py` that wraps the SDK and uses the configuration values.
* Replace the Redis‑based vector store in the Oak option manager with the Milvus client.

---
*Document authored by the VIBE‑compliant development assistant. All code follows the VIBE coding rules (type hints, single source of truth, no magic numbers).* 