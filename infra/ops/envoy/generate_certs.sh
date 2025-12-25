#!/bin/bash
# Generate example CA, server, and client certs for Envoy mTLS demo
# Usage: ./generate_certs.sh
set -euo pipefail

CERTS_DIR="$(dirname "$0")/certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# 1. Generate CA key and cert
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt -subj "/CN=somabrain-ca"

# 2. Generate server key and CSR
openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr -subj "/CN=envoy.somabrain"

# 3. Sign server cert with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650 -sha256

# 4. Generate client key and CSR
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -subj "/CN=client.somabrain"

# 5. Sign client cert with CA
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 3650 -sha256

# 6. Cleanup
rm -f *.csr *.srl

echo "Certificates generated in $CERTS_DIR:"
echo "  ca.crt, ca.key, server.crt, server.key, client.crt, client.key"
