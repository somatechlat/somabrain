import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


def _bhdc_layer(**overrides) -> QuantumLayer:
    cfg = HRRConfig(
        dim=overrides.get("dim", 512),
        seed=overrides.get("seed", 123),
        sparsity=overrides.get("sparsity", 0.1),
        binary_mode=overrides.get("binary_mode", "pm_one"),
        mix=overrides.get("mix", "none"),
        binding_seed=overrides.get("binding_seed"),
        binding_tenant=overrides.get("tenant"),
        binding_model_version=overrides.get("model_version"),
    )
    return QuantumLayer(cfg)


def test_bhdc_roundtrip_recovery():
    q = _bhdc_layer(dim=256)
    a = q.random_vector()
    b = q.random_vector()
    bound = q.bind(a, b)
    recovered = q.unbind(bound, b)
    cos = QuantumLayer.cosine(a, recovered)
    assert cos > 0.98


def test_bhdc_binding_is_deterministic():
    q = _bhdc_layer(dim=128)
    a = q.encode_text("deterministic-a")
    b = q.encode_text("deterministic-b")
    c1 = q.bind(a, b)
    c2 = q.bind(a, b)
    assert np.allclose(c1, c2, atol=1e-9)


def test_bhdc_roles_are_distinct():
    q = _bhdc_layer(dim=128)
    role_a = q.make_unitary_role("role-a")
    role_b = q.make_unitary_role("role-b")
    assert not np.allclose(role_a, role_b)
    cos = QuantumLayer.cosine(role_a, role_b)
    assert cos < 0.99


def test_bhdc_seed_variation_changes_binding():
    qa = _bhdc_layer(dim=128, binding_seed="tenant-A")
    qb = _bhdc_layer(dim=128, binding_seed="tenant-B")
    a_a = qa.encode_text("shared-a")
    b_a = qa.encode_text("shared-b")
    a_b = qb.encode_text("shared-a")
    b_b = qb.encode_text("shared-b")
    c_a = qa.bind(a_a, b_a)
    c_b = qb.bind(a_b, b_b)
    cos = QuantumLayer.cosine(c_a, c_b)
    assert cos < 0.999


def test_bhdc_wiener_alias_returns_unbind():
    q = _bhdc_layer(dim=128)
    a = q.random_vector()
    b = q.random_vector()
    bound = q.bind(a, b)
    rec_w = q.unbind_wiener(bound, b, snr_db=20.0)
    rec = q.unbind(bound, b)
    assert np.allclose(rec, rec_w, atol=1e-7)
