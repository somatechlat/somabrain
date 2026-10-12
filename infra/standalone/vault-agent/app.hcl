# Vault Agent — application sidecar (SOMA-STD-BOOTSTRAP-001 / R-SEC-01).
#
# Auto-auth via AppRole. The authenticated token is sunk to a tmpfs file that
# VAULT_TOKEN_FILE points at — a scoped, auto-renewed service token, never the
# root token and never an env value. somabrain/core/security/vault_client.py
# then resolves individual secrets (database, jwt, runtime, shared agent token)
# from Vault over the API with least privilege.

vault {
  # Address comes from VAULT_ADDR (topology). Never hardcoded here (Rule 91).
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path     = "/run/approle/app/role_id"
      secret_id_file_path   = "/run/approle/app/secret_id"
      remove_secret_id_file = false
    }
  }

  sink "file" {
    config = {
      path = "/run/vault/token"
    }
  }
}

# Optional rendered copy of the shared memory token for health probes that
# must not hold a Vault client. Whitespace is load-bearing.
template {
  contents = "{{ with secret \"secret/data/agent/credentials\" }}{{ .Data.data.somabrain_memory_http_token }}{{ end }}"
  destination = "/run/vault/somabrain_memory_http_token"
  perms       = 0600
  error_on_missing_key = true
}
