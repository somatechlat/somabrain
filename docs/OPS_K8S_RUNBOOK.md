> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

## SomaBrain Kubernetes Operations Runbook

This runbook documents the cluster-level changes applied to the `k8s/full-stack.yaml` manifest and how to operate, harden, and keep the full infra running reliably for development and staging/production parity.

Scope
- Postgres StatefulSet + Service
- Migration `Job` to run Alembic migrations before app startup
- Somabrain Deployment changes: init containers (wait-for-postgres, copy-code, apply-overrides), mounted overrides `ConfigMap`
- Secrets wiring (DB creds in `somabrain-postgres` and app `somabrain-secrets`)

Component map (as shipped in `k8s/full-stack.yaml`)

| Component        | Workload        | Service name     | Ports (container → svc) | External Access | Notes |
|------------------|-----------------|------------------|-------------------------|-----------------|-------|
| Somabrain API    | `Deployment`    | `somabrain`      | 9696 → 9696             | Internal only   | Primary API traffic |
| Somabrain Public | — (shares pods) | `somabrain-public` | 9696 → 9999           | LoadBalancer    | Production external access |
| Somabrain Test   | — (shares pods) | `somabrain-test` | 9696 → 9696             | Internal only   | Alternate service for learning/tests |
| Nginx Ingress    | `Deployment`    | `ingress-nginx-controller` | 80/443 → 80/443 | LoadBalancer | HTTPS termination, routing |
| Redis cache      | `Deployment`    | `sb-redis`       | 6379 → 6379             | Internal only   | Cache + coordination |
| OPA policy       | `Deployment`    | `sb-opa`         | 8181 → 8181             | Internal only   | Optional policy checks |
| Postgres         | `StatefulSet`   | `postgres`       | 5432 → 5432             | Internal only   | Feedback/token persistence |

All objects live in namespace `somabrain-prod` by default; adjust manifests or use `kubectl -n <ns>` overrides for other environments.

Goals
- Make the production-like stack (API on port 9696) self-healing and deterministic.
- Ensure migrations are applied automatically before the API starts.
- Provide a documented, repeatable path to build/push images and make changes permanent via CI/CD.

What I changed
- Added a `postgres` `Service` + `StatefulSet` (Postgres 15) with a PVC and readiness/liveness probes.
- Created `somabrain-postgres` secret for DB credentials and updated `somabrain-secrets` DSNs to point at `postgres.somabrain-prod.svc.cluster.local`.
- Added a `job.batch/somabrain-migrate` Job that waits for Postgres, clones the repo, installs deps, and runs `alembic upgrade head`.
- Somabrain `Deployment` now includes:
  - `wait-for-postgres` init container that blocks startup until DB is reachable.
  - `copy-code` init container that clones the repo into an emptyDir (still used for rapid iteration).
  - `apply-overrides` init container that copies files from a `ConfigMap` named `somabrain-overrides` into the app tree (used to hot-fix or stage local changes without rebuilding images).
  - env references to `somabrain-postgres` secret so runtime has DB credentials.
- Added `somabrain-overrides` `ConfigMap` to carry local code patches (for emergency fixes / staged overrides).

