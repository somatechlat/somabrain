from __future__ import annotations

from collections import Counter
from typing import List, Tuple, Dict
import re
import numpy as np


STOP = set(
    "the a an and or of to in on for with at from by as is are was were be been it this that these those i you he she we they do did does not".split()
)


def top_keywords(texts: List[str], k: int = 8) -> List[str]:
    words: List[str] = []
    for t in texts:
        toks = re.findall(r"[a-zA-Z0-9_]+", (t or "").lower())
        words.extend(w for w in toks if w not in STOP and len(w) > 2)
    counts = Counter(words)
    return [w for w, _ in counts.most_common(k)]


def summarize_episodics(payloads: List[dict]) -> Tuple[str, List[dict]]:
    # Simple heuristic summary: top keywords over recent tasks
    tasks = [str(p.get("task", "")) for p in payloads]
    keys = top_keywords(tasks, k=min(8, max(3, len(tasks) // 2 or 3)))
    summary = ", ".join(keys) if keys else "recent activity"
    return summary, payloads


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z0-9_]+", (text or "").lower()) if w not in STOP and len(w) > 2]


def _vocab_and_vectors(texts: List[str]) -> Tuple[Dict[str, int], np.ndarray]:
    vocab: Dict[str, int] = {}
    rows: List[np.ndarray] = []
    for t in texts:
        toks = _tokenize(t)
        counts = Counter(toks)
        for w in counts:
            if w not in vocab:
                vocab[w] = len(vocab)
        # temporary row; fill later once vocab finalized
        rows.append(counts)  # type: ignore
    mat = np.zeros((len(texts), len(vocab)), dtype="float32")
    for i, counts in enumerate(rows):  # type: ignore
        for w, c in counts.items():
            j = vocab[w]
            mat[i, j] = float(c)
    # l2 normalize rows
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms
    return vocab, mat


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def cluster_episodics(payloads: List[dict], sim_threshold: float = 0.35, min_cluster_size: int = 2) -> List[List[int]]:
    texts = [str(p.get("task") or p.get("fact") or "") for p in payloads]
    if not texts:
        return []
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
            if _cosine_sim(mat[j], centroid) >= sim_threshold:
                members.append(j)
                assigned[j] = assigned[i]
                # update centroid (mean then normalize)
                centroid = centroid + mat[j]
                norm = np.linalg.norm(centroid) or 1.0
                centroid = centroid / norm
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
    texts = [str(payloads[i].get("task") or payloads[i].get("fact") or "") for i in indices]
    keys = top_keywords(texts, k=max_keywords)
    return ", ".join(keys) if keys else "summary"

