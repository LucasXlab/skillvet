"""Build-only regressions: anonymous archives preserve content, mode and paths."""

import gzip
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "pyproject.toml").is_file():
    pytest.skip(
        "Source-packaging regressions require a source checkout; wheel core tests are separate",
        allow_module_level=True,
    )
SPEC = importlib.util.spec_from_file_location("anonymous_build_backend", ROOT / "_build_backend.py")
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


def make_archive(path, entries, variant=1):
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="synthetic-host-build-name", fileobj=raw, mode="wb", mtime=variant
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                directory = tarfile.TarInfo("example-1.0")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                directory.uid = 123 + variant
                directory.gid = 456 + variant
                directory.uname = "synthetic-owner"
                directory.gname = "synthetic-group"
                archive.addfile(directory)
                for name, data, mode, kind in entries:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.mode = mode
                    info.size = len(data) if kind == tarfile.REGTYPE else 0
                    info.uid, info.gid = 789 + variant, 987 + variant
                    info.uname, info.gname = "synthetic-owner", "synthetic-group"
                    info.mtime = 12.5 + variant
                    info.pax_headers = {
                        "comment": "synthetic host identity",
                        "uname": "synthetic-owner",
                        "uid": str(info.uid),
                    }
                    if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                        info.linkname = "target.txt"
                    archive.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)


def inspect_archive(path):
    raw = path.read_bytes()
    assert raw[:3] == b"\x1f\x8b\x08"
    assert raw[3] == 0  # No optional gzip filename, comment, extra, or header CRC.
    assert raw[4:8] == b"\0\0\0\0"
    assert raw[9] == 255  # Generic OS, not a build-host platform identity.
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            assert (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
            assert member.mtime == 0
            assert set(member.pax_headers) <= {"path", "size"}
        return {
            member.name: (
                member.mode,
                archive.extractfile(member).read() if member.isreg() else None,
            )
            for member in members
        }


def test_normalization_is_reproducible_and_preserves_long_unicode_paths_and_modes(tmp_path):
    long_name = "example-1.0/docs/" + "long-" * 40 + "/说明.txt"
    entries = [
        ("example-1.0/run.sh", b"#!/bin/sh\nexit 0\n", 0o755, tarfile.REGTYPE),
        (long_name, "synthetic long-path content".encode(), 0o640, tarfile.REGTYPE),
    ]
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    make_archive(first, entries, variant=1)
    make_archive(second, entries, variant=2)
    backend._normalize_sdist(first)
    backend._normalize_sdist(second)
    assert first.read_bytes() == second.read_bytes()
    contents = inspect_archive(first)
    assert contents[long_name] == (0o640, entries[1][1])
    assert contents["example-1.0/run.sh"] == (0o755, entries[0][1])
    assert contents["example-1.0/_build_backend.py"][1] == (ROOT / "_build_backend.py").read_bytes()


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "example-1.0/../escape",
        "C:/escape",
        "example-1.0\\escape",
        "another-root/file",
    ],
)
def test_unsafe_member_paths_are_rejected_without_partial_replacement(tmp_path, name):
    path = tmp_path / "bad.tar.gz"
    make_archive(path, [(name, b"synthetic", 0o644, tarfile.REGTYPE)])
    before = path.read_bytes()
    with pytest.raises(ValueError):
        backend._normalize_sdist(path)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".anonymous-sdist-*"))


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE]
)
def test_links_and_special_files_are_rejected_instead_of_silently_removed(tmp_path, kind):
    path = tmp_path / "bad.tar.gz"
    make_archive(path, [("example-1.0/entry", b"", 0o644, kind)])
    with pytest.raises(ValueError):
        backend._normalize_sdist(path)


def test_duplicate_and_privileged_members_are_rejected(tmp_path):
    for entries in (
        [
            ("example-1.0/same", b"one", 0o644, tarfile.REGTYPE),
            ("example-1.0/same", b"two", 0o644, tarfile.REGTYPE),
        ],
        [("example-1.0/privileged", b"synthetic", 0o4755, tarfile.REGTYPE)],
    ):
        path = tmp_path / "bad.tar.gz"
        make_archive(path, entries)
        with pytest.raises(ValueError):
            backend._normalize_sdist(path)


def test_standard_sdist_hook_normalizes_every_returned_archive(tmp_path, monkeypatch):
    def upstream(directory, config_settings):
        path = Path(directory) / "example-1.0.tar.gz"
        make_archive(path, [("example-1.0/module.py", b"VALUE = 1\n", 0o644, tarfile.REGTYPE)])
        return path.name

    monkeypatch.setattr(backend._delegate, "build_sdist", upstream)
    result = backend.build_sdist(str(tmp_path), {"synthetic": "setting"})
    assert result == "example-1.0.tar.gz"
    assert inspect_archive(tmp_path / result)["example-1.0/module.py"] == (0o644, b"VALUE = 1\n")


def test_failed_sdist_hook_does_not_leave_identity_bearing_result(tmp_path, monkeypatch):
    def upstream(directory, config_settings):
        path = Path(directory) / "example-1.0.tar.gz"
        make_archive(path, [("../unsafe", b"synthetic", 0o644, tarfile.REGTYPE)])
        return path.name

    monkeypatch.setattr(backend._delegate, "build_sdist", upstream)
    with pytest.raises(ValueError):
        backend.build_sdist(str(tmp_path))
    assert not (tmp_path / "example-1.0.tar.gz").exists()
