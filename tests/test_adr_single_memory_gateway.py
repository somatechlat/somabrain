import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_no_direct_somafractalmemory_imports_outside_memory_client():
    base = ROOT / "somabrain"
    offenders = []
    for py in base.rglob("*.py"):
        # allow the gateway itself
        if py.name == "memory_client.py":
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "somafractalmemory." in text or "from somafractalmemory" in text:
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, (
        "Direct somafractalmemory imports are only allowed in memory_client.py, "
        f"found in: {offenders}"
    )
