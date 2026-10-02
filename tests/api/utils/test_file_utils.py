"""File hashing."""

import hashlib
from pathlib import Path

from casm.api.utils.file_utils import file_sha256


class TestFileSha256:
    def test_hashes_file_contents(self, tmp_path: Path) -> None:
        path: Path = tmp_path / "f.txt"
        path.write_bytes(b"abc")
        assert file_sha256(path=path) == hashlib.sha256(b"abc").hexdigest()

    def test_missing_file_is_none(self, tmp_path: Path) -> None:
        assert file_sha256(path=tmp_path / "missing.txt") is None
