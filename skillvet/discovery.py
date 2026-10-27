"""Deterministic discovery of supported assets and static local script references."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .filesystem import ReadError, SafeReader
from .ignore import is_ignored, load_ignore_patterns
from .metadata import MetadataError, parse_frontmatter, parse_json, validate_config
from .redact import collect_secrets, redact_text

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "target",
}
INSTRUCTION_NAMES = {
    "skill.md",
    "claude.md",
    "agents.md",
    "gemini.md",
    ".cursorrules",
    ".windsurfrules",
    ".clinerules",
    "copilot-instructions.md",
}
HOOK_CONFIG_NAMES = {"hooks.json", ".claude/settings.json", ".claude/settings.local.json"}
MCP_CONFIG_NAMES = {
    ".mcp.json",
    "mcp.json",
    ".vscode/mcp.json",
    "claude_desktop_config.json",
    ".cursor/mcp.json",
}
MANIFEST_NAMES = {".claude-plugin/plugin.json", "plugin.json"}
SCRIPT_EXTENSIONS = {".sh", ".bash", ".zsh", ".ps1", ".py", ".js", ".mjs", ".ts", ".rb", ".pl"}


@dataclass
class ScannedFile:
    path: str
    relpath: str
    kind: str
    text: str = ""
    data: Optional[dict] = None
    lines: List[str] = field(default_factory=list)
    locations: dict = field(default_factory=dict)

    def __post_init__(self):
        self.secret_values = collect_secrets(self.text, self.data)

    def snippet(self, line_no: int, width: int = 100) -> str:
        text = self.lines[line_no - 1].strip() if 1 <= line_no <= len(self.lines) else ""
        text = redact_text(text, self.secret_values)
        return text[: width - 1] + "…" if len(text) > width else text


def classify(root: str, path: str) -> Optional[str]:
    rel = os.path.relpath(path, root).replace(os.sep, "/").lower()
    name = os.path.basename(path).lower()
    if name in INSTRUCTION_NAMES or ("skills" in rel.split("/")[:-1] and name.endswith(".md")):
        return "instruction"
    for names, kind in [
        (HOOK_CONFIG_NAMES, "hook-config"),
        (MCP_CONFIG_NAMES, "mcp-config"),
        (MANIFEST_NAMES, "manifest"),
    ]:
        if any(rel == value or rel.endswith("/" + value) for value in names):
            return kind
    if os.path.splitext(name)[1] in SCRIPT_EXTENSIONS:
        if set(rel.split("/")[:-1]) & {
            "skills",
            ".claude",
            ".agents",
            "hooks",
            ".cursor",
            ".codex",
            "scripts",
            "bin",
            ".hooks",
        }:
            return "script"
    return None


def _commands(data):
    if isinstance(data, dict):
        command = data.get("command", data.get("cmd"))
        if isinstance(command, str):
            args = data.get("args", [])
            yield (
                " ".join([command, *[shlex.quote(a) for a in args]])
                if isinstance(args, list)
                else command
            )
        for key, value in data.items():
            if key == "scripts" and isinstance(value, dict):
                yield from (x for x in value.values() if isinstance(x, str))
            yield from _commands(value)
    elif isinstance(data, list):
        for value in data:
            yield from _commands(value)


class Discovery:
    """Coverage receipts accompany every exclusion and incomplete selected file."""

    def __init__(
        self,
        root,
        patterns=(),
        strict=False,
        max_files=10_000,
        max_file_bytes=1_048_576,
        max_total_bytes=16_777_216,
    ):
        self.root = os.path.abspath(root)
        self.patterns = list(patterns)
        self.caller_patterns = set(patterns)
        self.strict = strict
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.files = []
        self.errors = []
        self.skipped = []
        self.notes = []
        self.bytes_read = 0
        self._seen = set()
        self.reader = None

    def run(self):
        try:
            self.reader = SafeReader(self.root, self.max_file_bytes, self.max_total_bytes)
            if not self.strict:
                self.patterns += load_ignore_patterns(self.root, self.reader, self.errors)
            visited = 0
            stop = False
            for directory, dirs, names in os.walk(
                self.root,
                followlinks=False,
                onerror=lambda _: self.errors.append("directory traversal failed"),
            ):
                safe_dirs = []
                for name in sorted(dirs):
                    rel = os.path.relpath(os.path.join(directory, name), self.root)
                    if name in SKIP_DIRS:
                        continue
                    if is_ignored(rel + "/", self.patterns):
                        self._skip(rel, "path ignore (directory)")
                    elif Path(directory, name).is_symlink():
                        self.errors.append(f"{rel}: directory symbolic link refused")
                    else:
                        safe_dirs.append(name)
                dirs[:] = safe_dirs
                visited += len(dirs) + len(names)
                if visited > 50_000:
                    self.errors.append("directory entry limit exceeded (50000)")
                    break
                for name in sorted(names):
                    path = os.path.join(directory, name)
                    kind = classify(self.root, path)
                    if kind:
                        self._load(os.path.relpath(path, self.root), kind)
                    if len(self._seen) > self.max_files:
                        stop = True
                        break
                if stop:
                    break
            self.bytes_read = self.reader.bytes_read
        except (ReadError, OSError) as exc:
            self.errors.append(str(exc))
        finally:
            if self.reader:
                self.reader.close()
        self.files.sort(key=lambda f: f.relpath)
        return self

    def _skip(self, rel, reason):
        for item in self.skipped:
            if item["path"] == rel or (
                item["reason"].endswith("(directory)") and rel.startswith(item["path"] + os.sep)
            ):
                return
        probe = rel + "/" if reason.endswith("(directory)") else rel
        matched = [p for p in self.patterns if is_ignored(probe, [p])]
        source = (
            "caller --ignore"
            if any(p in self.caller_patterns for p in matched)
            else "target .skillvetignore"
        )
        self.skipped.append({"path": rel, "reason": reason, "source": source, "patterns": matched})

    def _load(self, rel, kind="script"):
        rel = os.path.normpath(rel)
        if rel in self._seen:
            return
        self._seen.add(rel)
        if len(self._seen) > self.max_files:
            self.errors.append(f"selected file limit exceeded ({self.max_files})")
            return
        if set(Path(rel).parts[:-1]) & SKIP_DIRS:
            self.skipped.append(
                {"path": rel, "reason": "built-in excluded directory", "source": "scanner policy"}
            )
            return
        if is_ignored(rel, self.patterns):
            self._skip(rel, "path ignore")
            return
        try:
            text = self.reader.read(rel)
            data, locations = None, {}
            if kind in {"hook-config", "mcp-config", "manifest"}:
                data, locations = parse_json(text)
                validate_config(data, kind)
            elif kind == "instruction":
                data, locations = parse_frontmatter(text)
            self.files.append(
                ScannedFile(
                    os.path.join(self.root, rel),
                    rel,
                    kind,
                    text,
                    data,
                    text.splitlines(),
                    locations,
                )
            )
            if data:
                for command in _commands(data):
                    self._follow(command, rel)
        except (ReadError, MetadataError) as exc:
            self.errors.append(f"{rel}: {exc}")

    def _follow(self, command, origin):
        if any(c in command for c in "$`|;&><\n\r"):
            self.notes.append(f"{origin}: dynamic/shell command was not followed")
            return
        try:
            tokens = shlex.split(command)
        except ValueError:
            self.errors.append(f"{origin}: malformed command quoting")
            return
        for token in tokens:
            if os.path.splitext(token)[1].lower() not in SCRIPT_EXTENSIONS:
                continue
            if token.startswith(("/", "~")) or "://" in token:
                self.notes.append(f"{origin}: external script reference was not followed")
                continue
            candidates = [
                os.path.normpath(token),
                os.path.normpath(os.path.join(os.path.dirname(origin), token)),
            ]
            candidates = list(dict.fromkeys(candidates))
            candidates = [p for p in candidates if p != ".." and not p.startswith(".." + os.sep)]
            if not candidates:
                self.notes.append(f"{origin}: outside-root script reference was not followed")
                continue
            selected = next(
                (p for p in candidates if os.path.lexists(os.path.join(self.root, p))), None
            )
            if selected is None:
                self.notes.append(f"{origin}: missing local script reference (not followed)")
                continue
            self._load(selected)


def discover(root: str) -> List[ScannedFile]:
    """Compatibility API. Use Discovery for complete diagnostics/receipts."""
    return Discovery(root).run().files
