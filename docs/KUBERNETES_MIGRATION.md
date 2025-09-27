## Kubernetes migration impact analysis

This document summarizes the impact and recommended steps to migrate the current Docker Compose DEV stack for Somabrain to Kubernetes. It focuses on the developer/dev cluster migration (kind/minikube) and provides pointers for production-ready choices.

### Goal
Run the full DEV_FULL stack in Kubernetes so Somabrain connects to real Kafka/OPA/Redis/Memory services, supports running integration tests from the host `.venv`, and enables ramped benchmarks (100 → 10k) against real backends.

### High-level mapping
- Docker Compose service -> Kubernetes object(s)
  - somabrain (FastAPI / Uvicorn) -> Deployment + Service (+Ingress/NodePort for host access)
  - redis -> StatefulSet (or Deployment for dev) + Service
  - opa -> Deployment + Service
  - memory service (SFM) -> Deployment + Service
  - kafka (Redpanda/Strimzi) -> Operator-backed StatefulSet (Strimzi or Redpanda operator is recommended) or use a simple single-node broker for dev
  - postgres -> StatefulSet / managed DB or Postgres operator
  - qdrant -> StatefulSet or Helm chart for Qdrant
  - prometheus -> Helm chart / Deployment (optional for dev)
  - persistence/backups -> PersistentVolumeClaims + StorageClass

### Required Kubernetes resources
- Namespace (e.g. `somabrain-dev`)
- Deployments or StatefulSets for stateful services
- Services (ClusterIP for internal connectivity; NodePort/LoadBalancer for host access)
- ConfigMaps for non-sensitive configuration (SOMABRAIN envs, OPA policies)
- Secrets for credentials (DB users, Kafka TLS, etc.)
- PersistentVolumeClaims for Postgres/Qdrant/Redis if you need durable storage
- Probes (readiness & liveness) for Somabrain and memory service
- RBAC if using operators that require it
- NetworkPolicy if you need isolation (optional for dev)

### Networking and host access
- In-cluster services should reference each other by DNS name (service.namespace.svc.cluster.local). For the Somabrain app use environment variables like:
  - SOMA_KAFKA_URL=sb-kafka:9092
  - SOMABRAIN_OPA_URL=http://sb-opa:8181
  - SOMA_REDIS_URL=redis://sb-redis:6379/0
  - SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://somamemory:9595
- To reach services from the host (for running `.venv`-based tests):
  - Option A (recommended for dev): use `kubectl port-forward` for each service you need reachable on localhost (9696, 9092, 8181, 6379, 9595)
  - Option B: expose Somabrain via NodePort (or LoadBalancer in minikube) and access via minikube IP or localhost for kind with node port mapping
  - Option C: use a LoadBalancer implementation (MetalLB) on kind to provide cluster IPs reachable from host

### Storage and stateful considerations
- For development, you can run Redis and Qdrant with ephemeral storage. For persistence and integration testing that checks persistence to Postgres/Qdrant:
  - Use PVCs backed by hostPath (minikube) or standard StorageClass
  - Use Postgres operator (e.g. Zalando/Postgres-Operator) or a managed Postgres for production
  - Qdrant has a Helm chart which creates StatefulSet + PVCs

### Operators & Helm charts (recommended)
- Kafka: Strimzi or Redpanda operator. Strimzi is common and exposes Kafka bootstrap services. For production-like behavior use Strimzi with a 3-node Kafka cluster.
- Postgres: Zalando Postgres Operator or Helm chart (Bitnami) for development. For production use a managed DB or operator-backed cluster.
- Qdrant: Official Helm chart (or the community chart) to manage StatefulSet and volumes.
- Prometheus & OPA: install via Helm charts (prometheus-community/kube-prometheus-stack and open-policy-agent/opa-helm)

### CI/CD and developer workflow changes
- Build images inside CI or use image registry. For local clusters (kind): after building images locally, `kind load docker-image <image>` to make them available to the cluster.
- Replace `docker compose up` with `kubectl apply -f k8s/` or a Helm chart deploy in CI.
- Health checks in the repo (prechecks) should be updated to optionally use `kubectl port-forward` or ClusterIP names (when run from a pod inside the cluster).
- Tests that run from the host `.venv` should either use port-forwarding or run inside a test runner pod in the cluster (recommended for parity).

### Dev vs Production differences
- Dev: single-node Kafka, ephemeral volumes, NodePort for host access, reduced resource requests/limits
- Prod: multi-node Kafka via operator, PVCs with replicated storage, readiness/liveness tuned, resource quotas, RBAC and network policies, TLS and auth for Kafka/Postgres/Qdrant

### Risks and mitigations
- Operator complexity: operators require RBAC and cluster roles; mitigate with thorough operator testing in staging and smaller clusters first.
- Networking differences: host-local access differs; mitigate by testing both host-run (port-forward) and cluster-run (tests executed in a test pod).
- Stateful data persistence: ensure PVC size and StorageClass are available in the target cluster before migrating.

### Minimal testing checklist
- [ ] Create a `somabrain-dev` namespace
- [ ] Deploy Redis, OPA, Memory, and Somabrain in the namespace
- [ ] Expose Somabrain on localhost:9696 via `kubectl port-forward` or NodePort
- [ ] Run `scripts/sb_precheck.py` from `.venv` with host port forwards in place
- [ ] Run integration tests; if tests are flaky, run them from a job/pod inside the cluster to ensure same network view

### Example commands (local kind cluster)

Build image and load into kind:

```bash
# build the image locally (from repo root)
docker build -t somatechlat/somabrain:dev .
# create cluster named 'somabrain'
kind create cluster --name somabrain
# load image into kind
kind load docker-image somatechlat/somabrain:dev --name somabrain
# apply manifests
kubectl apply -f k8s/minimal-manifests.yaml -n somabrain-dev
# port-forward somabrain to localhost:9696
kubectl -n sombrain-dev port-forward svc/somabrain 9696:9696 &
# then run prechecks from host
python scripts/sb_precheck.py
```

### Next steps & migration plan
1. Create k8s manifests for dev (this repo includes `k8s/minimal-manifests.yaml` as a starting point).
2. Stand up a local cluster (kind/minikube) and iterate on manifests until the prechecks pass.
3. Decide on operator choices for Kafka/Postgres/Qdrant and install them in a staging cluster.
4. Migrate data from current local volumes (if needed) into PVCs.
5. Update CI to run integration tests inside a cluster-run job to reduce host/cluster networking mismatches.

### Notes & tradeoffs
- For strict NO_MOCKS testing you will want the memory service (SFM), Postgres and Qdrant running in-cluster with PVCs. If that is difficult, run the memory service out-of-cluster and expose it to the cluster (not recommended for production parity).

---

File pointers:
- `k8s/minimal-manifests.yaml` — minimal manifests for dev testing (Namespace, Deployments, Services)
- `k8s/README.md` — quick local-run instructions

If you'd like I can now generate a Helm chart skeleton, or scaffold separate manifests per service and a Kustomize overlay for dev/staging/production.