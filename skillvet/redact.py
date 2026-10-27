"""Shared report redaction; heuristic masking is not a privacy guarantee."""

from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    re.compile(r"\b(?:gsk_|glpat-)[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bpypi-[A-Za-z0-9_\-]{16,}"),
]
ASSIGNMENT = re.compile(
    r"""(?i)["']?\b(?:api[_-]?key|secret|token|password|passwd|credential)s?["']?\s*[:=]\s*["']([^"'\r\n]{4,})["']"""
)
URL_AUTH = re.compile(r"(https?://)[^\s/@]+(?::[^\s/@]*)?@", re.I)
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")


def collect_secrets(text, data=None):
    values = {m.group(0) for p in SECRET_PATTERNS for m in p.finditer(text)}
    values.update(m.group(1) for m in ASSIGNMENT.finditer(text))

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if re.search(r"(?i)(key|token|secret|password|credential)", str(key)):
                    if isinstance(value, str) and len(value) >= 4 and not value.startswith("$"):
                        values.add(value)
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    return values


def redact_text(text: str, secrets=(), controls=True) -> str:
    for value in sorted(secrets, key=len, reverse=True):
        if value:
            text = text.replace(value, "<redacted>")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<redacted>", text)
    text = ASSIGNMENT.sub(lambda m: m.group(0).replace(m.group(1), "<redacted>"), text)
    text = URL_AUTH.sub(r"\1<redacted>@", text)
    return CONTROL.sub(lambda m: f"\\u{ord(m.group(0)):04x}", text) if controls else text
