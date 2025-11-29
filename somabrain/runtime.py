from __future__ import annotations
import sys

# Defensive: always ensure cfg is present as a module attribute, even on reload or subprocess import
import traceback
import datetime

mod = sys.modules[__name__]


def _log_cfg_event(event):
    ts = datetime.datetime.now().isoformat()
    msg = f"[runtime.py][{ts}] {event}\n"
    sys.stderr.write(msg)
    sys.stderr.flush()


if not hasattr(mod, "cfg") or getattr(mod, "cfg", None) is None:

    class _TmpCfg:

    setattr(mod, "cfg", _TmpCfg())
    _log_cfg_event(
        f"cfg alternative assigned at import: {traceback.format_stack(limit=4)}"
    )

"""
Runtime Singletons Registry
---------------------------

Tiny module to avoid circular imports when wiring the retrieval pipeline.
The app sets these singletons at startup; services import here lazily.
"""

embedder = None
quantum = None
mt_wm = None
mc_wm = None
mt_memory = None


class RuntimeConfig:
    def __init__(self):
        self.use_query_expansion = False
        self.query_expansion_variants = 0
        self.use_microcircuits = False
        self.graph_hops = 1
        self.graph_limit = 20
        self.retriever_weight_vector = 1.0
        self.retriever_weight_wm = 1.0
        self.retriever_weight_graph = 1.0
        self.retriever_weight_lexical = 0.8
        self.reranker_model = None
        self.reranker_top_n = 50
        self.reranker_out_k = 1
        self.reranker_batch = 32


setattr(mod, "cfg", RuntimeConfig())
_log_cfg_event(
    f"cfg assigned after class definition: {traceback.format_stack(limit=4)}"
)


def set_singletons(
    *,
    _embedder=None,
    _quantum=None,
    _mt_wm=None,
    _mc_wm=None,
    _mt_memory=None,
    _cfg=None,
) -> None:
    global embedder, quantum, mt_wm, mc_wm, mt_memory
    embedder = _embedder
    quantum = _quantum
    mt_wm = _mt_wm
    mc_wm = _mc_wm
    mt_memory = _mt_memory
    # Always ensure cfg is present as a module attribute
    if _cfg is not None:
        setattr(mod, "cfg", _cfg)
        _log_cfg_event(
            f"cfg set by set_singletons(_cfg): {repr(_cfg)} {traceback.format_stack(limit=4)}"
        )
    elif not hasattr(mod, "cfg") or getattr(mod, "cfg") is None:
        setattr(mod, "cfg", RuntimeConfig())
        _log_cfg_event(
            f"cfg alternative in set_singletons: {traceback.format_stack(limit=4)}"
        )
