import pytest

pytest.skip(
    "Mask composer tests were removed with the BHDC rollout."
    " See tests/test_bhdc_binding.py for the canonical suite.",
    allow_module_level=True,
)
