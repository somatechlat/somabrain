> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

<!--
SomaStack Shared Infra Agent Onboarding Guide
Audience: coding agents (Codex/Copilot) responsible for deploying application services into the Soma shared infrastructure.
Goal: provide deterministic, automation-friendly steps from environment setup to production promotion, including explicit commands, guardrails, and diagrams.
-->

# SomaStack Shared Infra — Agent Deployment Playbook

> **Scope**: This is the canonical manual for any automation agent (Codex, Copilot, GitOps bots) that needs to deploy workloads into the Soma shared infrastructure. It assumes no human intuition and documents every prerequisite, command, and validation step.

---

## 0. Cluster Reset Checklist

**Run before every fresh deployment to guarantee a clean slate.**

```sh
# Remove previous shared infra release (if present)
helm uninstall sharedinfra -n soma-infra || true

# Delete namespace to purge PVCs, secrets, CRDs
kubectl delete namespace soma-infra --wait=false || true
kubectl wait --for=delete ns/soma-infra --timeout=120s || true

# Ensure namespace is gone
kubectl get namespaces
```

If `soma-infra` still appears as `Terminating`, delete blocking finalizers:

```sh
kubectl get namespace soma-infra -o json | jq '.spec.finalizers=[]' | \
  kubectl replace --raw /api/v1/namespaces/soma-infra/finalize -f -
```

Wait until `kubectl get ns` shows no `soma-infra` entry before continuing.

---

## 1. Environment Bootstrap

### 1.1 Toolchain Versions

```yaml
tools:
  kubectl: ">=1.28"
  helm: ">=3.13"
  kind: ">=0.22"
  docker: ">=24.0"
  jq: ">=1.6"
```

Agents must validate binaries:

```sh
kubectl version --client
helm version
kind version
docker version
jq --version
```

### 1.2 Kind Cluster Provisioning

```sh
kind delete cluster --name soma || true
kind create cluster --name soma --config infra/kind/soma-kind.yaml
kubectl config use-context kind-soma
```

Verify capacity:

```sh
kubectl describe node soma-control-plane | grep -E "Allocatable|cpu|memory"
```

### 1.3 Preload Critical Images

```sh
for img in \
  bitnamicharts/postgresql-repmgr:17.6.0-debian-12-r2 \
  bitnamicharts/pgpool:4.6.3-debian-12-r0 \
  apache/kafka:3.8.0 \
  redis:7.2.4-alpine \
  hashicorp/vault:1.15.4 \
  openpolicyagent/opa:0.57.0-debug \
  prom/prometheus:v2.47.2 \
  grafana/grafana:10.2.3
do
  docker pull "$img"
  kind load docker-image "$img" --name soma
done
```

`docker pull` resolves `bitnamicharts/*` via Docker Hub automatically; Kind stores the same tag internally. If your environment requires the fully-qualified path, substitute `registry-1.docker.io/bitnamicharts/...` in both commands.

---

## 2. Shared Infra Deployment

### 2.1 Helm Dependencies

```sh
helm dependency update infra/helm/soma-infra
```

### 2.2 Namespace Creation

```sh
kubectl create namespace soma-infra
```

### 2.3 Base Install (Dev Mode Example)

```sh
helm upgrade --install sharedinfra infra/helm/soma-infra \
  -n soma-infra \
  -f infra/helm/soma-infra/values-dev.yaml \
  --wait --timeout 5m
```

### 2.4 Post-Install Verification

```sh
kubectl get pods -n soma-infra
kubectl wait --for=condition=ready pod --all -n soma-infra --timeout=180s
helm status sharedinfra -n soma-infra
```

**Postgres HA check**:

```sh
kubectl exec -n soma-infra sts/sharedinfra-postgres-postgresql -- repmgr cluster show
kubectl get deployment sharedinfra-postgres-pgpool -n soma-infra -o jsonpath='{.status.readyReplicas}/{.spec.replicas}'
```

If any pod reports `ImagePullBackOff`, confirm `registry-1.docker.io` reachability and that `global.security.allowInsecureImages=true` is present in the rendered values.

### 2.5 Overlay Matrix

