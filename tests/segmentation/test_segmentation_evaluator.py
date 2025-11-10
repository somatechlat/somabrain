from somabrain.segmentation.evaluator import (
    generate_synthetic_sequence,
    true_boundaries,
    evaluate_boundaries,
    evaluate_sequence,
)


def test_evaluator_basic():
    seq = generate_synthetic_sequence(length=100, change_prob=0.1, seed=42)
    tb = true_boundaries(seq)
    # Simulate emitted boundaries with small jitter: choose subset of true boundaries
    emitted = [t for i, t in enumerate(tb) if i % 2 == 0]
    f1, false_rate, latency = evaluate_boundaries(emitted, tb)
    assert 0.0 <= f1 <= 1.0
    assert 0.0 <= false_rate <= 1.0
    assert latency >= 0.0


def test_evaluator_sequence_wrapper():
    seq = generate_synthetic_sequence(length=120, change_prob=0.08, seed=7)
    tb = true_boundaries(seq)
    # Emitted boundaries intentionally sparse
    emitted = tb[::3]
    res = evaluate_sequence(seq, emitted)
    assert "f1" in res and "false_rate" in res and "mean_latency" in res
    assert res["true_count"] == len(tb)
    assert res["emitted_count"] == len(emitted)
