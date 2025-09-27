Kubernetes local run instructions (dev)

This file explains quick steps to try the minimal manifests with `kind` or `minikube`.

1) Create a local cluster (kind example):

```bash
# create kind cluster
kind create cluster --name somabrain

# build somabrain image locally and load into kind
docker build -t somatechlat/somabrain:dev .
kind load docker-image somatechlat/somabrain:dev --name somabrain

# if you have a memory service image, build and load it too
# docker build -t somatechlat/somamemory:dev path/to/memory
# kind load docker-image somatechlat/somamemory:dev --name somabrain
```

2) Apply the manifests:

```bash
kubectl apply -f k8s/minimal-manifests.yaml
```

3) Make Somabrain and other services reachable from your host for tests:

Option A (port-forward):

```bash
# forward somabrain
kubectl -n somabrain-dev port-forward svc/somabrain 9696:9696 &
# forward memory service
kubectl -n somabrain-dev port-forward svc/somamemory 9595:9595 &
# forward redis if desired
kubectl -n somabrain-dev port-forward svc/sb-redis 6379:6379 &
# forward opa
kubectl -n somabrain-dev port-forward svc/sb-opa 8181:8181 &
```

Option B (NodePort):
- Somabrain is configured in the manifest to use NodePort 30096; use `kubectl get nodes -o wide` and `kubectl get svc -n somabrain-dev somabrain` to determine the node IP and access it via `NODE_IP:30096`.

4) Run prechecks and tests from `.venv`:

```bash
# run precheck (ensure your venv has kafka-python, redis and requests)
python scripts/sb_precheck.py

# run integration tests (example)
SOMA_KAFKA_URL=sb-kafka:9092 \ 
SOMABRAIN_OPA_URL=http://localhost:8181 \ 
SOMA_REDIS_URL=redis://localhost:6379/0 \ 
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595 \ 
python -m pytest -m integration -q -r a --maxfail=5
```

Notes:
- For Kafka in Kubernetes use Strimzi or Redpanda operator; the minimal manifests intentionally omit Kafka since operator installation is recommended.
- If you run tests from host, prefer port-forward per-service so the host `scripts/sb_precheck.py` can reach the services at `localhost`.
- For production-grade deployments create Helm charts or Kustomize overlays and configure resource requests/limits, probes, and RBAC.