| Mode | Values File | Characteristics |
|------|-------------|-----------------|
| dev | `values-dev.yaml` | Single Postgres replica, persistence on, Vault dev server. |
| test | `values-test.yaml` | Ephemeral services, persistence off, Grafana/Auth disabled. |
| staging | `values-staging.yaml` | Prod-like Vault TLS, Kafka=3, Postgres=1. |
| prod-lite | `values-prod-lite.yaml` | Premium storage, scaled-down prod footprint. |
| prod | `values-prod.yaml` | HA Postgres (3+2), Vault raft cluster, premium storage. |

Select the overlay by adding `-f infra/helm/soma-infra/values-<mode>.yaml` to the Helm command. Always run a readiness wait afterward.

### 2.6 Architecture Snapshot

```mermaid
flowchart LR
  subgraph SharedInfra[Shared Infra Namespace]
    PG[(Postgres HA)]
    PP[(Pgpool)]
    RED[(Redis)]
    KAF[(Kafka KRaft)]
    VAULT[(Vault Raft)]
    OPA[(OPA)]
    AUTH[(OpenFGA)]
    PROM[(Prometheus)]
    GRAF[(Grafana)]
  end
  subgraph Apps[Application Namespaces]
    SA01
    SBR
    SAH
    SFM
    Custom
  end
  Apps -->|DB| PP --> PG
  Apps -->|Cache| RED
  Apps -->|Events| KAF
  Apps -->|Policy| OPA
  Apps -->|Secrets| VAULT
  Apps -->|Metrics| PROM
```

---

## 3. Application Wire-Up Workflow

### 3.1 Namespace Labeling

```sh
APP_NS="sa01"
kubectl create namespace "$APP_NS" || true
kubectl label namespace "$APP_NS" soma.sh/allow-shared-infra="true" --overwrite
```

### 3.2 Vault Role + Policy Automation

```sh
cat <<'HCL' > policies/${APP_NS}.hcl
path "secret/data/shared-infra/${APP_NS}/*" {
  capabilities = ["read"]
}
path "secret/metadata/shared-infra/${APP_NS}/*" {
  capabilities = ["list", "read"]
}
HCL

vault policy write ${APP_NS} policies/${APP_NS}.hcl
vault write auth/kubernetes/role/${APP_NS} \
  bound_service_account_names=${APP_NS}-sa \
  bound_service_account_namespaces=${APP_NS} \
  policies=${APP_NS} \
  ttl=24h
```

### 3.3 ExternalSecret Template

Export the environment slug (`ENV=dev|staging|prod`) before applying manifests:

```sh
export ENV=dev
```

Create `infra/external-secrets/${APP_NS}-externalsecret.yaml`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ${APP_NS}-secrets
  namespace: ${APP_NS}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: soma-infra-vault
    kind: ClusterSecretStore
  target:
    name: ${APP_NS}-runtime
    template:
      type: Opaque
  data:
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: secret/data/shared-infra/${APP_NS}/${ENV}
        property: postgres_password
    - secretKey: REDIS_PASSWORD
      remoteRef:
        key: secret/data/shared-infra/${APP_NS}/${ENV}
        property: redis_password
    - secretKey: KAFKA_SASL_PASSWORD
      remoteRef:
        key: secret/data/shared-infra/${APP_NS}/${ENV}
        property: kafka_sasl_password
    - secretKey: POSTGRES_DSN
      remoteRef:
        key: secret/data/shared-infra/${APP_NS}/${ENV}
        property: postgres_dsn
```

Apply and verify:

```sh
kubectl apply -f infra/external-secrets/${APP_NS}-externalsecret.yaml
kubectl describe externalsecret ${APP_NS}-secrets -n ${APP_NS}
```

### 3.4 ConfigMap Contract

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${APP_NS}-settings
  namespace: ${APP_NS}
data:
  POSTGRES_HOST: "sharedinfra-postgres-pgpool.soma-infra.svc.cluster.local"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "somaagent01"
  POSTGRES_USER: "soma"
  REDIS_URL: "redis://sharedinfra-redis-master.soma-infra.svc.cluster.local:6379/0"
  KAFKA_BOOTSTRAP_SERVERS: "sharedinfra-kafka.soma-infra.svc.cluster.local:9092"
  OPA_URL: "http://sharedinfra-opa.soma-infra.svc.cluster.local:8181/v1/data"
  VAULT_ADDR: "https://sharedinfra-vault.soma-infra.svc.cluster.local:8200"
  VAULT_ROLE: "${APP_NS}"
```

