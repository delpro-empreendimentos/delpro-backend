"""In-memory dev routing state. Ephemeral — resets on container restart."""

_active: bool = False


def is_active() -> bool:
    """Return whether dev routing is currently active."""
    return _active


def toggle() -> bool:
    """Toggle dev routing on/off. Returns the new state."""
    global _active
    _active = not _active
    return _active
