"""
Semantic Graph Module for SomaBrain.

This module defines the semantic graph structures and relation types used for knowledge
representation and semantic relationships in the SomaBrain system. It provides a taxonomy
of relationship types and utilities for normalizing relation specifications.

Key Features:
- Enumerated relation types for semantic relationships
- Normalization utilities for relation type strings
- Support for causal, hierarchical, and associative relations
- Extensible design for custom relation types

Classes:
    RelationType: Enumeration of semantic relation types.

Functions:
    normalize_relation: Normalize relation type strings to valid RelationType values.
"""

from __future__ import annotations

from enum import Enum


class RelationType(str, Enum):
    """
    Enumeration of semantic relation types for knowledge graphs.

    Defines the standard relationship types used to connect concepts and entities
    in the semantic graph. Each relation type represents a different kind of
    semantic connection between nodes.

    Values:
        related: General associative relationship
        causes: Causal relationship (A causes B)
        contrasts: Contrastive relationship (A contrasts with B)
        part_of: Meronomic relationship (A is part of B)
        depends_on: Dependency relationship (A depends on B)
        motivates: Motivational relationship (A motivates B)
        summary_of: Summarization relationship (A summarizes B)
        co_replay: Co-occurrence in memory replay

    Example:
        >>> relation = RelationType.causes
        >>> print(relation.value)  # "causes"
    """

    related = "related"
    causes = "causes"
    contrasts = "contrasts"
    part_of = "part_of"
    depends_on = "depends_on"
    motivates = "motivates"
    summary_of = "summary_of"
    co_replay = "co_replay"


def normalize_relation(t: str | None) -> str:
    """
    Normalize a relation type string to a valid RelationType value.

    Takes a potentially invalid or None relation type string and converts it
    to a valid RelationType value. If the input is invalid or None, defaults
    to the generic "related" relation type.

    Args:
        t (str | None): Relation type string to normalize, or None.

    Returns:
        str: Normalized relation type string corresponding to a valid RelationType value.

    Example:
        >>> normalized = normalize_relation("causes")
        >>> print(normalized)  # "causes"
        >>> alternative = normalize_relation("invalid_type")
        >>> print(alternative)  # "related"
        >>> default = normalize_relation(None)
        >>> print(default)  # "related"
    """
    if not t:
        return RelationType.related.value
    try:
        return RelationType(t).value
    except Exception:
        # alternative to generic
        return RelationType.related.value