Ingress & TLS provisioning
- Run `scripts/setup_ingress_tls.sh` to provision the `somabrain-tls` secret (Let's Encrypt via cert-manager) and apply ingress resources.
- Validate DNS resolution: `dig somabrain.internal` should point at the ingress IP (or `/etc/hosts` entry for local).
- Test TLS handshake: `curl -sk --resolve somabrain.internal:9999:127.0.0.1 https://somabrain.internal:9999/health`.
- Inspect ingress status: `kubectl -n ingress-nginx get ingress somabrain-ingress -o wide`.

How to make these changes permanent (recommended workflow)
1. Build and publish a production image (CI):

   - Build a tagged, immutable image in CI (or locally for dev):

     docker build -t registry.example.com/somatechlat/somabrain:stable-YYYYMMDD .
     docker push registry.example.com/somatechlat/somabrain:stable-YYYYMMDD

   - Replace the `image: python:3.13-slim` recipe in `k8s/full-stack.yaml` with the published image and remove `pip install -e .` from runtime container (build-time install ensures deterministic runtime).

2. Convert repo-cloning init containers to an image-layer approach:

   - Keep `copy-code` for quick dev cycles, but for production use the built image and remove heavy init steps that clone/install at runtime.

3. Promote DB to managed / operator-backed Postgres for production:

   - Use Bitnami Helm chart or a Postgres operator for HA, backups, and credential rotation.

4. Replace overrides with a controlled release process:

   - Use the overrides `ConfigMap` only for emergency hotfixes. Long-term, make changes in branch -> CI -> image promotion pipeline.

5. Add Helm or Kustomize overlays:

   - Create overlays for `dev`, `staging`, and `prod` (resource sizes, replica counts, and RBAC differ). Deploy via CI/CD (e.g., GitHub Actions -> kubectl apply or Helm upgrade).

Verification & daily checks
- After deployment or a rollout:
  1. Wait for `somabrain-migrate` Job to complete: `kubectl -n somabrain-prod wait --for=condition=complete job/somabrain-migrate --timeout=300s`.
  2. Confirm Postgres readiness: `kubectl -n somabrain-prod get sts/postgres` and `kubectl -n somabrain-prod exec sts/postgres-0 -- pg_isready -U $POSTGRES_USER`.
  3. Check somabrain pods: `kubectl -n somabrain-prod get pods -l app=somabrain` and `kubectl -n somabrain-prod logs deploy/somabrain --tail=200`.
4. Port-forward for local test access (API 9696, Redis 6379, Postgres 55432) and run prechecks.

Running the learning test locally (host)
1. Forward ports from the cluster to your host (recommended):

```bash
# Example, run in separate shells (or use the background/nohup pattern in docs):
./scripts/port_forward_api.sh &
kubectl -n somabrain-prod port-forward svc/somabrain-test 9696:9696 &
kubectl -n somabrain-prod port-forward svc/sb-redis 6379:6379 &
kubectl -n somabrain-prod port-forward svc/postgres 55432:5432 &
```

2. Confirm health endpoints:

```bash
curl -s http://127.0.0.1:9696/health | jq
curl -s http://127.0.0.1:9696/health | jq  # via somabrain-test service
```

3. Run the cognition learning suite (from repo root using your venv):

```bash
export SOMA_API_URL=http://127.0.0.1:9696
export SOMABRAIN_REDIS_URL=redis://127.0.0.1:6379/0
export SOMABRAIN_POSTGRES_LOCAL_PORT=55432
.venv/bin/pytest -vv tests/test_cognition_learning.py
```

Notes on the adaptation endpoint
- The adaptation state endpoint is defined at `/context/adaptation/state` and requires the router to be imported at startup. If you see `404 Not Found` for that endpoint while `/context/evaluate` exists, it means the `context_route` module was loaded from a different file that doesn't include the adaptation endpoint, or the router registration was skipped due to an import-time exception. Review pod logs for traceback during startup and ensure no syntax errors exist in `context_route.py` mounted via `somabrain-overrides`.

Rollback & safety
- If something regresses, roll back the deployment:

```bash
kubectl -n somabrain-prod rollout undo deployment/somabrain
kubectl -n somabrain-prod delete job/somabrain-migrate --ignore-not-found
```

Follow-ups (recommended)
1. Replace runtime repo cloning with built images and remove `pip install -e .` from runtime containers.
2. Add a simple GitHub Actions workflow to: build image, run migrations (job), and `kubectl apply` to the cluster for each promoted tag.
3. Create Kustomize overlays and a Helm chart for safe environment-specific overrides.

If you'd like, I can now update the repository docs to point to this runbook and create the CI skeleton for image promotion and automatic deployments. Also I can run the learning pytest now and report results — say the word and I'll run it next (it will target the forwarded local port 9696 by default).
