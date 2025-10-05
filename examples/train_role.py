"""Small example showing how to train a learned unitary role using the HybridQuantumLayer.

This script performs a toy training loop that attempts to make the role such that
binding then unbinding a noisy version of a vector reconstructs the original.

Usage:
    python examples/train_role.py

This is intentionally small, self-contained, and uses only repository internal APIs
(no external services). It demonstrates how to call `train_role_phases` with a
simple gradient that encourages correct unbinding.
"""

from somabrain.config import load_config
from somabrain.quantum import HRRConfig, make_quantum_layer
import numpy as np


def simple_reconstruction_gradient(theta, qlayer, token, target_vector):
    """Compute a finite-difference gradient on theta that reduces reconstruction MSE.

    This is a toy estimator: perturb each phase slightly and measure change in
    MSE after unbinding. It's slow but deterministic and simple for example.
    """
    eps = 1e-3
    grad = np.zeros_like(theta, dtype=float)
    base_recon = qlayer._learned_roles.unbind(
        token, qlayer._learned_roles.bind(token, target_vector)
    )
    base_mse = float(np.mean((target_vector - base_recon) ** 2))
    for i in range(len(theta)):
        theta_p = theta.copy()
        theta_p[i] += eps
        qlayer._learned_roles.set_role(token, theta_p)
        recon_p = qlayer._learned_roles.unbind(
            token, qlayer._learned_roles.bind(token, target_vector)
        )
        mse_p = float(np.mean((target_vector - recon_p) ** 2))
        grad[i] = (mse_p - base_mse) / eps
    # restore original theta
    qlayer._learned_roles.set_role(token, theta)
    return grad


def main():
    cfg = load_config()
    # enable hybrid for example runtime if not already
    cfg.hybrid_math_enabled = True
    hrr = HRRConfig(dim=256, seed=123, dtype="float32")
    q = make_quantum_layer(hrr)

    token = "example-role"
    # create a random target vector to reconstruct
    target = q.random_vector()
    # train the role via the provided method if available
    try:
        # prepare a closure gradient function bound to current q and token
        def grad_fn(theta):
            return simple_reconstruction_gradient(theta, q, token, target)

        q.train_role_phases(token, grad_fn, steps=10, lr=1e-2)
        print("Training completed; role updated.")
    except Exception as e:
        print("Training API not available or failed:", e)


if __name__ == "__main__":
    main()
