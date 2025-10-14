#!/usr/bin/env python
"""Print current HRR/quantum configuration for operational inspection.

Usage:
    python -m scripts.print_hrr_config
"""
import json

from somabrain.config import get_config
from somabrain.quantum import HRRConfig

cfg = get_config()
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
                "binding_method": qcfg.binding_method,
                "sparsity": qcfg.sparsity,
                "binary_mode": qcfg.binary_mode,
                "mix": qcfg.mix,
                "roles_unitary": qcfg.roles_unitary,
            },
            indent=2,
        )
    )
