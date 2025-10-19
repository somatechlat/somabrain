from __future__ import annotations

import json

import pytest

from somabrain.learning.dataset import (
    TrainingExample,
    build_examples,
    tokenize_examples,
)


def test_build_examples_from_conversation():
    records = [
        {
            "tenant": "acme",
            "namespace": "wm",
            "payload": {
                "conversation": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
                "score": 0.9,
            },
        }
    ]

    examples = build_examples(records)
    assert len(examples) == 1
    ex = examples[0]
    assert isinstance(ex, TrainingExample)
    assert ex.prompt == "Hello"
    assert ex.response == "Hi!"
    tokens = tokenize_examples(examples, lambda s: [ord(c) for c in s])
    assert tokens[0]["prompt_tokens"]


def test_build_examples_from_prompt_response():
    records = [
        {
            "tenant": "acme",
            "namespace": "ltm",
            "payload": {
                "prompt": "What is SomaBrain?",
                "response": "A governed HDM memory system.",
            },
        }
    ]

    examples = build_examples(records)
    assert len(examples) == 1
    assert examples[0].tenant == "acme"
    assert "prompt" not in examples[0].metadata


def test_export_learning_corpus_requires_flag(tmp_path, monkeypatch):
    # Prepare input file with one record
    input_path = tmp_path / "records.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "tenant": "acme",
                "namespace": "wm",
                "payload": {"prompt": "Hi", "response": "Hello"},
            }
        )
        + "\n"
    )
    output_path = tmp_path / "output.jsonl"

    import scripts.export_learning_corpus as export_script

    # Flag disabled -> expect SystemExit from argparse error
    monkeypatch.setenv("SOMABRAIN_LEARNING_LOOP_ENABLED", "0")
    with pytest.raises(SystemExit):
        dummy_cfg = type("Cfg", (), {"learning_loop_enabled": False})()
        monkeypatch.setattr(export_script, "get_config", lambda: dummy_cfg)
        export_script.main([str(input_path), str(output_path)])

    # With force flag it should succeed
    dummy_cfg_enabled = type("Cfg", (), {"learning_loop_enabled": False})()
    monkeypatch.setattr(export_script, "get_config", lambda: dummy_cfg_enabled)
    monkeypatch.setattr(
        export_script, "_git_metadata", lambda: {"commit": "deadbeef", "dirty": False}
    )
    monkeypatch.setattr(
        export_script,
        "_config_snapshot",
        lambda: {"digest": "abc123", "learning_loop_enabled": False},
    )

    metadata_path = tmp_path / "run.json"
    rc = export_script.main(
        [
            str(input_path),
            str(output_path),
            "--force",
            "--metadata-out",
            str(metadata_path),
        ]
    )
    assert rc == 0
    assert output_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text())
    assert metadata["examples"] == 1
    assert metadata["git"]["commit"] == "deadbeef"
    assert metadata["config"]["digest"] == "abc123"
