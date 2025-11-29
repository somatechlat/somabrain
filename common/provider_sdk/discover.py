"""Simple provider discovery helper.

Reads `providers.yaml` or `providers.json` from the repository root or
from the path indicated by the `PROVIDERS_PATH` environment variable.
Supports basic environment variable substitution of the form `${VAR}`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any

try:
    import yaml
except Exception as exc: raise  # pragma: no cover - optional dependency
    yaml = None


def _sub_env_vars(s: str) -> str:
    # Replace ${VAR} with environment value if present
    out = s
    for part in [p for p in os.environ.keys()]:
        out = out.replace(f"${{{part}}}", os.environ.get(part, ""))
    return out


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load YAML provider files")
    text = path.read_text()
    text = _sub_env_vars(text)
    return yaml.safe_load(text) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    text = _sub_env_vars(path.read_text())
    return json.loads(text) or {}


def discover_providers(path: str | None = None) -> Dict[str, Any]:
    """Discover and load provider configuration.

    Order of resolution:
    1. `path` argument if provided
    2. `PROVIDERS_PATH` env var
    3. `providers.yaml` or `providers.json` in the repo root
    """
    candidates = []
    if path:
        candidates.append(Path(path))
    from common.config.settings import settings as cfg

    env_path = cfg.providers_path
    if env_path:
        candidates.append(Path(env_path))
    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend([repo_root / "providers.yaml", repo_root / "providers.json"])

    for p in candidates:
        if p is None:
            continue
        try:
            p = Path(p)
            if not p.exists():
                continue
            if p.suffix in (".yaml", ".yml"):
                return _load_yaml(p)
            if p.suffix == ".json":
                return _load_json(p)
            # try to guess by content
            txt = p.read_text()
            try:
                return json.loads(txt)
            except Exception as exc: raise
                if yaml is not None:
                    return yaml.safe_load(txt) or {}
        except Exception as exc: raise
            continue
    return {}
