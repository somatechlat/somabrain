#!/usr/bin/env python3
"""Initialize runtime singletons for SomaBrain.

This script mirrors the initialization logic used inside `somabrain.app`
but runs early (from the container entrypoint) so imports of
`somabrain.app` don't fail when `STRICT_REAL` requires initialized
singletons.

It is safe to run idempotently.
"""
import importlib.util
import os
import sys
import traceback

try:
    # Ensure the package path includes /app where the copied code lives
    sys.path.insert(0, "/app")
    from somabrain.config import load_config
    cfg = load_config()
    # Build optional quantum layer if requested
    quantum = None
    if getattr(cfg, "use_hrr", False):
        try:
            from somabrain.quantum import make_quantum_layer, HRRConfig as _HRRConfig

            quantum = make_quantum_layer(_HRRConfig(dim=cfg.hrr_dim, seed=cfg.hrr_seed))
        except Exception:
            try:
                from somabrain.quantum import QuantumLayer, HRRConfig

                quantum = QuantumLayer(HRRConfig(dim=cfg.hrr_dim, seed=cfg.hrr_seed))
            except Exception:
                quantum = None

    # Create embedder and working memories
    from somabrain.embeddings import make_embedder
    from somabrain.mt_wm import MTWMConfig, MultiTenantWM
    from somabrain.microcircuits import MCConfig, MultiColumnWM
    from somabrain.memory_pool import MultiTenantMemory

    embedder = None
    try:
        embedder = make_embedder(cfg, quantum)
    except Exception:
        embedder = None

    try:
        mt_wm = MultiTenantWM(dim=cfg.embed_dim, cfg=MTWMConfig(per_tenant_capacity=max(64, cfg.wm_size), max_tenants=1000))
    except Exception:
        mt_wm = None

    try:
        mc_wm = MultiColumnWM(
            dim=cfg.embed_dim,
            cfg=MCConfig(columns=max(1, int(cfg.micro_circuits)), per_col_capacity=max(16, int(cfg.wm_size // max(1, int(cfg.micro_circuits)))), vote_temperature=cfg.micro_vote_temperature,),
        )
    except Exception:
        mc_wm = None

    try:
        mt_memory = MultiTenantMemory(cfg)
    except Exception:
        mt_memory = None

    # App expects the runtime code loaded under the name 'somabrain.runtime_module'
    # (see somabrain.app: spec_from_file_location("somabrain.runtime_module", ...)).
    _rt = None
    try:
        if "somabrain.runtime_module" in sys.modules:
            _rt = sys.modules["somabrain.runtime_module"]
            print(f"initialize_runtime: reusing existing somabrain.runtime_module -> {_rt} (id={id(_rt)})")
        else:
            pkg_spec = importlib.util.find_spec("somabrain")
            if pkg_spec and getattr(pkg_spec, "submodule_search_locations", None):
                pkg_path = list(pkg_spec.submodule_search_locations)[0]
            else:
                pkg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "somabrain")
            _runtime_path = os.path.join(pkg_path, "runtime.py")
            print(f"initialize_runtime: loading runtime.py from path: {_runtime_path}")
            _spec = importlib.util.spec_from_file_location("somabrain.runtime_module", _runtime_path)
            _rt = importlib.util.module_from_spec(_spec)
            sys.modules[_spec.name] = _rt
            _spec.loader.exec_module(_rt)
            print(f"initialize_runtime: loaded somabrain.runtime_module from file -> {_rt} (id={id(_rt)})")
    except Exception:
        print("initialize_runtime: could not load somabrain.runtime_module; pkg_path=", locals().get('pkg_path', None))
        print(traceback.format_exc())
        _rt = None

    if _rt is not None:
        try:
            # show existing state for diagnostics
            try:
                print("initialize_runtime: before set_singletons: embedder=", getattr(_rt, 'embedder', None), "mt_wm=", getattr(_rt, 'mt_wm', None), "mc_wm=", getattr(_rt, 'mc_wm', None))
            except Exception:
                pass
            _rt.set_singletons(_embedder=embedder, _quantum=quantum, _mt_wm=mt_wm, _mc_wm=mc_wm, _mt_memory=mt_memory, _cfg=cfg)
            try:
                print("initialize_runtime: after set_singletons: embedder=", getattr(_rt, 'embedder', None), "mt_wm=", getattr(_rt, 'mt_wm', None), "mc_wm=", getattr(_rt, 'mc_wm', None))
            except Exception:
                pass
            print("initialize_runtime: set_singletons executed")
        except Exception:
            print("initialize_runtime: set_singletons failed:\n", traceback.format_exc())
    else:
        print("initialize_runtime: runtime module not loaded; skipping set_singletons")

except Exception:
    print("initialize_runtime: failed to initialize runtime:\n", traceback.format_exc())
