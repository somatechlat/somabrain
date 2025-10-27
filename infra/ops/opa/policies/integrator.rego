package soma.policy.integrator

# Default to allow unless explicitly denied
default allow = true

# Proposed leader defaults to candidate leader (can be overridden by rules)
leader := input.candidate.leader

# Example adjustment: if action weight is very strong, choose action explicitly
leader := "action" if {
  w := input.candidate.weights["action"]
  w >= 0.7
}

# Example deny rule for a blocked tenant (demo)
allow = false if {
  input.tenant == "blocked"
}

# Result object is assembled by OPA automatically when querying this package path
# via /v1/data/soma/policy/integrator; it will contain the top-level keys allow, leader.
