# Vault server configuration — standalone stack.
#
# Production-shaped on purpose:
#   * `file` storage on a named volume, so secrets SURVIVE a container restart.
#     Dev mode keeps them in memory and loses every credential on restart,
#     which is not a deployment, it is a lottery.
#   * Real seal. The stack starts sealed and is unsealed by vault_unseal.py
#     using a key the deployer holds in ./secrets/, exactly like every other
#     credential in this stack. Production replaces that key with auto-unseal
#     against a cloud KMS; the shape is the same, only the key custodian moves.
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
