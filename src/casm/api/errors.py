"""Domain errors raised below the HTTP layer; `app.py` maps them to responses."""


class NotFoundError(Exception):
    """A requested record does not exist."""
