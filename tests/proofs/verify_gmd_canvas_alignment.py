import numpy as np
import somabrain_rs as rs


def test_variance_of_similarity(D: int = 8192, N: int = 1000):
    """Measure Var(sim(x,y)) and confirm it is ~ 1/D."""
    similarities = []
    # Use standard encoder to match system behavior
    encoder = rs.BHDCEncoder(dim=D, sparsity=0.1, base_seed=42, binary_mode="pm_one")

    for i in range(N):
        x = np.array(encoder.random_vector())
        y = np.array(encoder.random_vector())
        # Cosine similarity
        sim = np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
        similarities.append(sim)

    var_empirical = np.var(similarities)
    var_theoretical = 1.0 / D
    ratio = var_empirical / var_theoretical

    print("--- Var(sim) Test ---")
    print(f"Dimension D: {D}")
    print(f"Empirical Var: {var_empirical:.8f}")
    print(f"Theoretical Var (1/D): {var_theoretical:.8f}")
    print(f"Ratio: {ratio:.4f} (Ideal: 1.0)")
    return ratio


def test_snr_decay(D: int = 2048, L_max: int = 50, eta: float = 0.08):
    """Measure SNR(L) vs L and confirm power law decay (1-eta)^{2L}."""
    # We use BayesianMemory from Rust
    # λ* from the GMD Theorem 3 formula at production sparsity p = 0.1
    lambda_reg = rs.compute_wiener_lambda(0.1, 8)
    mem = rs.BayesianMemory(D, eta=eta, lambda_reg=lambda_reg)

    # Generate items to store
    keys = [
        np.array(rs.BHDCEncoder(dim=D, sparsity=0.1, base_seed=i).random_vector())
        for i in range(L_max)
    ]
    values = [
        np.array(
            rs.BHDCEncoder(dim=D, sparsity=0.1, base_seed=i + 1000).random_vector()
        )
        for i in range(L_max)
    ]

    # Store items
    for k, v in zip(keys, values):
        # Simplistic bind for test: elementwise multiply
        binding = k * v
        mem.update(binding.tolist())

    # Measure SNR at different lags
    snrs = []
    theoretical_decays = []

    for L in range(L_max):
        # Item stored L steps ago (last item is L=0)
        idx = (L_max - 1) - L
        key = keys[idx]
        expected_v = values[idx]

        recalled = np.array(mem.recall(key.tolist()))

        # Signal = similarity with target
        sim = np.dot(recalled, expected_v) / (
            np.linalg.norm(recalled) * np.linalg.norm(expected_v)
        )

        # SNR Calculation: (Signal^2) / (1 - Signal^2) * D
        if sim >= 1.0:
            snr = float("inf")
        else:
            snr = (sim**2) / (1.0 - sim**2 + 1e-9) * D

        snrs.append(snr)
        # Power law: w_L^2 / (W2 - w_L^2) where w_L = eta(1-eta)^L
        # Simplified ratio check: SNR(L) / SNR(0) should be ~ (1-eta)^{2L}
        theoretical_decays.append((1.0 - eta) ** (2 * L))

    # Log linear regression on SNR ratios
    snr_ratios = [s / snrs[0] for s in snrs]

    print("\n--- SNR Decay Test ---")
    print("Lag | SNR Ratio | Theoretical (1-eta)^2L")
    for i in [0, 1, 5, 10, 20]:
        if i < len(snr_ratios):
            print(f"{i:3} | {snr_ratios[i]:.4f}    | {theoretical_decays[i]:.4f}")

    # Return correlation or MSE
    corr = np.corrcoef(snr_ratios, theoretical_decays)[0, 1]
    print(f"Correlation with power law: {corr:.6f}")
    return corr


def test_quantization_lambda_optimality(D: int = 1024, samples: int = 100):
    """Find optimal lambda for 8-bit quantization noise."""
    lambdas = np.logspace(-6, -3, 20)
    mses = []

    encoder = rs.BHDCEncoder(dim=D, sparsity=0.1, base_seed=42)

    for lam in lambdas:
        total_mse = 0
        for _ in range(samples):
            v = np.array(encoder.random_vector())
            k = np.array(encoder.random_vector())
            # binding
            c = v * k
            # add quantization noise (simulated)
            c_q = np.array([rs.quantize_8bit(x) for x in c])

            # Use Wiener unbinding
            recovered = np.array(rs.wiener_unbind(c_q.tolist(), k.tolist(), lam))

            # MSE vs original v
            # total_mse += np.mean((recovered - v)**2)
            # Actually measure Reconstruction Error: 1 - Similarity
            sim = np.dot(recovered, v) / (np.linalg.norm(recovered) * np.linalg.norm(v))
            total_mse += 1.0 - sim

        mses.append(total_mse / samples)

    # Theoretical λ* from the production formula (GMD Theorem 3):
    # λ* = Δ² / (12 p (1−p)) with Δ = 2/255 — same function the binder uses.
    p = 0.1
    theoretical_lambda = rs.compute_wiener_lambda(p, 8)

    experimental_min_lambda = lambdas[np.argmin(mses)]

    print("\n--- Quantization Lambda Test ---")
    print(f"Theoretical optimal lambda: {theoretical_lambda:.2e}")
    print(f"Experimental optimal lambda: {experimental_min_lambda:.2e}")

    return experimental_min_lambda / theoretical_lambda


if __name__ == "__main__":
    test_variance_of_similarity()
    test_snr_decay()
    test_quantization_lambda_optimality()
