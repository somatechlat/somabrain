from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from numpy.testing import assert_allclose

from somabrain.predictors.base import load_operator_from_file


def test_load_operator_from_adjacency_tmpfile(tmp_path: Path):
    # Simple 3-node line graph adjacency
    A = np.array(
        [
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 0.0],
        ]
    )
    p = tmp_path / "graph.json"
    p.write_text(json.dumps({"adjacency": A.tolist()}))
    apply_A, dim = load_operator_from_file(str(p))
    assert dim == 3
    # Laplacian for line graph should be [[1,-1,0],[-1,2,-1],[0,-1,1]]
    v = np.array([1.0, 0.0, 0.0])
    out = apply_A(v)
    assert_allclose(out, np.array([1.0, -1.0, 0.0]))


def test_load_operator_from_laplacian_tmpfile(tmp_path: Path):
    L = np.array(
        [
            [1.0, -1.0, 0.0],
            [-1.0, 2.0, -1.0],
            [0.0, -1.0, 1.0],
        ]
    )
    p = tmp_path / "graphL.json"
    p.write_text(json.dumps({"laplacian": L.tolist()}))
    apply_A, dim = load_operator_from_file(str(p))
    assert dim == 3
    v = np.array([0.0, 1.0, 0.0])
    out = apply_A(v)
    # L * [0,1,0] = [-1,2,-1]
    assert_allclose(out, np.array([-1.0, 2.0, -1.0]))
