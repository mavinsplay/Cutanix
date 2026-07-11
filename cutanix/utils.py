__all__ = ["get_bool_env"]


def get_bool_env(value):
    """Convert any truthy/falsy value to bool.

    Accepts: bool, int (0/1), str ("true"/"false"/"yes"/"no"/"1"/"0" etc.)
    Returns True for: True, 1, "true", "t", "yes", "y", "1", "on"
    Returns False for everything else, including None.
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value != 0

    if isinstance(value, str):
        return value.strip().lower() in ("true", "t", "yes", "y", "1", "on")

    return False
