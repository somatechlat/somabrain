# Vault server configuration — standalone stack.
#
# Production-shaped on purpose:
#   * `file` storage on a named volume, so secrets SURVIVE a container restart.
#     Dev mode keeps them in memory and loses every credential on restart,
#     which is not a deployment, it is a lottery.
#   * Real seal. The stack starts sealed and is unsealed by vault_unseal.py
#     using a key the operator holds in the OS keychain / KMS
#     (SOMA-STD-BOOTSTRAP-001 §2.3) — never a file in this repo. Production
#     replaces that key with auto-unseal against a cloud KMS; the shape is the
#     same, only the key custodian moves.
#
# TLS is disabled here because the listener is container-internal on a
# compose network. Production terminates TLS at the listener.

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

# Deliberately no api_addr / cluster_addr. Vault derives both from the request
# and from the listener; on a single-node stack the defaults are correct and
# pinning them to 0.0.0.0 only invites a second bind. The one thing that does
# break this file is loading it twice — see the `entrypoint` note in
# docker-compose.yml.

# mlock needs IPC_LOCK and buys nothing on a single-node laptop stack.
disable_mlock = true

ui = true

# F-16 audit device (SOMA-STD-BOOTSTRAP-001 §3.5).
#
# Vault OSS does NOT load audit devices from server config — this stanza is
# the named declaration of the device and its path. The live device is enabled
# after unseal by vault_unseal.py via `sys/audit/file` (idempotent).
#
# Path is on the dedicated `somabrain_standalone_vault_audit` named volume,
# never inside /vault/data and never in the repo. Contents are HMAC-SHA256
# under a per-device salt: plaintext secrets never enter this file. That is
# the designed exception to R-SEC-01 documented in §2.1 of the bootstrap
# standard.
audit "file" {
  path = "/vault/audit/vault-audit.log"
}
