"""
Reflection Module for SomaBrain.

This module provides text analysis and summarization utilities for cognitive reflection
and memory consolidation. It includes keyword extraction, clustering of similar memories,
and automatic summarization of episodic content.

Key Features:
- Stop word filtering for meaningful keyword extraction
- TF-IDF style vectorization for text similarity
- Cosine similarity-based clustering of memories
- Automatic summarization of memory clusters
- Configurable similarity thresholds and cluster sizes

Functions:
    top_keywords: Extract most frequent keywords from a collection of texts.
    summarize_episodics: Generate summary of recent episodic memories.
    cluster_episodics: Group similar memories using text similarity clustering.
    summarize_cluster: Create keyword-based summary for a memory cluster.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np

from somabrain.math import cosine_similarity

STOP = set(
    "the a an and or of to in on for with at from by as is are was were be been it this that these those i you he she we they do did does not".split()
)
"""
Set of common English stop words to filter out during text analysis.

These words are excluded from keyword extraction and tokenization to focus
on meaningful content words. The set includes common articles, prepositions,
pronouns, and auxiliary verbs.
"""


def top_keywords(texts: List[str], k: int = 8) -> List[str]:
    """
    Extract the most frequent keywords from a collection of texts.

    Performs tokenization, stop word filtering, and frequency counting to identify
    the top-k most common meaningful words across all input texts.

    Args:
        texts (List[str]): List of text strings to analyze.
        k (int, optional): Number of top keywords to return. Defaults to 8.

    Returns:
        List[str]: List of top-k keywords in descending order of frequency.

    Example:
        >>> texts = ["machine learning is powerful", "AI and neural networks"]
        >>> keywords = top_keywords(texts, k=5)
        >>> print(keywords)  # ['machine', 'learning', 'powerful', 'neural', 'networks']
    """
    words: List[str] = []
    for t in texts:
        toks = re.findall(r"[a-zA-Z0-9_]+", (t or "").lower())
        words.extend(w for w in toks if w not in STOP and len(w) > 2)
    counts = Counter(words)
    return [w for w, _ in counts.most_common(k)]


def summarize_episodics(payloads: List[dict]) -> Tuple[str, List[dict]]:
    """
    Generate a simple heuristic summary of recent episodic memories.

    Creates a keyword-based summary by extracting the most common keywords
    from task descriptions in the memory payloads.

    Args:
        payloads (List[dict]): List of memory payload dictionaries containing task information.

    Returns:
        Tuple[str, List[dict]]: A tuple containing:
            - Summary string of top keywords
            - Original payloads list (unchanged)

    Example:
        >>> payloads = [
        ...     {"task": "studied machine learning"},
        ...     {"task": "implemented neural network"},
        ...     {"task": "analyzed data"}
        ... ]
        >>> summary, _ = summarize_episodics(payloads)
        >>> print(summary)  # "machine, learning, neural, network, data"
    """
    # Simple heuristic summary: top keywords over recent tasks
    tasks = [str(p.get("task", "")) for p in payloads]
    keys = top_keywords(tasks, k=min(8, max(3, len(tasks) // 2 or 3)))
    summary = ", ".join(keys) if keys else "recent activity"
    return summary, payloads


def _tokenize(text: str) -> List[str]:
    """
    Internal function to tokenize text with stop word filtering.

    Tokenizes input text into words, filters out stop words and short words,
    and converts to lowercase.

    Args:
        text (str): Input text to tokenize.

    Returns:
        List[str]: List of filtered tokens.
    """
    return [
        w
        for w in re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
        if w not in STOP and len(w) > 2
    ]


def _vocab_and_vectors(texts: List[str]) -> Tuple[Dict[str, int], np.ndarray]:
    """
    Internal function to create vocabulary and TF vectors from texts.

    Builds a vocabulary dictionary and creates term-frequency vectors for each text,
    then L2-normalizes the vectors for cosine similarity computation.

    Args:
        texts (List[str]): List of text strings to vectorize.

    Returns:
        Tuple[Dict[str, int], np.ndarray]: A tuple containing:
            - Vocabulary dictionary mapping words to indices
            - Normalized TF matrix (n_texts x n_vocab)

    Note:
        Uses simple term frequency (not TF-IDF) for vectorization.
        Vectors are L2-normalized for cosine similarity.
    """
    vocab: Dict[str, int] = {}
    rows: List[Counter] = []
    for t in texts:
        toks = _tokenize(t)
        counts = Counter(toks)
        for w in counts:
            if w not in vocab:
                vocab[w] = len(vocab)
        # temporary row; fill later once vocab finalized
        rows.append(counts)
    from somabrain.math import normalize_batch

    mat = np.zeros((len(texts), len(vocab)), dtype="float32")
    for i, counts in enumerate(rows):
        for w, c in counts.items():
            j = vocab[w]
            mat[i, j] = float(c)
    # l2 normalize rows using canonical batch normalization
    mat = normalize_batch(mat, axis=-1, dtype=np.float32)
    return vocab, mat


def cluster_episodics(
    payloads: List[dict], sim_threshold: float = 0.35, min_cluster_size: int = 2
) -> List[List[int]]:
    """
    Cluster episodic memories based on text similarity.

    Groups memory payloads into clusters using greedy agglomerative clustering
    with cosine similarity on TF vectors. Memories with similar task descriptions
    are grouped together.

    Args:
        payloads (List[dict]): List of memory payload dictionaries.
        sim_threshold (float, optional): Minimum cosine similarity for clustering. Defaults to 0.35.
        min_cluster_size (int, optional): Minimum cluster size to keep. Defaults to 2.

    Returns:
        List[List[int]]: List of clusters, where each cluster is a list of payload indices.
                         Small clusters may be filtered out based on min_cluster_size.

    Example:
        >>> payloads = [
        ...     {"task": "studied machine learning"},
        ...     {"task": "implemented neural network"},
        ...     {"task": "analyzed data"}
        ... ]
        >>> clusters = cluster_episodics(payloads, sim_threshold=0.3)
        >>> print(clusters)  # [[0, 1], [2]] (if similar enough)
    """
    texts = [str(p.get("task") or p.get("fact") or "") for p in payloads]
    if not texts:
        return []
    from somabrain.math import normalize_vector

    _, mat = _vocab_and_vectors(texts)
    n = mat.shape[0]
    assigned = [-1] * n
    clusters: List[List[int]] = []
    for i in range(n):
        if assigned[i] != -1:
            continue
        # start new cluster with i as seed
        centroid = mat[i].copy()
        members = [i]
        assigned[i] = len(clusters)
        # greedy add
        for j in range(i + 1, n):
            if assigned[j] != -1:
                continue
            if cosine_similarity(mat[j], centroid) >= sim_threshold:
                members.append(j)
                assigned[j] = assigned[i]
                # update centroid (mean then normalize)
                centroid = centroid + mat[j]
                centroid = normalize_vector(centroid, dtype=np.float32)
        if len(members) >= max(1, int(min_cluster_size)):
            clusters.append(members)
        else:
            # mark as unassigned if too small; may be filtered out
            for m in members:
                assigned[m] = -1
    # Add any unassigned as singleton clusters if allowed by min_cluster_size
    if min_cluster_size <= 1:
        for i in range(n):
            if assigned[i] == -1:
                clusters.append([i])
    return clusters


def summarize_cluster(payloads: List[dict], indices: List[int], max_keywords: int = 8) -> str:
    """
    Generate a keyword-based summary for a cluster of memory payloads.

    Extracts the most common keywords from the task descriptions of memories
    in the specified cluster indices.

    Args:
        payloads (List[dict]): List of all memory payload dictionaries.
        indices (List[int]): Indices of payloads in the cluster to summarize.
        max_keywords (int, optional): Maximum number of keywords to include. Defaults to 8.

    Returns:
        str: Comma-separated string of top keywords, or "summary" if no keywords found.

    Example:
        >>> payloads = [
        ...     {"task": "studied machine learning"},
        ...     {"task": "implemented neural network"}
        ... ]
        >>> summary = summarize_cluster(payloads, [0, 1])
        >>> print(summary)  # "machine, learning, neural, network"
    """
    texts = [str(payloads[i].get("task") or payloads[i].get("fact") or "") for i in indices]
    keys = top_keywords(texts, k=max_keywords)
    return ", ".join(keys) if keys else "summary"
