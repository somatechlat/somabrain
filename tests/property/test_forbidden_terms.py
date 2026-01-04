"""Property check: production files must not contain forbidden terms in comments/docstrings."""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st


FORBIDDEN = ("mock", "stub", "placeholder", "todo", "fixme", "dummy")


def _prod_files() -> list[Path]:
    """Execute prod files.
        """

    root = Path(__file__).resolve().parents[2]  # repo root
    return [
        p for p in root.joinpath("somabrain").rglob("*.py") if "tests" not in p.parts
    ]


def _comment_and_docstring_tokens(path: Path) -> list[str]:
    """Execute comment and docstring tokens.

        Args:
            path: The path.
        """

    content = path.read_text(encoding="utf-8")
    tokens = []
    stream = io.StringIO(content)
    prev_toktype = None
    for tok in tokenize.generate_tokens(stream.readline):
        tok_type, tok_str, _, _, _ = tok
        if tok_type == tokenize.COMMENT:
            tokens.append(tok_str.lower())
        elif tok_type == tokenize.STRING and prev_toktype == tokenize.INDENT:
            # Likely a docstring at module/class/func start
            tokens.append(tok_str.lower())
        prev_toktype = tok_type
    return tokens


@pytest.mark.property
@given(st.sampled_from(_prod_files()))
@settings(max_examples=120, deadline=None)
def test_no_forbidden_terms_in_comments(path: Path) -> None:
    """**Feature: memory-client-api-alignment, Property 4: Production comments/docstrings never contain forbidden terms**"""
    tokens = _comment_and_docstring_tokens(path)
    bad = [t for t in tokens if any(term in t for term in FORBIDDEN)]
    assert not bad, f"Forbidden term found in comments/docstrings of {path}"


def test_all_files_checked() -> None:
    """Deterministic sweep to ensure zero violations across all production files."""
    failures = {}
    for path in _prod_files():
        tokens = _comment_and_docstring_tokens(path)
        hits = [t for t in tokens if any(term in t for term in FORBIDDEN)]
        if hits:
            failures[str(path)] = hits
    if failures:
        summary = "; ".join(f"{p}: {len(v)} hits" for p, v in failures.items())
        pytest.fail(
            f"Forbidden terms present in production comments/docstrings: {summary}"
        )