package soma.policy

# FAIL-CLOSED. This file previously shipped `default allow = true` (dev
# "allow all") and was mounted into the production OPA container — a
# latent bypass. Enterprise law: default deny. Nothing is allowed here
# unless an explicit rule says so.

default allow = false

# No broad allow rules in this package. Real authorization lives in
# `somabrain/auth/allow` (constitution.rego) and the composed agent
# policies. Keep this file deny-by-default so a mis-mount cannot open
# the product.
