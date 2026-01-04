"""Dataset construction helpers for SomaBrain learning loops."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Iterator, List, Optional, Sequence


def _extract_text(payload: dict) -> Optional[str]:
    """Execute extract text.

        Args:
            payload: The payload.
        """

    for key in ("text", "task", "content", "what"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


@dataclass
class TrainingExample:
    """Trainingexample class implementation."""

    prompt: str
    response: str
    tenant: str
    namespace: str
    metadata: dict

    def tokens(self, tokenizer: Callable[[str], Sequence[int]]) -> dict:
        """Execute tokens.

            Args:
                tokenizer: The tokenizer.
            """

        return {
            "prompt_tokens": list(tokenizer(self.prompt)),
            "response_tokens": list(tokenizer(self.response)),
            "tenant": self.tenant,
            "namespace": self.namespace,
            "metadata": self.metadata,
        }


def _conversation_from_payload(payload: dict) -> Optional[List[dict]]:
    """Execute conversation from payload.

        Args:
            payload: The payload.
        """

    convo = payload.get("conversation")
    if isinstance(convo, list):
        messages: List[dict] = []
        for item in convo:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append({"role": role.strip(), "content": content})
        if messages:
            return messages
    return None


def _build_example(record: dict) -> Optional[TrainingExample]:
    """Execute build example.

        Args:
            record: The record.
        """

    tenant = str(record.get("tenant") or "unknown")
    namespace = str(record.get("namespace") or "default")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None

    convo = _conversation_from_payload(payload)
    if convo and len(convo) >= 2:
        # use the last user/assistant pair
        user = None
        assistant = None
        for message in reversed(convo):
            if assistant is None and message.get("role") == "assistant":
                assistant = message.get("content")
                continue
            if assistant is not None and message.get("role") == "user":
                user = message.get("content")
                break
        if isinstance(user, str) and isinstance(assistant, str):
            return TrainingExample(
                prompt=user.strip(),
                response=assistant.strip(),
                tenant=tenant,
                namespace=namespace,
                metadata={
                    k: v for k, v in payload.items() if k not in {"conversation"}
                },
            )

    prompt = payload.get("prompt")
    response = payload.get("response")
    if isinstance(prompt, str) and isinstance(response, str):
        return TrainingExample(
            prompt=prompt.strip(),
            response=response.strip(),
            tenant=tenant,
            namespace=namespace,
            metadata={
                k: v for k, v in payload.items() if k not in {"prompt", "response"}
            },
        )

    # alternative: treat current text as response and use previous text as prompt
    response_text = _extract_text(payload)
    history = payload.get("history")
    if isinstance(history, list):
        for item in reversed(history):
            if isinstance(item, dict):
                prompt_text = _extract_text(item)
                if prompt_text and response_text:
                    return TrainingExample(
                        prompt=prompt_text,
                        response=response_text,
                        tenant=tenant,
                        namespace=namespace,
                        metadata={"source": "history"},
                    )

    return None


def build_examples(records: Iterable[dict]) -> List[TrainingExample]:
    """Execute build examples.

        Args:
            records: The records.
        """

    examples: List[TrainingExample] = []
    for record in records:
        example = _build_example(record)
        if example and example.prompt and example.response:
            examples.append(example)
    return examples


def tokenize_examples(
    examples: Iterable[TrainingExample],
    tokenizer: Callable[[str], Sequence[int]],
) -> List[dict]:
    """Execute tokenize examples.

        Args:
            examples: The examples.
            tokenizer: The tokenizer.
        """

    return [example.tokens(tokenizer) for example in examples]


def export_examples(examples: Iterable[TrainingExample], path: str) -> None:
    """Execute export examples.

        Args:
            examples: The examples.
            path: The path.
        """

    with open(path, "w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(asdict(example), ensure_ascii=False) + "\n")


def iter_jsonl(path: str) -> Iterator[dict]:
    """Execute iter jsonl.

        Args:
            path: The path.
        """

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)