### 3.5 Deployment Skeleton (Helm)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "service.name" . }}
  namespace: {{ .Release.Namespace }}
spec:
  replicas: {{ .Values.replicas | default 2 }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "service.name" . }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include "service.name" . }}
    spec:
      serviceAccountName: {{ .Values.serviceAccount.name }}
      containers:
        - name: app
          image: {{ printf "%s:%s" .Values.image.repository .Values.image.tag | quote }}
          envFrom:
            - secretRef:
                name: {{ .Values.secretsRef | default (printf "%s-runtime" (include "service.name" .)) }}
            - configMapRef:
                name: {{ include "service.name" . }}-settings
          env:
            - name: POSTGRES_DSN
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.secretsRef | default (printf "%s-runtime" (include "service.name" .)) }}
                  key: POSTGRES_DSN
          resources: {{- toYaml .Values.resources | nindent 12 }}
```

### 3.6 Database Provisioning

```sh
ADMIN_PASS=$(kubectl get secret sharedinfra-postgres-admin -n soma-infra -o jsonpath='{.data.password}' | base64 -d)
kubectl run psql-client -n soma-infra --rm -it --image=postgres:16-alpine --restart=Never -- \
  psql "postgresql://admin:${ADMIN_PASS}@sharedinfra-postgres-pgpool:5432/postgres" <<'SQL'
CREATE DATABASE ${APP_NS} OWNER soma;
GRANT ALL ON DATABASE ${APP_NS} TO soma;
SQL
```

### 3.7 Kafka Topic Setup

```sh
kubectl exec -n soma-infra sts/sharedinfra-kafka -- \
  kafka-topics.sh --bootstrap-server sharedinfra-kafka:9092 \
  --create --if-not-exists --topic ${APP_NS}.events \
  --partitions 6 --replication-factor 1 --config retention.ms=259200000
```

Adjust replication factor to 3 in staging/prod overlays.

---

## 4. Continuous Deployment Pipeline

### 4.1 GitHub Actions Blueprint

```yaml
name: deploy-${{ env.SERVICE }}

on:
  push:
    branches: [ main ]
    paths:
      - "services/${{ env.SERVICE }}/**"
      - ".github/workflows/deploy-${{ env.SERVICE }}.yml"

env:
  SERVICE: sa01
  NAMESPACE: sa01

jobs:
  build-deploy:
    runs-on: ubuntu-22.04
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - name: Setup helm & kubectl
        uses: azure/setup-kubectl@v4
      - name: Build image
        run: |
          docker build -t ghcr.io/somatech/${SERVICE}:${GITHUB_SHA} services/${SERVICE}
          echo "IMAGE=ghcr.io/somatech/${SERVICE}:${GITHUB_SHA}" >> $GITHUB_ENV
      - name: Push image
        run: |
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
          docker push "$IMAGE"
      - name: Deploy via Helm
        run: |
          helm upgrade --install ${SERVICE} charts/${SERVICE} \
            -n ${NAMESPACE} --create-namespace \
            --set image.repository=ghcr.io/somatech/${SERVICE} \
            --set image.tag=${GITHUB_SHA}
      - name: Readiness gate
        run: |
          kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=${SERVICE} -n ${NAMESPACE} --timeout=180s
```

### 4.2 Promotion Diagram

```mermaid
flowchart LR
  Commit --> Build --> Dev --> Staging --> Prod
  Build --> Dev
  Dev -->|smoke (45s)| Staging -->|chaos + soak| Prod
```

Enforce identical readiness checks across environments for deterministic rollouts.

---

## 5. Verification Matrix

| Layer | Command | Success Criteria |
|-------|---------|------------------|
| Namespace | `kubectl get ns ${APP_NS}` | Status `Active`, label `soma.sh/allow-shared-infra=true`. |
| Secrets | `kubectl get secret ${APP_NS}-runtime -n ${APP_NS}` | Contains base64 keys `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, etc. |
| Pods | `kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=${APP_NS} -n ${APP_NS} --timeout=180s` | All pods ready. |
| Database | `kubectl exec deploy/${APP_NS} -n ${APP_NS} -- pg_isready -d "$POSTGRES_DSN"` | Returns `accepting connections`. |
| Kafka | `kubectl exec deploy/${APP_NS} -n ${APP_NS} -- kafka-metadata-shell --command "describeTopic --topic ${APP_NS}.events"` | Topic metadata returned. |
| Redis | `kubectl exec deploy/${APP_NS} -n ${APP_NS} -- redis-cli -h sharedinfra-redis-master.soma-infra.svc.cluster.local ping` | `PONG`. |
| Vault | `kubectl exec deploy/${APP_NS} -n ${APP_NS} -- vault token lookup` | Token data with positive TTL. |

