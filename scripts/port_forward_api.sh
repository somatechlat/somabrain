#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC2034
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NAMESPACE="${SOMABRAIN_NAMESPACE:-somabrain-prod}"
SERVICE_NAME="${SOMABRAIN_SERVICE:-somabrain}"
LOCAL_PORT="${SOMABRAIN_PORT:-9696}"
REMOTE_PORT="${SOMABRAIN_REMOTE_PORT:-9696}"
WAIT_SECONDS="${SOMABRAIN_FORWARD_WAIT:-2}"

usage() {
  cat <<"EOF"
Usage: port_forward_api.sh [--namespace <ns>] [--service <svc>] [--local-port <port>] [--remote-port <port>]

Environment overrides:
  SOMABRAIN_NAMESPACE       Namespace (default: somabrain-prod)
  SOMABRAIN_SERVICE         Service name (default: somabrain)
  SOMABRAIN_PORT            Local listen port (default: 9696)
  SOMABRAIN_REMOTE_PORT     Remote service port (default: 9696)
  SOMABRAIN_FORWARD_WAIT    Seconds to allow the tunnel to establish (default: 2)

The script will ensure no duplicate port-forward is running, then start a new
kubectl port-forward session that stays attached until interrupted. Use Ctrl+C
or send SIGINT/SIGTERM to stop the tunnel.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace|-n)
      NAMESPACE="$2"
      shift 2
      ;;
    --service|-s)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --local-port|-l)
      LOCAL_PORT="$2"
      shift 2
      ;;
    --remote-port|-r)
      REMOTE_PORT="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found in PATH" >&2
  exit 1
fi

if ! kubectl version --client >/dev/null 2>&1; then
  echo "Failed to execute kubectl; ensure your kubeconfig is configured" >&2
  exit 1
fi

PF_PATTERN="kubectl -n ${NAMESPACE} port-forward svc/${SERVICE_NAME} ${LOCAL_PORT}:${REMOTE_PORT}"
if pkill -f "${PF_PATTERN}" >/dev/null 2>&1; then
  echo "Stopped existing port-forward: ${PF_PATTERN}" >&2
fi

if lsof -i:"${LOCAL_PORT}" >/dev/null 2>&1; then
  echo "Local port ${LOCAL_PORT} is already in use. Please free it and retry." >&2
  exit 1
fi

kubectl -n "${NAMESPACE}" port-forward "svc/${SERVICE_NAME}" "${LOCAL_PORT}:${REMOTE_PORT}" &
PF_PID=$!

cleanup() {
  if kill -0 "${PF_PID}" >/dev/null 2>&1; then
    kill "${PF_PID}" >/dev/null 2>&1 || true
    wait "${PF_PID}" >/dev/null 2>&1 || true
    echo "Stopped port-forward (PID ${PF_PID})."
  fi
}

trap cleanup INT TERM EXIT

sleep "${WAIT_SECONDS}"

if ! kill -0 "${PF_PID}" >/dev/null 2>&1; then
  echo "Port-forward process exited early" >&2
  wait "${PF_PID}"
  exit 1
fi

echo "Forwarding svc/${SERVICE_NAME} in namespace ${NAMESPACE} on localhost:${LOCAL_PORT} -> ${REMOTE_PORT}."
echo "Press Ctrl+C to stop."

wait "${PF_PID}"
