package soma.policy.integrator

# Integrator leader selection — FAIL-CLOSED.
# default allow = true is forbidden (enterprise law): an undecided
# integrator request is denied, never allowed.

default allow = false

# Proposed leader defaults to candidate leader (can be overridden by rules)
leader := input.candidate.leader

# If action weight is very strong, choose action explicitly
leader := "action" if {
  w := input.candidate.weights["action"]
  w >= 0.7
}

# Explicit allow: integrator evaluation for a non-blocked tenant with a candidate.
allow if {
  input.tenant != "blocked"
  input.candidate
  input.action
}

# Explicit deny: blocked tenant is never allowed.
allow = false if {
  input.tenant == "blocked"
}
