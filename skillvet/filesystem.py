"""Bounded, descriptor-relative reads. Nothing discovered is ever executed."""

from __future__ import annotations

import os
import stat
from pathlib import Path


class ReadError(ValueError):
    """A selected file could not be read within the declared boundary."""


class SafeReader:
    def __init__(self, root: str, max_file_bytes=1_048_576, max_total_bytes=16_777_216):
        self.root = os.path.abspath(root)
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.bytes_read = 0
        self.fd = None
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise ReadError("secure descriptor-relative reading requires a POSIX host")
        try:
            # Resolve parents only: the requested root itself must not be a link.
            if Path(self.root).is_symlink():
                raise ReadError("scan root must not be a symbolic link")
            self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as exc:
            raise ReadError("cannot open scan root as a regular directory") from exc

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def read(self, relpath: str) -> str:
        parts = Path(relpath).parts
        if not parts or Path(relpath).is_absolute() or any(p in {".", ".."} for p in parts):
            raise ReadError("path is outside the scan root")
        current = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
                os.close(current)
                current = child
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode):
                    raise ReadError("not a regular file (links and special files are refused)")
                if info.st_size > self.max_file_bytes:
                    raise ReadError("file exceeds the per-file byte limit")
                allowance = min(self.max_file_bytes, self.max_total_bytes - self.bytes_read)
                if allowance < 0 or info.st_size > allowance:
                    raise ReadError("scan exceeds the total byte limit")
                chunks = []
                size = 0
                while size <= allowance:
                    chunk = os.read(fd, min(65_536, allowance + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                if size > allowance:
                    raise ReadError("file grew beyond the scan byte limit")
                self.bytes_read += size
                return b"".join(chunks).decode("utf-8")
            finally:
                os.close(fd)
        except (OSError, UnicodeError) as exc:
            raise ReadError("unreadable, linked, non-UTF-8 or inaccessible file") from exc
        finally:
            os.close(current)
