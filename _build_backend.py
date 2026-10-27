"""Setuptools PEP 517 adapter with reproducible, anonymous source archives.

Only build dependencies are imported here. Runtime packages do not import this
module. Source archives retain regular file bytes/modes and safe long paths, but
never inherit the build machine's tar ownership, PAX metadata, or gzip filename.
"""

from __future__ import annotations

import gzip
import io
import os
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from setuptools import build_meta as _delegate

get_requires_for_build_wheel = _delegate.get_requires_for_build_wheel
get_requires_for_build_sdist = _delegate.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _delegate.prepare_metadata_for_build_wheel
build_wheel = _delegate.build_wheel
get_requires_for_build_editable = _delegate.get_requires_for_build_editable
prepare_metadata_for_build_editable = _delegate.prepare_metadata_for_build_editable
build_editable = _delegate.build_editable


def _safe_name(name):
    stripped = name.rstrip("/")
    if (
        not stripped
        or "\\" in stripped
        or "\x00" in stripped
        or stripped.startswith("/")
        or (len(stripped) >= 2 and stripped[0].isalpha() and stripped[1] == ":")
        or any(part in ("", ".", "..") for part in stripped.split("/"))
    ):
        raise ValueError("source archive contains an unsafe member path")
    return stripped


def _clean_info(member, name):
    if not (member.isdir() or member.isreg()) or member.sparse is not None:
        raise ValueError("source archive links, sparse files, and special files are unsupported")
    if member.size < 0 or (member.isdir() and member.size):
        raise ValueError("source archive has an invalid member size")
    if member.mode & ~0o777:
        raise ValueError("source archive has unsupported privileged permissions")
    clean = tarfile.TarInfo(name)
    clean.type = tarfile.DIRTYPE if member.isdir() else tarfile.REGTYPE
    clean.size = 0 if member.isdir() else member.size
    clean.mode = member.mode
    clean.uid = clean.gid = 0
    clean.uname = clean.gname = ""
    clean.mtime = 0
    clean.linkname = ""
    clean.devmajor = clean.devminor = 0
    clean.pax_headers = {}
    return clean


def _normalize_sdist(archive):
    """Atomically normalize one freshly built archive; fail rather than omit data."""
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("source archive must be a regular file")
    backend = Path(__file__)
    backend_bytes = backend.read_bytes()
    temporary = None
    try:
        with tarfile.open(archive, "r:gz") as source:
            members = source.getmembers()
            if not members:
                raise ValueError("source archive is empty")
            indexed = {}
            roots = set()
            for member in members:
                name = _safe_name(member.name)
                if name in indexed:
                    raise ValueError("source archive contains duplicate member paths")
                _clean_info(member, name)
                indexed[name] = member
                roots.add(PurePosixPath(name).parts[0])
            if len(roots) != 1:
                raise ValueError("source archive must have exactly one top-level directory")
            root = next(iter(roots))
            if root in indexed and not indexed[root].isdir():
                raise ValueError("source archive top-level member must be a directory")
            backend_name = root + "/" + backend.name
            if backend_name in indexed:
                member = indexed[backend_name]
                if not member.isreg() or member.size != len(backend_bytes):
                    raise ValueError("source archive backend does not match the current source")
                with source.extractfile(member) as handle:
                    if handle.read() != backend_bytes:
                        raise ValueError("source archive backend does not match the current source")
            descriptor, filename = tempfile.mkstemp(prefix=".anonymous-sdist-", dir=archive.parent)
            temporary = Path(filename)
            with os.fdopen(descriptor, "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                    with tarfile.open(
                        fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
                    ) as target:
                        for name in sorted(set(indexed) | {backend_name}):
                            if name == backend_name and name not in indexed:
                                info = tarfile.TarInfo(name)
                                info.size = len(backend_bytes)
                                info.mode = stat.S_IMODE(backend.stat().st_mode)
                                target.addfile(_clean_info(info, name), io.BytesIO(backend_bytes))
                                continue
                            member = indexed[name]
                            info = _clean_info(member, name)
                            if member.isdir():
                                target.addfile(info)
                            else:
                                with source.extractfile(member) as handle:
                                    target.addfile(info, handle)
                raw.flush()
                os.fsync(raw.fileno())
        os.chmod(temporary, stat.S_IMODE(archive.stat().st_mode))
        os.replace(temporary, archive)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_sdist(sdist_directory, config_settings=None):
    filename = _delegate.build_sdist(sdist_directory, config_settings)
    if Path(filename).name != filename or not filename.endswith(".tar.gz"):
        raise ValueError("build backend returned an unsupported source archive name")
    archive = Path(sdist_directory) / filename
    try:
        _normalize_sdist(archive)
    except BaseException:
        # Do not leave an unsafe, identity-bearing build result in the output
        # directory after reporting that the source build failed.
        archive.unlink(missing_ok=True)
        raise
    return filename
