# Vault Agent — MinIO sidecar (SOMA-STD-BOOTSTRAP-001 / R-SEC-01).
#
# Auto-auth via AppRole. Root credentials are rendered to a tmpfs volume and
# consumed via MINIO_ROOT_USER_FILE / MINIO_ROOT_PASSWORD_FILE. Values never
# enter env, argv, compose YAML, or a disk volume.

vault {
  # Address comes from VAULT_ADDR (topology). Never hardcoded here (Rule 91).
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path     = "/run/approle/minio/role_id"
      secret_id_file_path   = "/run/approle/minio/secret_id"
      remove_secret_id_file = false
    }
  }

  sink "file" {
    config = {
      path = "/run/secrets/.vault_token"
    }
  }
}

# Whitespace is load-bearing: *_FILE must contain ONLY the credential.
template {
  contents = "{{ with secret \"somabrain/data/runtime\" }}{{ .Data.data.minio_access_key }}{{ end }}"
  destination = "/run/secrets/minio_access_key"
  perms       = 0600
  error_on_missing_key = true
}

template {
  contents = "{{ with secret \"somabrain/data/runtime\" }}{{ .Data.data.minio_secret_key }}{{ end }}"
  destination = "/run/secrets/minio_secret_key"
  perms       = 0600
  error_on_missing_key = true
}
