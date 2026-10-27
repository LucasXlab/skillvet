"""Explicit metadata subset with source locations, never a general YAML loader."""

from __future__ import annotations

import json
import re


class MetadataError(ValueError):
    pass


def _scalar(raw):
    raw = raw.strip()
    if not raw:
        raise MetadataError("empty scalar in frontmatter")
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise MetadataError("unsupported quoted frontmatter scalar") from exc
        if not isinstance(value, str):
            raise MetadataError("frontmatter scalar must be a string")
        return value
    if raw.startswith("'"):
        if not raw.endswith("'") or len(raw) < 2:
            raise MetadataError("unterminated frontmatter string")
        return raw[1:-1].replace("''", "'")
    if any(c in raw for c in "[]{}&*!|>\"'") or re.search(r":\s", raw):
        raise MetadataError("unsupported YAML syntax; use plain/quoted strings and string lists")
    value = raw.split(" #", 1)[0].strip()
    if value.lower() in {"true", "false", "null", "~"} or re.fullmatch(
        r"[-+]?\d+(?:\.\d+)?", value
    ):
        raise MetadataError(
            "implicit numeric/boolean/null YAML values are not supported; quote strings"
        )
    return value


def _inline_list(raw):
    if not raw.endswith("]"):
        raise MetadataError("unterminated frontmatter list")
    text = raw[1:-1]
    parts, start, quote, escaped = [], 0, None, False
    for i, char in enumerate(text):
        if quote:
            if char == quote and not escaped:
                quote = None
            escaped = char == "\\" and not escaped
        elif char in "\"'":
            quote = char
        elif char == ",":
            parts.append(text[start:i])
            start = i + 1
    if quote:
        raise MetadataError("unterminated frontmatter string")
    parts.append(text[start:])
    if any(not p.strip() for p in parts[:-1]):
        raise MetadataError("empty frontmatter list item")
    return [_scalar(p) for p in parts if p.strip()]


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, {}
    data, locations, current = {}, {}, None
    for n, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            return data, locations
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+-\s+", line):
            if current is None or not isinstance(data[current], list):
                raise MetadataError(f"frontmatter line {n}: unexpected list item")
            value = _scalar(re.sub(r"^\s+-\s+", "", line))
            index = len(data[current])
            data[current].append(value)
            locations[(current, index)] = n
            continue
        match = re.fullmatch(r"([A-Za-z][\w-]*):\s*(.*)", line)
        if not match:
            raise MetadataError(f"frontmatter line {n}: unsupported syntax")
        key, raw = match.groups()
        if key in data:
            raise MetadataError(f"frontmatter line {n}: duplicate field")
        current = key
        value = _inline_list(raw) if raw.startswith("[") else (_scalar(raw) if raw else [])
        data[key] = value
        locations[(key,)] = n
        if isinstance(value, list):
            for index in range(len(value)):
                locations[(key, index)] = n
    raise MetadataError("frontmatter is missing its closing ---")


def parse_json(text):
    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise MetadataError("duplicate JSON key")
            data[key] = value
        return data

    def invalid_constant(_):
        raise MetadataError("non-finite JSON constant")

    try:
        data = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise MetadataError("invalid JSON configuration") from exc
    if not isinstance(data, dict):
        raise MetadataError("configuration must be a JSON object")
    locations = {}
    decoder = json.JSONDecoder()

    def whitespace(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def walk(pos, path, depth=0):
        if depth > 64:
            raise MetadataError("configuration nesting exceeds 64 levels")
        pos = whitespace(pos)
        locations[path] = text.count("\n", 0, pos) + 1
        if text[pos] == "{":
            pos = whitespace(pos + 1)
            while text[pos] != "}":
                key, pos = decoder.raw_decode(text, pos)
                pos = walk(whitespace(pos) + 1, path + (key,), depth + 1)
                pos = whitespace(pos)
                if text[pos] != ",":
                    break
                pos = whitespace(pos + 1)
            return pos + 1
        if text[pos] == "[":
            pos, index = whitespace(pos + 1), 0
            while text[pos] != "]":
                pos = walk(pos, path + (index,), depth + 1)
                index += 1
                pos = whitespace(pos)
                if text[pos] != ",":
                    break
                pos = whitespace(pos + 1)
            return pos + 1
        return decoder.raw_decode(text, pos)[1]

    walk(0, ())
    return data, locations


def grants(data, locations=None):
    """Only documented grant fields; deny/description strings are never grants."""
    if not isinstance(data, dict):
        return []
    locations = locations or {}
    if "permissions" in data and not isinstance(data["permissions"], dict):
        raise MetadataError("permissions must be an object")
    result = []
    for path in [
        ("allowed-tools",),
        ("allowed_tools",),
        ("permissions", "allow"),
        ("permissions", "tools"),
    ]:
        node = data
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            continue
        if isinstance(node, str):
            node = [node]
        if not isinstance(node, list) or any(not isinstance(x, str) for x in node):
            raise MetadataError("permission grant must be a string or a list of strings")
        for index, value in enumerate(node):
            result.append((path, value, locations.get(path + (index,), locations.get(path, 1))))
    return result


def validate_config(data, kind):
    grants(data)
    for key in ("mcpServers", "servers", "mcp"):
        if key not in data:
            continue
        if not isinstance(data[key], dict):
            raise MetadataError("MCP server collection must be an object")
        for cfg in data[key].values():
            if not isinstance(cfg, dict):
                raise MetadataError("MCP server entry must be an object")
            for field in ("command", "url", "baseUrl", "endpoint"):
                if field in cfg and not isinstance(cfg[field], str):
                    raise MetadataError(f"MCP {field} must be a string")
            if "args" in cfg and (
                not isinstance(cfg["args"], list)
                or any(not isinstance(a, str) for a in cfg["args"])
            ):
                raise MetadataError("MCP args must be a list of strings")
            if "env" in cfg and (
                not isinstance(cfg["env"], dict)
                or any(not isinstance(v, str) for v in cfg["env"].values())
            ):
                raise MetadataError("MCP env must be an object of strings")
    if kind == "mcp-config" and not any(key in data for key in ("mcpServers", "servers", "mcp")):
        raise MetadataError("unsupported MCP configuration schema")

    def walk(node, depth=0):
        if depth > 64:
            raise MetadataError("configuration nesting exceeds 64 levels")
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"command", "cmd"}:
                    if not isinstance(value, str):
                        raise MetadataError("command field must be a string")
                    args = node.get("args", [])
                    if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
                        raise MetadataError("command args must be a list of strings")
                walk(value, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)

    walk(data)
