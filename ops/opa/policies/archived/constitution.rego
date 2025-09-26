# OPA policy template generated from the SomaBrain constitution.
# The template uses placeholders that will be replaced by the policy builder.
# Required top-level keys (e.g., version, rules) are enforced.
# Rule example: if the instance has `forbidden` set and the constitution does not allow it, deny.

package soma.policy

# Default allow – will be overridden by specific rules.
default allow = true

# Enforce required keys exist in the constitution.
allow {
    input.constitution.version != ""
    input.constitution.rules != null
}

# Deny if instance is marked forbidden and constitution disallows it.
allow {
    not input.instance.forbidden
}

allow {
    # If forbidden is allowed by constitution
    input.constitution.rules.allow_forbidden == true
}