Log all failures with `kubectl logs` and attach to incident reports.

---

## 6. Troubleshooting Runbook

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `ImagePullBackOff` for Postgres | Missing registry override or network block to `registry-1.docker.io`. | Confirm values include `registry-1.docker.io/bitnamicharts/*`, preload images, ensure `global.security.allowInsecureImages=true`. |
| Helm upgrade fails on PVC resize | Existing volumes smaller than desired. | Delete namespace (Section 0) or adjust request size upwards only (never downscale). |
| Kafka topic errors | Broker not ready or missing cluster ID. | Wait for `sharedinfra-kafka-0` ready, re-run topic create. |
| Vault auth failure | ServiceAccount mismatch or policy missing. | Verify Vault role bound to correct SA/namespace, reapply policy. |
| Readiness gate timeout | Resource constraints or misconfigured env vars. | Check pod logs, describe pod for events, adjust resources or secrets. |

---

## 7. Operational Policies

- **No Mocking**: All services use real dependencies. Do not stub Postgres or Kafka.
- **Restart Resilience**: After deployment, run `helm test sharedinfra -n soma-infra` (if tests defined) and `kubectl rollout restart` for each workload to confirm restart safety.
- **Drift Detection**: Nightly job should diff `helm get manifest` against Git to detect manual drift.
- **Access Control**: Only namespaces labeled with `soma.sh/allow-shared-infra=true` may connect to shared services; network policies enforce this.

---

## 8. Appendix — Automation Snippets

### 8.1 Mode Switch Script

```sh
MODE=${1:-dev}
helm upgrade --install sharedinfra infra/helm/soma-infra \
  -n soma-infra \
  -f infra/helm/soma-infra/values.yaml \
  -f infra/helm/soma-infra/values-${MODE}.yaml \
  --wait --timeout 5m
```

### 8.2 Health Snapshot Script

```sh
kubectl get pods -n soma-infra -o wide
echo "Postgres:" && kubectl exec -n soma-infra sts/sharedinfra-postgres-postgresql -- repmgr cluster show || true
echo "Kafka:" && kubectl exec -n soma-infra sts/sharedinfra-kafka -- kafka-get-offsets.sh --bootstrap-server sharedinfra-kafka:9092 --topic __consumer_offsets || true
```

### 8.3 Incident Bundle Collector

```sh
mkdir -p /tmp/sharedinfra-debug
kubectl cluster-info dump --namespaces soma-infra > /tmp/sharedinfra-debug/cluster-dump.json
kubectl logs -n soma-infra -l app.kubernetes.io/name=postgres > /tmp/sharedinfra-debug/postgres.log
kubectl get events -n soma-infra --sort-by='.lastTimestamp' > /tmp/sharedinfra-debug/events.txt
```

---

## 9. ASCII Quick Reference

```
[Reset] -> helm uninstall sharedinfra -> kubectl delete ns soma-infra
[Cluster] -> kind create cluster --config infra/kind/soma-kind.yaml
[Images] -> docker pull + kind load registry-1.docker.io/bitnamicharts/*
[Deploy] -> helm upgrade --install sharedinfra ... --wait
[Verify] -> kubectl wait pods, repmgr cluster show, helm status
[App Prep] -> create namespace, Vault policy, ExternalSecret, ConfigMap
[Deploy App] -> helm upgrade --install service chart; readiness gate
[Operate] -> metrics, alerts, incident bundle
```

---

## 10. Change Management

- Update this guide whenever chart versions, registry locations, or onboarding policies change.
- Store agent automation scripts under `scripts/agents/` and reference this playbook for consistency.
- Pull requests touching shared infra must run `make deploy-kind-full MODE=dev` in CI and attach readiness logs.

Follow these instructions exactly to ensure deterministic, restart-resistant deployments into the Soma shared infrastructure.
