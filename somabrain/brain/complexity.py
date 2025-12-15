"""Complexity Detector - Content complexity analysis for auto-scaling."""

from __future__ import annotations

from typing import Any, Dict


class ComplexityDetector:
    """Detect content complexity for auto-scaling decisions."""

    def analyze_complexity(self, content: Dict[str, Any]) -> float:
        """Analyze the complexity of content to determine processing requirements."""
        complexity_score = 0.0

        text_content = content.get("concept", "") + " " + content.get("content", "")
        text_length = len(text_content)
        complexity_score += min(0.3, text_length / 1000)

        words = text_content.lower().split()
        unique_words = len(set(words))
        complexity_score += min(0.3, unique_words / 200)

        if "relationships" in content:
            complexity_score += min(0.2, len(content["relationships"]) / 10)

        importance = content.get("importance", 0.5)
        complexity_score *= 0.5 + importance

        return min(1.0, complexity_score)
