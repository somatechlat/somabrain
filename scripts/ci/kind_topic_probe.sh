#!/usr/bin/env bash
set -euo pipefail

# Kind cluster topic probe for Sprint 0 acceptance
# Creates a kind cluster, deploys single-node Kafka and runs a topic creation + probe.
# Requires: kind, kubectl.

NS="somabrain-prod"
TOPICS=("cog.global.frame" "cog.segments")

log() { echo "[probe] $*"; }

if ! command -v kind >/dev/null 2>&1; then
  log "kind not installed"; exit 1
fi
if ! command -v kubectl >/dev/null 2>&1; then
  log "kubectl not installed"; exit 1
fi

log "Creating kind cluster (if absent)"
kind get clusters | grep -qx "somabrain-ci" || kind create cluster --name somabrain-ci --wait 60s

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS"

log "Applying Kafka manifest"
kubectl apply -n "$NS" -f infra/k8s/kafka-single.yaml

log "Waiting for Kafka readiness"
kubectl wait --for=condition=Ready pod -l app=somabrain-kafka -n "$NS" --timeout=180s

POD=$(kubectl get pods -n "$NS" -l app=somabrain-kafka -o jsonpath='{.items[0].metadata.name}')

create_topic() {
  local t="$1"
  kubectl exec -n "$NS" "$POD" -- bash -c "/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic $t --partitions 1 --replication-factor 1" || true
}

for t in "${TOPICS[@]}"; do
  log "Ensuring topic $t"
  create_topic "$t"
done

log "Listing topics"
ALL=$(kubectl exec -n "$NS" "$POD" -- bash -c "/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list" || true)

echo "$ALL"

for t in "${TOPICS[@]}"; do
  echo "$ALL" | grep -qx "$t" || { log "Missing required topic $t"; exit 1; }
  log "Verified topic $t"
done

log "Kind topic probe succeeded"
