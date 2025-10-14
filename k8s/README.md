> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

Kubernetes full-stack run instructions (dev/staging parity)

These steps mirror `k8s/full-stack.yaml`, which targets the `somabrain-prod` namespace by default. Adjust the namespace if you are testing in a sandbox (e.g. `somabrain-dev`).

1) Create a local cluster (kind example):

```bash
# create kind cluster
kind create cluster --name somabrain

# build somabrain image locally and load into kind (optional for local overrides)
docker build -t somatechlat/somabrain:dev .
kind load docker-image somatechlat/somabrain:dev --name somabrain

# optional: pre-build other service images and load them if you customize manifests
```

2) Apply the manifests:

```bash
kubectl apply -f k8s/full-stack.yaml

# verify namespace and pods
kubectl get pods -n somabrain-prod
kubectl get svc -n somabrain-prod
```

3) Make Somabrain and other services reachable from your host for tests:

Option A (port-forward, recommended for parity with CI and strict-real tests):

```bash
kubectl -n somabrain-prod port-forward svc/somabrain 9696:9696 &
kubectl -n somabrain-prod port-forward svc/somabrain-test 9696:9696 &
kubectl -n somabrain-prod port-forward svc/sb-redis 6379:6379 &
kubectl -n somabrain-prod port-forward svc/postgres 55432:5432 &
kubectl -n somabrain-prod port-forward svc/sb-opa 8181:8181 &

# or run helper script for the main API tunnel
./scripts/port_forward_api.sh &
```

4) Run prechecks and tests from `.venv`:

```bash
# run precheck (ensure your venv has kafka-python, redis and requests)
python scripts/sb_precheck.py

# run integration tests (example)
SOMABRAIN_KAFKA_URL=kafka://localhost:9092 \
SOMABRAIN_OPA_URL=http://localhost:8181 \
SOMABRAIN_REDIS_URL=redis://localhost:6379/0 \
python -m pytest -m integration -q -r a --maxfail=5
```

Notes:
- For Kafka in Kubernetes use Strimzi or Redpanda operator; the full-stack manifest assumes operator-managed brokers or an external bootstrap URL.
- If you run tests from host, prefer port-forward per-service so the host `scripts/sb_precheck.py` can reach the services at `localhost`.
- For production-grade deployments create Helm charts or Kustomize overlays and configure resource requests/limits, probes, and RBAC.
