"""Example training using a simple Adam optimizer for learned unitary roles.

This script demonstrates a practical (still toy) training loop that uses an
analytic gradient estimate computed via Wirtinger-style differentiation in the
frequency domain (finite difference over complex multiplier). It's vectorized
for moderate speed and uses a small Adam implementation.

Usage:
    python examples/train_role_adam.py
"""

# ruff: noqa: E402,F841  # allow imports after sys.path manipulation & ignore unused variable

import copy
import os
import sys

# Ensure repo root is on sys.path when running examples from repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from somabrain.config import get_config
from somabrain.quantum import HRRConfig, make_quantum_layer
import numpy as np


class Adam:
    def __init__(self, size, lr=1e-2, b1=0.9, b2=0.999, eps=1e-8):
        self.m = np.zeros(size, dtype=float)
        self.v = np.zeros(size, dtype=float)
        self.t = 0
        self.lr = lr
        self.b1 = b1
        self.b2 = b2
        self.eps = eps

    def step(self, grad):
        self.t += 1
        self.m = self.b1 * self.m + (1 - self.b1) * grad
        self.v = self.b2 * self.v + (1 - self.b2) * (grad * grad)
        m_hat = self.m / (1 - self.b1**self.t)
        v_hat = self.v / (1 - self.b2**self.t)
        return -self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


def analytic_phase_gradient(theta, layer, token, x):
    """Estimate gradient of reconstruction MSE w.r.t phase vector theta.

    Uses frequency-domain analytic chain rule: bind = irfft(FFT(x) * exp(i*theta)),
    unbind = irfft(FFT(bound) * exp(-i*theta)), differentiated approximately by
    considering small perturbations in the complex multiplier.
    """
    # ensure theta is rfft-length
    D = layer.cfg.dim
    n_bins = D // 2 + 1
    theta = np.asarray(theta, dtype=float)
    # build multipliers
    R = np.exp(1j * theta[:n_bins])
    X = np.fft.rfft(x)
    Y = X * R
    y = np.fft.irfft(Y, n=D)
    # unbind via conjugate phases
    X_hat = np.fft.rfft(y)
    R_conj = np.conjugate(R)
    _ = np.fft.irfft(X_hat * R_conj, n=D)  # noqa: F841 unused variable
    # error
    # reconstruction error (used only for debugging/MSE below)
    # gradient w.r.t theta_k relates to imaginary part of (conj(R_k) * X_k^* * ...)
    # We'll compute a heuristic directional derivative: dMSE/dtheta_k ~ 2 * Im( something )
    # This is a hand-wavy but practical estimator for demonstration purposes.
    # Compute frequency-domain sensitivity S_k = X_k * conj(X_hat_k) (proxy)
    S = X * np.conjugate(X_hat[:n_bins])
    # gradient approx: 2 * real( i * R_conj * S ).imag -> 2 * imag(R_conj * S)
    grad = 2.0 * np.imag(R_conj * S)
    # pad to full theta length if needed (theta already rfft-length in LearnedUnitaryRoles)
    return np.asarray(grad, dtype=float)


def main():
    cfg = copy.deepcopy(get_config())
    cfg.hybrid_math_enabled = True
    hrr = HRRConfig(dim=256, seed=1337, dtype="float32")
    # signal to factory to prefer HybridQuantumLayer
    setattr(hrr, "hybrid_math_enabled", True)
    q = make_quantum_layer(hrr)

    # Prepare role and data
    token = "adam-role"
    # random target
    x = q.random_vector()
    # initialize role
    try:
        q._learned_roles.init_role(token, seed=42)
    except Exception:
        print("Learned roles backend not available; aborting example.")
        return

    theta = q._learned_roles.get_role(token)
    opt = Adam(len(theta), lr=1e-2)

    for step in range(50):
        grad = analytic_phase_gradient(theta, q, token, x)
        delta = opt.step(grad)
        theta = theta + delta
        # wrap
        theta = np.mod(theta + np.pi, 2 * np.pi) - np.pi
        q._learned_roles.set_role(token, theta)
        # compute MSE
        rec = q._learned_roles.unbind(token, q._learned_roles.bind(token, x))
        mse = float(np.mean((rec - x) ** 2))
        if step % 10 == 0:
            print(f"step={step} mse={mse:.6e}")

    print("Example training finished. final mse=", mse)


if __name__ == "__main__":
    main()
