"""Rule definitions for skillvet.

Every rule is a pure function over a ScannedFile plus a small context object,
so rules are trivial to unit test and to extend. Each rule returns findings
with an explicit remediation and public references (OWASP LLM Top 10 etc.).
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

from .discovery import ScannedFile
from .metadata import grants
from .model import Finding, Severity
from .redact import ASSIGNMENT, SECRET_PATTERNS, redact_text

RuleFn = Callable[[ScannedFile, "ScanContext"], List[Finding]]


class ScanContext:
    """Shared state passed to every rule."""

    def __init__(self, root: str) -> None:
        self.root = root

    def make(
        self,
        rule_id: str,
        file: ScannedFile,
        line_no: int,
        snippet: str,
        confidence: str = "high",
    ) -> Finding:
        meta = RULES[rule_id]
        return Finding(
            rule_id=rule_id,
            severity=meta.severity,
            title=meta.title,
            path=file.relpath,
            line=line_no,
            snippet=snippet,
            remediation=meta.remediation,
            references=list(meta.references),
            confidence=confidence,
        )


class Rule:
    def __init__(
        self,
        rule_id: str,
        severity: Severity,
        title: str,
        remediation: str,
        references: List[str],
        kinds: List[str],
        check: RuleFn,
    ) -> None:
        self.id = rule_id
        self.severity = severity
        self.title = title
        self.remediation = remediation
        self.references = references
        self.kinds = kinds
        self.check = check


RULES: Dict[str, Rule] = {}


def register(
    rule_id: str,
    severity: Severity,
    title: str,
    remediation: str,
    references: List[str],
    kinds: List[str],
):
    def decorator(fn: RuleFn) -> RuleFn:
        RULES[rule_id] = Rule(rule_id, severity, title, remediation, references, kinds, fn)
        return fn

    return decorator


OWASP_LLM01 = "https://genai.owasp.org/llmrisk/llm01-prompt-injection/"
OWASP_LLM02 = "https://genai.owasp.org/llmrisk/llm02-sensitive-information-disclosure/"
OWASP_LLM05 = "https://genai.owasp.org/llmrisk/llm05-supply-chain-vulnerabilities/"
OWASP_LLM06 = "https://genai.owasp.org/llmrisk/llm06-excessive-agency/"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
DIRECTIVE_RE = re.compile(
    r"\b(ignore|disregard|forget|override|bypass|always|never|must|execute|run|send|upload|post|fetch|curl|wget|exfiltrate|delete|install|grant|secret|token|password|api[ _-]?key|http[s]?://)",
    re.IGNORECASE,
)

OVERRIDE_RE = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above|preceding)\s+(instructions?|prompts?|rules?)"
    r"|disregard\s+(your|all|any)\s+(instructions?|programming|rules?|training)"
    r"|you\s+are\s+now\s+(?:(?:a|an|the)\s+)?(?:unrestricted|unfiltered|jailbroken|dan)"
    r"\b|dan\s+mode|do\s+anything\s+now|no\s+(?:longer\s+)?(?:bound|restricted)\s+by"
    r"|reveal\s+your\s+(system\s+)?prompt|print\s+your\s+(system\s+)?prompt)",
    re.IGNORECASE,
)

INVISIBLE_RE = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]"
)

BASE64_BLOB_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{48,}={0,2}(?![A-Za-z0-9+/=])")
DECODE_CMD_RE = re.compile(
    r"(base64\s+(?:-d|--decode|-D)"
    r"|FromBase64String"
    r"|\batob\s*\("
    r"|Buffer\.from\([^)]*['\"]base64['\"]"
    r"|certutil\s+-decode"
    r"|openssl\s+(?:enc|base64)\s+-d)",
    re.IGNORECASE,
)

SENSITIVE_PATH_RE = re.compile(
    r"(~/\.ssh|~/\.aws|~/\.config/gcloud|/etc/passwd|/etc/shadow|id_rsa|id_ed25519"
    r"|\.env\b(?!\.example)|\.netrc|\.pgpass|keychain|login\.data|Cookies"
    r"|chrome/Default|\.kube/config|credentials\.json|\.git-credentials)",
)


EXFIL_URL_RE = re.compile(
    r"(https?://(?:webhook\.site|requestbin|hookbin|pipedream|ngrok\.io|pastebin\.com|paste\.ee"
    r"|transfer\.sh|file\.io|api\.telegram\.org/bot|discord(?:app)?\.com/api/webhooks"
    r"|[0-9]{1,3}(?:\.[0-9]{1,3}){3}))",
    re.IGNORECASE,
)

SEND_DATA_RE = re.compile(
    r"(?i)\b(send|upload|post|transmit|exfiltrate|forward|report)\b[^.\n]{0,80}\b(to|via)\s+(https?://|the\s+url|remote\s+server|external\s+endpoint)"
    r"|\b(collect|gather|harvest)\b[^.\n]{0,60}\b(user|personal|credential|token|secret)s?\b[^.\n]{0,60}\b(send|upload|post)\b",
)

PIPE_SHELL_RE = re.compile(r"(?i)(curl|wget|fetch)[^\n|]{0,200}\|\s*(sudo\s+)?(ba|z|fi)?sh\b")
EVAL_RE = re.compile(
    r"(?i)(\beval\s*\$\(|\beval\s+[\"']|powershell(?:\.exe)?\s+-(?:e|ec|en|encodedcommand)\b|\biex\s*\(|\bnc(t)?\s+-e\b|/dev/tcp/)"
)


# ---------------------------------------------------------------------------
# instruction-file rules
# ---------------------------------------------------------------------------


@register(
    "SV001",
    Severity.HIGH,
    "Hidden instruction inside an HTML comment",
    "Remove the comment or make the directive visible and reviewable. Agents execute "
    "commented-out instructions; comments are not a safe place for policy.",
    [OWASP_LLM01],
    ["instruction"],
)
def hidden_html_comment(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    text = file.text
    for match in HTML_COMMENT_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        if DIRECTIVE_RE.search(body):
            line_no = text[: match.start()].count("\n") + 1
            findings.append(ctx.make("SV001", file, line_no, file.snippet(line_no)))
    return findings


@register(
    "SV002",
    Severity.MEDIUM,
    "Prompt-override or jailbreak phrasing",
    "Remove override phrasing. Legitimate skills describe tasks, not attempts to "
    "redefine the agent's instructions.",
    [OWASP_LLM01],
    ["instruction"],
)
def override_phrasing(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if OVERRIDE_RE.search(line):
            findings.append(ctx.make("SV002", file, idx, file.snippet(idx)))
    return findings


@register(
    "SV003",
    Severity.HIGH,
    "Invisible or bidirectional Unicode characters",
    "Strip zero-width and bidi control characters. They can hide instructions from "
    "human reviewers while remaining visible to the model.",
    [OWASP_LLM01],
    ["instruction", "script"],
)
def invisible_unicode(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        match = INVISIBLE_RE.search(line)
        if match:
            codepoints = " ".join(f"U+{ord(c):04X}" for c in match.group(0))
            findings.append(
                Finding(
                    rule_id="SV003",
                    severity=RULES["SV003"].severity,
                    title=RULES["SV003"].title,
                    path=file.relpath,
                    line=idx,
                    snippet=f"hidden characters: {codepoints}",
                    remediation=RULES["SV003"].remediation,
                    references=list(RULES["SV003"].references),
                )
            )
    return findings


@register(
    "SV004",
    Severity.HIGH,
    "Encoded or obfuscated payload",
    "Do not ship encoded payloads. If a script needs data, commit it as readable text "
    "and explain what it is.",
    [OWASP_LLM01, OWASP_LLM05],
    ["instruction", "script"],
)
def encoded_payload(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if DECODE_CMD_RE.search(line):
            findings.append(ctx.make("SV004", file, idx, file.snippet(idx)))
            continue
        for match in BASE64_BLOB_RE.finditer(line):
            blob = match.group(0)
            if len(blob) >= 48:
                findings.append(
                    Finding(
                        rule_id="SV004",
                        severity=RULES["SV004"].severity,
                        title=RULES["SV004"].title,
                        path=file.relpath,
                        line=idx,
                        snippet=f"base64-looking blob ({len(blob)} chars): <encoded data omitted>",
                        remediation=RULES["SV004"].remediation,
                        references=list(RULES["SV004"].references),
                    )
                )
    return findings


@register(
    "SV005",
    Severity.CRITICAL,
    "Instruction to send data to an external endpoint",
    "Skills must not instruct the agent to transmit local data off-machine. Remove the "
    "instruction and publish the skill's data flow explicitly.",
    [OWASP_LLM02],
    ["instruction"],
)
def exfil_instruction(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if EXFIL_URL_RE.search(line) or SEND_DATA_RE.search(line):
            findings.append(ctx.make("SV005", file, idx, file.snippet(idx)))
    return findings


@register(
    "SV006",
    Severity.HIGH,
    "Reference to sensitive local paths",
    "Skills should stay inside the workspace. Reading SSH keys, cloud credentials or "
    "browser cookies is never required for a coding task.",
    [OWASP_LLM02],
    ["instruction", "script"],
)
def sensitive_paths(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if SENSITIVE_PATH_RE.search(line):
            findings.append(ctx.make("SV006", file, idx, file.snippet(idx)))
    return findings


@register(
    "SV007",
    Severity.HIGH,
    "Hardcoded credential in an agent file",
    "Rotate the exposed credential and move it to an environment variable or a secret "
    "manager. Never commit tokens into skills or configs.",
    [OWASP_LLM02],
    ["instruction", "hook-config", "mcp-config", "manifest"],
)
def hardcoded_secret(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        for pattern in [*SECRET_PATTERNS, ASSIGNMENT]:
            match = pattern.search(line)
            if match:
                redacted = redact_text(line, file.secret_values)
                findings.append(
                    Finding(
                        rule_id="SV007",
                        severity=RULES["SV007"].severity,
                        title=RULES["SV007"].title,
                        path=file.relpath,
                        line=idx,
                        snippet=redacted.strip()[:100],
                        remediation=RULES["SV007"].remediation,
                        references=list(RULES["SV007"].references),
                        confidence="medium",
                    )
                )
                break
    return findings


@register(
    "SV008",
    Severity.CRITICAL,
    "Obfuscated or piped remote code execution",
    "Never pipe network content into a shell. Fetch, inspect, then run explicitly.",
    [OWASP_LLM01, OWASP_LLM05],
    ["instruction", "script", "hook-config"],
)
def piped_execution(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if PIPE_SHELL_RE.search(line) or EVAL_RE.search(line):
            findings.append(ctx.make("SV008", file, idx, file.snippet(idx)))
    return findings


# ---------------------------------------------------------------------------
# permission rules (manifests / settings)
# ---------------------------------------------------------------------------


def _iter_tool_strings(file):
    return grants(file.data, file.locations)


def _find_line(file: ScannedFile, needle: str) -> int:
    for idx, line in enumerate(file.lines, start=1):
        if needle and needle in line:
            return idx
    return 1


@register(
    "SV010",
    Severity.MEDIUM,
    "Unrestricted shell tool granted",
    'Scope Bash to explicit command prefixes (e.g. "Bash(git status:*)") or drop it.',
    [OWASP_LLM06],
    ["manifest", "hook-config", "instruction"],
)
def unrestricted_bash(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    if not isinstance(file.data, dict):
        return findings
    for path, value, line_no in _iter_tool_strings(file):
        lower = value.strip().lower()
        if lower in {"bash", "shell", "bash(*)", "shell(*)", "computer", "computer(*)"}:
            findings.append(ctx.make("SV010", file, line_no, f"{'/'.join(path)}: {value}"))
    return findings


@register(
    "SV011",
    Severity.MEDIUM,
    "Unrestricted file write/edit tool granted",
    "Scope Write/Edit to the workspace directory instead of the whole filesystem.",
    [OWASP_LLM06],
    ["manifest", "hook-config", "instruction"],
)
def unrestricted_write(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    if not isinstance(file.data, dict):
        return findings
    for path, value, line_no in _iter_tool_strings(file):
        lower = value.strip().lower()
        if lower in {"write", "edit", "write(*)", "edit(*)", "notebookedit(*)"}:
            findings.append(ctx.make("SV011", file, line_no, f"{'/'.join(path)}: {value}"))
    return findings


@register(
    "SV012",
    Severity.MEDIUM,
    "Wildcard tool grant or missing allow-list",
    'Declare an explicit allowed-tools list. "*" defeats the purpose of sandboxing an agent.',
    [OWASP_LLM06],
    ["manifest", "hook-config", "instruction"],
)
def wildcard_tools(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    if not isinstance(file.data, dict):
        return findings
    for path, value, line_no in _iter_tool_strings(file):
        if value.strip() == "*":
            findings.append(ctx.make("SV012", file, line_no, f"{'/'.join(path)}: *"))
    return findings


# ---------------------------------------------------------------------------
# MCP config rules
# ---------------------------------------------------------------------------


def _mcp_servers(data: dict) -> List[tuple]:
    servers = []
    if not isinstance(data, dict):
        return servers
    for key in ("mcpServers", "servers", "mcp"):
        node = data.get(key)
        if isinstance(node, dict):
            for name, cfg in node.items():
                if isinstance(cfg, dict):
                    servers.append((name, cfg))
    return servers


@register(
    "SV020",
    Severity.MEDIUM,
    "MCP server installed without a pinned version",
    "Pin the package version (npx pkg@1.2.3). Unpinned auto-installs let an upstream "
    "release change what executes on your machine.",
    [OWASP_LLM05],
    ["mcp-config"],
)
def mcp_unpinned(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for name, cfg in _mcp_servers(file.data or {}):
        command = str(cfg.get("command", ""))
        args = cfg.get("args") or []
        joined = " ".join(str(a) for a in args)
        if command in {"npx", "uvx", "uv", "pipx"}:
            pkg = next((str(a) for a in args if not str(a).startswith("-")), None)
            if pkg and not re.search(r"@[0-9]", pkg) and not re.search(r"==[0-9]", pkg):
                line_no = _find_line(file, pkg)
                findings.append(ctx.make("SV020", file, line_no, f"{name}: {command} {joined}"))
        elif command in {"pip", "pip3", "npm", "yarn", "pnpm"}:
            line_no = _find_line(file, command)
            findings.append(ctx.make("SV020", file, line_no, f"{name}: {command} {joined}"))
    return findings


@register(
    "SV021",
    Severity.HIGH,
    "Plaintext secret in MCP server environment",
    "Move the secret to a real secret store and reference it by name, or use a "
    "credential helper. Config files get committed.",
    [OWASP_LLM02],
    ["mcp-config", "hook-config"],
)
def mcp_env_secret(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for name, cfg in _mcp_servers(file.data or {}):
        env = cfg.get("env")
        if not isinstance(env, dict):
            continue
        for key, value in env.items():
            if not isinstance(value, str) or not value:
                continue
            if re.search(
                r"(?i)(key|token|secret|password|credential)", key
            ) and not value.startswith("$"):
                if not re.fullmatch(r"[\w\-]{0,3}", value):
                    line_no = _find_line(file, key)
                    findings.append(
                        Finding(
                            rule_id="SV021",
                            severity=RULES["SV021"].severity,
                            title=RULES["SV021"].title,
                            path=file.relpath,
                            line=line_no,
                            snippet=f"{name}: env {key}=<redacted:{len(value)} chars>",
                            remediation=RULES["SV021"].remediation,
                            references=list(RULES["SV021"].references),
                            confidence="medium",
                        )
                    )
    return findings


@register(
    "SV022",
    Severity.MEDIUM,
    "Remote MCP endpoint (data egress surface)",
    "Remote servers receive everything the agent sends them. Prefer local stdio "
    "servers, or document the remote endpoint's data handling.",
    [OWASP_LLM06],
    ["mcp-config"],
)
def mcp_remote(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for name, cfg in _mcp_servers(file.data or {}):
        url = cfg.get("url") or cfg.get("baseUrl") or cfg.get("endpoint")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            line_no = _find_line(file, url)
            findings.append(ctx.make("SV022", file, line_no, f"{name}: {url}"))
    return findings


@register(
    "SV023",
    Severity.HIGH,
    "MCP server with arbitrary shell execution",
    "A server that spawns a shell can run anything. Restrict it to a fixed binary "
    "with a fixed argument list.",
    [OWASP_LLM06],
    ["mcp-config"],
)
def mcp_shell_passthrough(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for name, cfg in _mcp_servers(file.data or {}):
        command = str(cfg.get("command", ""))
        args = [str(a) for a in (cfg.get("args") or [])]
        joined = " ".join([command, *args])
        if re.search(r"(?i)(sh|bash|zsh|cmd|powershell)\s+-c\b", joined) or re.search(
            r"(?i)\bpython[0-9.]*\s+-c\b|\bnode\s+-e\b", joined
        ):
            line_no = _find_line(file, command)
            findings.append(ctx.make("SV023", file, line_no, f"{name}: {joined}"))
    return findings


# ---------------------------------------------------------------------------
# hook rules
# ---------------------------------------------------------------------------


def _hook_commands(data: dict) -> List[tuple]:
    commands = []
    if not isinstance(data, dict):
        return commands

    def walk(node, where):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"command", "cmd"} and isinstance(value, str) and value.strip():
                    commands.append((where, value))
                else:
                    walk(value, f"{where}.{key}" if where else str(key))
        elif isinstance(node, list):
            for item in node:
                walk(item, where)

    walk(data.get("hooks", data), "")
    return commands


OUTSIDE_REPO_RE = re.compile(
    r"(?<![\w])~(?:/|$)"
    r"|(?<![\w.])\.\./"
    r"|(?<![\w])/(?:home|Users|opt|srv|root|tmp|var|private|mnt|media)(?:/[\w.\-]+)+\.(?:sh|py|js|mjs|ts|ps1|rb|pl)\b"
)


@register(
    "SV030",
    Severity.HIGH,
    "Hook executes a script from outside the repository",
    "Hooks should run files that live in the repo (or well-known system paths such as "
    "/usr/bin). Home-directory, parent-relative or /opt paths hide what will execute.",
    [OWASP_LLM05],
    ["hook-config"],
)
def hook_outside_repo(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for where, command in _hook_commands(file.data or {}):
        if OUTSIDE_REPO_RE.search(command):
            line_no = _find_line(file, command)
            findings.append(ctx.make("SV030", file, line_no, f"{where}: {command}"))
    return findings


@register(
    "SV031",
    Severity.CRITICAL,
    "Hook performs network access",
    "Hooks run automatically on agent events. Network access in a hook can silently "
    "exfiltrate workspace content; remove it or make it an explicit, reviewed step.",
    [OWASP_LLM02],
    ["hook-config"],
)
def hook_network(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for where, command in _hook_commands(file.data or {}):
        if re.search(r"(?i)\b(curl|wget|nc|ncat|socat|ssh|scp)\b", command):
            line_no = _find_line(file, command)
            findings.append(ctx.make("SV031", file, line_no, f"{where}: {command}"))
    return findings


# ---------------------------------------------------------------------------
# hygiene rules
# ---------------------------------------------------------------------------


@register(
    "SV040",
    Severity.LOW,
    "Skill directory without a license file",
    "Add a LICENSE file. Users cannot safely adopt a skill whose terms are unknown.",
    [OWASP_LLM05],
    ["instruction"],
)
def missing_license(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    import os

    directory = os.path.dirname(file.path)
    for candidate in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        if os.path.exists(os.path.join(directory, candidate)):
            return []
    return [ctx.make("SV040", file, 1, file.relpath)]


@register(
    "SV041",
    Severity.LOW,
    "Dependency installed without a version pin",
    "Pin versions in setup scripts so a skill keeps working and stays auditable.",
    [OWASP_LLM05],
    ["instruction", "script"],
)
def unpinned_dependency(file: ScannedFile, ctx: ScanContext) -> List[Finding]:
    findings = []
    for idx, line in enumerate(file.lines, start=1):
        if re.search(r"(?i)\bpip3?\s+install\b(?!.*==)", line) and not re.search(
            r"(?i)-r\s|requirements", line
        ):
            findings.append(ctx.make("SV041", file, idx, file.snippet(idx)))
        elif re.search(r"(?i)\bnpm\s+(i|install)\s+(?!-)", line) and not re.search(
            r"@[0-9^~]", line
        ):
            findings.append(ctx.make("SV041", file, idx, file.snippet(idx)))
    return findings
