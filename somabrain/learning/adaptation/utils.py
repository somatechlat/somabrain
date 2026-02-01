def clamp(value: float, lower: float, upper: float) -> float:
    """Execute clamp.

    Args:
        value: The value.
        lower: The lower.
        upper: The upper.
    """
    return min(max(value, lower), upper)
