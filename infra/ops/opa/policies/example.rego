package soma.policy

# FAIL-CLOSED. This tree previously shipped `default allow = true` (dev
# "allow all") — a latent bypass if mounted. Enterprise law: default deny.

default allow = false
