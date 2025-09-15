from somabrain.numerics import spectral_floor_from_tiny


def test_spectral_floor_from_tiny_basic():
    tiny_amp = 1e-4
    D = 1024
    expected = (tiny_amp**2) / D
    got = spectral_floor_from_tiny(tiny_amp, D)
    assert abs(got - expected) < 1e-20
