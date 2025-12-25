#!/usr/bin/env bash
# Generate a local TLS certificate for somabrain.internal and install it in the cluster.
# This is intended for bootstrap/dev only. For production plug in your real certificate
# material before invoking the script.
set -euo pipefail

NAMESPACE=${NAMESPACE:-somabrain-prod}
SERVICE_HOST=${SERVICE_HOST:-somabrain.internal}
CERT_DIR=${CERT_DIR:-$(cd "$(dirname "$0")/.." && pwd)/infra/tls}
CERT_PATH="${CERT_DIR}/${SERVICE_HOST}.crt"
KEY_PATH="${CERT_DIR}/${SERVICE_HOST}.key"
DAYS_VALID=${DAYS_VALID:-365}

mkdir -p "${CERT_DIR}"

if [[ ! -s "${KEY_PATH}" || ! -s "${CERT_PATH}" ]]; then
  echo "[setup-ingress-tls] Generating self-signed cert for ${SERVICE_HOST} valid ${DAYS_VALID} days" >&2
  openssl req -x509 -nodes -newkey rsa:4096 \
    -keyout "${KEY_PATH}" \
    -out "${CERT_PATH}" \
    -days "${DAYS_VALID}" \
    -subj "/CN=${SERVICE_HOST}" \
    -addext "subjectAltName=DNS:${SERVICE_HOST}" >&2
else
  echo "[setup-ingress-tls] Re-using existing certificate at ${CERT_PATH}" >&2
fi

kubectl -n "${NAMESPACE}" create secret tls somabrain-tls \
  --cert="${CERT_PATH}" \
  --key="${KEY_PATH}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[setup-ingress-tls] TLS secret somabrain-tls applied to namespace ${NAMESPACE}" >&2

echo "Next steps:" >&2
echo "  1. Trust ${CERT_PATH} on your workstation (e.g. with Keychain Access or certutil)." >&2
echo "  2. Add '${SERVICE_HOST} 127.0.0.1' to /etc/hosts when using port-forward." >&2
