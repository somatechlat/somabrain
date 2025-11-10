import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]  # project root

LEGACY_PATTERNS = [
    r"ENABLE_[A-Z0-9_]+",
    r"SOMABRAIN_FF_[A-Z0-9_]+",
]

def test_no_legacy_feature_flag_tokens():
    py_files = [p for p in ROOT.rglob("*.py") if "tests/invariants" not in str(p)]
    pattern = re.compile("|".join(LEGACY_PATTERNS))
    offenders = []
    for pf in py_files:
        try:
            txt = pf.read_text(encoding="utf-8")
        except Exception:
            continue
        if pattern.search(txt):
            offenders.append(str(pf))
    assert offenders == [], f"Legacy flag tokens still present: {offenders}"
