# OPA policy for Oak option endpoints
# ------------------------------------------------------------
# This policy defines the permissions required to create and update
# Oak options.  It is loaded by the SimpleOPAEngine at startup via the
# ``opa_bundle_path`` setting (default points to the ``opa`` directory).

package somabrain.option

# Allow a user with the ``brain_admin`` role to create an option.
allow_option_creation {
    input.method == "POST"
    input.path = ["oak", "option", "create"]
    input.user.role == "brain_admin"
}

# Allow a user with the ``brain_admin`` role to update an option.
allow_option_update {
    input.method == "PUT"
    # The third element is the option identifier – we accept any value.
    input.path = ["oak", "option", "update", _]
    input.user.role == "brain_admin"
}

# The OPA engine will evaluate ``allow`` by checking the two rules above.
default allow = false
allow {
    allow_option_creation
}
allow {
    allow_option_update
}
