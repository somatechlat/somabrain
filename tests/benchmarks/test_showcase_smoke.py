from __future__ import annotations

import json
from pathlib import Path
import importlib.util
import sys


def _import_showcase_run() -> callable:
    """Import the run() function from the repo's benchmarks/showcase_suite.py by path.

    This avoids import shadowing from tests/benchmarks.
    """
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "benchmarks" / "showcase_suite.py"
    spec = importlib.util.spec_from_file_location("showcase_suite", mod_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return getattr(mod, "run")


def test_showcase_dry_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "showcase"
    run = _import_showcase_run()
    code = run(
        [
            "--dry-run",
            "--out-dir",
            str(out_dir),
            "--requests",
            "25",
            "--concurrency",
            "5",
        ]
    )
    assert code == 0
    # Check artifacts exist and have expected shape
    lat_path = out_dir / "latency.json"
    assert lat_path.exists()
    data = json.loads(lat_path.read_text())
    assert data["requests"] == 25
    assert data["concurrency"] == 5
    assert isinstance(data.get("samples_s"), list)

    md = (out_dir / "showcase_report.md").read_text()
    assert "Latency smoke" in md
