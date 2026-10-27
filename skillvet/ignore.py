"""Suppression support: .skillvetignore files and inline comments."""

from __future__ import annotations

import fnmatch
import os
import re
from typing import List, Set

from .filesystem import ReadError, SafeReader

INLINE_RE = re.compile(r"skillvet:\s*ignore\s+([A-Za-z0-9_,\s]+)", re.IGNORECASE)


def parse_inline(line: str) -> Set[str]:
    """Return rule ids suppressed on this line, e.g. '<!-- skillvet:ignore SV005 -->'."""
    ids: Set[str] = set()
    for match in INLINE_RE.finditer(line):
        for token in match.group(1).split(","):
            token = token.strip().upper()
            if token:
                ids.add(token)
    return ids


def load_ignore_patterns(root: str, reader=None, errors=None) -> List[str]:
    patterns: List[str] = []
    own_reader = reader is None
    errors = errors if errors is not None else []
    try:
        if not os.path.lexists(os.path.join(root, ".skillvetignore")):
            return patterns
        reader = reader or SafeReader(root)
        text = reader.read(".skillvetignore")
        patterns = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except ReadError as exc:
        errors.append(f".skillvetignore: {exc}")
    finally:
        if own_reader and reader:
            reader.close()
    return patterns


def is_ignored(relpath: str, patterns: List[str]) -> bool:
    normalized = relpath.replace(os.sep, "/")
    for pattern in patterns:
        pat = pattern.replace(os.sep, "/")
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(normalized, "*/" + pat.lstrip("/")):
            return True
        if pat.endswith("/") and normalized.startswith(pat):
            return True
    return False
