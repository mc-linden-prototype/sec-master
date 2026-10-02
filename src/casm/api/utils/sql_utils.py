"""Helpers for building SQL from user text."""

ESCAPE_CLAUSE: str = "ESCAPE '\\'"


def contains(*, text: str) -> str:
    """Escape LIKE wildcards in user text and wrap it for a contains search."""
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def prefix(*, text: str) -> str:
    """Escape LIKE wildcards in user text and wrap it for a starts-with search."""
    return contains(text=text)[1:]
