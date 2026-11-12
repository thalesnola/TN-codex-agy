def clamp(value, lower, upper):
    """Limit value to the inclusive interval [lower, upper]."""
    if lower > upper:
        raise ValueError('lower must not exceed upper')
    return min(lower, max(upper, value))
