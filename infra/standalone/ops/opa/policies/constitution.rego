package somabrain.auth

# Fail-closed: only explicit allow rules permit a request.
default allow = false

# Liveness / readiness probes (docker healthchecks, k8s).
allow {
	input.method == "GET"
	startswith(input.path, "/health")
}

allow {
	input.method == "GET"
	startswith(input.path, "/healthz")
}

allow {
	input.method == "GET"
	startswith(input.path, "/readyz")
}

allow {
	input.method == "GET"
	startswith(input.path, "/simple")
}

# Metrics scrape.
allow {
	input.method == "GET"
	startswith(input.path, "/metrics")
}

# OpenAPI / docs surface.
allow {
	input.method == "GET"
	startswith(input.path, "/api/docs")
}

allow {
	input.method == "GET"
	startswith(input.path, "/api/openapi.json")
}

# Versioned and unversioned cognitive API surface.
# AuthN/AuthZ still enforced by api_key_auth / require_auth on each route;
# this layer denies anything outside the declared surface.
allow {
	startswith(input.path, "/api/")
}

# Product agent↔brain surface (W-H + APM). Django auth still binds tenant.
# OPA here is surface-gate only (not identity) — fail-closed on unknown paths.
allow {
	startswith(input.path, "/memory/")
}

allow {
	startswith(input.path, "/context/")
}

allow {
	startswith(input.path, "/neuromod/")
}

allow {
	startswith(input.path, "/persona/")
}

allow {
	startswith(input.path, "/cognitive/")
}

allow {
	startswith(input.path, "/threads/")
}

allow {
	startswith(input.path, "/sleep/")
}

allow {
	startswith(input.path, "/oak/")
}

allow {
	startswith(input.path, "/brain/")
}

allow {
	startswith(input.path, "/admin/")
}

allow {
	startswith(input.path, "/remember")
}

allow {
	startswith(input.path, "/recall")
}

allow {
	startswith(input.path, "/forget")
}

# Static admin assets (GET only).
allow {
	input.method == "GET"
	startswith(input.path, "/static/")
}
