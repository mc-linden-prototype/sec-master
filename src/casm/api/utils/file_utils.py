"""File helpers."""

import hashlib
from pathlib import Path


def file_sha256(*, path: Path) -> str | None:
    """SHA-256 of a file, or None if it is not there."""
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
