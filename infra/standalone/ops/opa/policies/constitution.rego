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

# Static admin assets (GET only).
allow {
	input.method == "GET"
	startswith(input.path, "/static/")
}
