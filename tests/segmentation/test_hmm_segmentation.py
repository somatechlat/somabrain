from somabrain.segmentation.hmm import HMMParams, online_viterbi_probs, detect_boundaries


def test_hmm_boundary_detection_synthetic():
    # Synthetic sequence: low values ~ STABLE around mean 0, then high jump ~ TRANSITION mean 3
    stable = [0.05, -0.1, 0.02, 0.0, -0.05]
    transition = [2.7, 2.9, 3.1, 2.8, 3.0]
    seq = stable + transition
    params = HMMParams(
        A=((0.92, 0.08), (0.25, 0.75)),  # moderate persistence
        mu=(0.0, 3.0),
        sigma=(0.25, 0.3),
    )
    probs = online_viterbi_probs(seq, params)
    boundaries = detect_boundaries(probs, threshold=0.6)
    # Expect at least one boundary near index len(stable)
    assert boundaries, "No boundary detected in synthetic sequence"
    assert any(abs(b - len(stable)) <= 1 for b in boundaries), "Boundary not near transition point"
