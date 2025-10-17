from __future__ import annotations

import json
from pathlib import Path

from scripts import prove_enhancement


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prove_enhancement_pass(tmp_path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write(
        baseline,
        {
            "metrics": {
                "top1_accuracy": 0.90,
                "cosine_margin": 0.12,
                "recall_latency_p95": 0.085,
            }
        },
    )
    _write(
        candidate,
        {
            "metrics": {
                "top1_accuracy": 0.92,
                "cosine_margin": 0.15,
                "recall_latency_p95": 0.080,
            }
        },
    )

    code = prove_enhancement.main(
        ["--baseline", str(baseline), "--candidate", str(candidate)]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "PASS" in captured.out


def test_prove_enhancement_failure(tmp_path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write(
        baseline,
        {
            "metrics": {
                "top1_accuracy": 0.95,
                "cosine_margin": 0.18,
                "recall_latency_p95": 0.070,
            }
        },
    )
    _write(
        candidate,
        {
            "metrics": {
                "top1_accuracy": 0.94,
                "cosine_margin": 0.16,
                "recall_latency_p95": 0.075,
            }
        },
    )

    code = prove_enhancement.main(
        [
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--accuracy-tolerance",
            "0.005",
            "--margin-tolerance",
            "0.01",
            "--latency-regression",
            "0.03",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "FAIL" in captured.out
