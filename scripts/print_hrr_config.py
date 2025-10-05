#!/usr/bin/env python
"""Print current HRR/quantum configuration for operational inspection.

Usage:
    python -m scripts.print_hrr_config
"""
from somabrain.quantum import HRRConfig
from somabrain.config import load_config
import json

cfg = load_config()
if not getattr(cfg, "use_hrr", False):
    print(json.dumps({"hrr_enabled": False}, indent=2))
else:
    qcfg = HRRConfig(dim=cfg.hrr_dim, seed=cfg.hrr_seed)
    print(
        json.dumps(
            {
                "hrr_enabled": True,
                "dim": qcfg.dim,
                "seed": qcfg.seed,
                "renorm": qcfg.renorm,
                "tiny_floor_strategy": qcfg.tiny_floor_strategy,
                "roles_unitary": qcfg.roles_unitary,
            },
            indent=2,
        )
    )
