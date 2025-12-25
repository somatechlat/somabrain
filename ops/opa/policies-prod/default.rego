package soma.policy.integrator

# Deny-by-default policy for production examples.
# Tailor the allow rules below for your environment.

default allow = false

# Minimal example allow rule:
# allow {
#   # Permit system health probes or specific internal calls
#   input.request_path == "/health"  # adjust to your API
# }
