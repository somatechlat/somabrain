# Vault Agent — postgres sidecar (SOMA-STD-BOOTSTRAP-001 / R-SEC-01).
#
# Auto-auth via AppRole (industry pattern for services). role_id is an
# identifier, not a secret; secret_id is pulled from the isolated tmpfs
# bootstrap dir written once by init_vault.py. The Postgres password is
# rendered onto a tmpfs volume and consumed via POSTGRES_PASSWORD_FILE.
# Nothing is ever written to disk, argv, or the process environment.

vault {
  # Address comes from VAULT_ADDR (topology). Never hardcoded here (Rule 91).
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path     = "/run/approle/postgres/role_id"
      secret_id_file_path   = "/run/approle/postgres/secret_id"
      remove_secret_id_file = false
    }
  }

  sink "file" {
    config = {
      path = "/run/secrets/.vault_token"
    }
  }
}

# KV v2 raw path includes the `data/` segment — this is what vault_fetch_exec.sh
# got wrong (it asked for somabrain/database and Vault answered 404).
# Whitespace is load-bearing: POSTGRES_PASSWORD_FILE must contain ONLY the
# password. Any leading/trailing newline breaks auth (the file is not stripped
# of a leading newline by the stock entrypoint).
template {
  contents = "{{ with secret \"somabrain/data/database\" }}{{ .Data.data.password }}{{ end }}"
  destination = "/run/secrets/postgres_password"
  perms       = 0600
  error_on_missing_key = true
}
