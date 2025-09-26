import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_no_legacy_memory_service_imports_outside_memory_client():
    base = ROOT / "somabrain"
    offenders = []
    legacy_prefix = "somafractal" + "memory"
    for py in base.rglob("*.py"):
        # allow the gateway itself
        if py.name == "memory_client.py":
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if (
            f"{legacy_prefix}." in text
            or f"from {legacy_prefix}" in text
        ):
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, (
        "Direct legacy memory service imports are only allowed in memory_client.py, "
        f"found in: {offenders}"
    )
