package soma.policy.integrator

# Integrator leader selection — FAIL-CLOSED.
# default allow = true is forbidden: an undecided request is denied.

default allow = false

leader = input.candidate.leader

leader = "action" {
  w := input.candidate.weights["action"]
  w >= 0.7
}

allow {
  input.tenant != "blocked"
  input.candidate
  input.action
}

allow = false {
  input.tenant == "blocked"
}
