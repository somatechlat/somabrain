import logging
from typing import Any

logger = logging.getLogger(__name__)

# Try to import the Rust extension
try:
    import somabrain_rs as _rust

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    _rust = None  # type: ignore
    logger.warning(
        "Rust implementation 'somabrain_rs' not available. Falling back to Python defaults."
    )


def get_rust_module() -> Any:
    """Get the raw Rust module or raise ImportError if not available."""
    if not RUST_AVAILABLE:
        raise ImportError(
            "The 'somabrain_rs' module is not compiled or installed. "
            "Please run './scripts/build_rust.sh' to build the extension."
        )
    return _rust


def is_rust_available() -> bool:
    """Check if the Rust backend is available."""
    return RUST_AVAILABLE
