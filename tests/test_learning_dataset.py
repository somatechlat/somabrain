from __future__ import annotations

from somabrain.learning.dataset import TrainingExample, build_examples, tokenize_examples


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
