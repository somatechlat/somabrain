from __future__ import annotations

"""
Runtime Singletons Registry
---------------------------

Tiny module to avoid circular imports when wiring the RAG pipeline.
The app sets these singletons at startup; services import here lazily.
"""

embedder = None
quantum = None
mt_wm = None
mc_wm = None
mt_memory = None
cfg = None


def set_singletons(
    *,
    _embedder=None,
    _quantum=None,
    _mt_wm=None,
    _mc_wm=None,
    _mt_memory=None,
    _cfg=None,
) -> None:
    global embedder, quantum, mt_wm, mc_wm, mt_memory, cfg
    embedder = _embedder
    quantum = _quantum
    mt_wm = _mt_wm
    mc_wm = _mc_wm
    mt_memory = _mt_memory
    cfg = _cfg
