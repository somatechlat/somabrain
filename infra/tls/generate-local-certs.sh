#!/usr/bin/env bash
# Generate self-signed TLS certificates for local SomaBrain development.
# The generated .crt/.key files are ignored by git and must never be committed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_NAME="${CERT_NAME:-somabrain.internal}"
DAYS="${CERT_DAYS:-365}"
KEY_FILE="${SCRIPT_DIR}/${CERT_NAME}.key"
CRT_FILE="${SCRIPT_DIR}/${CERT_NAME}.crt"

if [ -f "${KEY_FILE}" ] || [ -f "${CRT_FILE}" ]; then
  echo "Certificate files already exist:"
  ls -la "${KEY_FILE}" "${CRT_FILE}" 2>/dev/null || true
  echo "Remove them first if you want to regenerate."
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required to generate local certificates." >&2
  exit 1
fi

openssl req -x509 -nodes -days "${DAYS}" -newkey rsa:2048 \
  -keyout "${KEY_FILE}" \
  -out "${CRT_FILE}" \
  -subj "/CN=${CERT_NAME}/O=SomaBrain Local Development" \
  -addext "subjectAltName=DNS:${CERT_NAME},DNS:localhost,IP:127.0.0.1"

chmod 600 "${KEY_FILE}"
chmod 644 "${CRT_FILE}"

echo "Generated local self-signed certificate:"
echo "  ${KEY_FILE}"
echo "  ${CRT_FILE}"
