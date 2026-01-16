"""
Type stubs for numpy to resolve Pyright shape/dtype attribute errors.
"""

from typing import Any

class dtype:
    """NumPy dtype type stub."""

    name: str
    kind: str

class ndarray:
    """NumPy ndarray type stub with shape and dtype attributes."""

    shape: tuple[int, ...]
    dtype: dtype
    ndim: int
    size: int

    def __getitem__(self, key: Any) -> "ndarray": ...
    def __add__(self, other: Any) -> "ndarray": ...
    def tolist(self) -> list: ...

def concatenate(arrays: list, axis: int = 0) -> ndarray: ...
def normalize_vector(v: Any, dtype: dtype | None = None) -> ndarray: ...

float32: dtype
float64: dtype
