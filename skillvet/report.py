"""Terminal report rendering."""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from .model import RESET, SEVERITY_COLOR, SEVERITY_ORDER, Finding, ScanResult, Severity
from .redact import redact_text


def _supports_color(stream, no_color: bool) -> bool:
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def _paint(text: str, severity: Severity, color: bool) -> str:
    text = redact_text(text)
    if not color:
        return text
    return f"{SEVERITY_COLOR[severity]}{text}{RESET}"


def render_findings_table(findings: List[Finding], color: bool) -> str:
    rows = []
    for f in findings:
        sev = f.severity.name.ljust(8)
        rid = f.rule_id.ljust(6)
        loc = f"{redact_text(f.path)}:{f.line}".ljust(48)
        title = redact_text(f.title)
        rows.append(f"  {_paint(sev, f.severity, color)} {rid} {loc} {title}")
    return "\n".join(rows)


def render_details(findings: List[Finding], color: bool, max_snippet: int = 90) -> str:
    blocks = []
    for f in findings:
        header = f"{f.rule_id}  {f.title}"
        lines = [
            _paint(f"  {redact_text(header)}", f.severity, color),
            f"    file    : {redact_text(f.path)}:{f.line}",
            f"    evidence: {redact_text(f.snippet)[:max_snippet]}",
            f"    fix     : {redact_text(f.remediation)}",
        ]
        if f.references:
            lines.append("    see     : " + ", ".join(redact_text(r) for r in f.references))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_summary(result: ScanResult, color: bool, fail_on: Severity) -> str:
    counts = result.counts()
    score = result.trust_score()
    parts = []
    for sev in reversed(SEVERITY_ORDER):
        if counts[str(sev)]:
            parts.append(_paint(f"{counts[str(sev)]} {sev.name.lower()}", sev, color))
    breakdown = ", ".join(parts) if parts else "no findings"
    code = result.exit_code(fail_on)
    verdict = "INCOMPLETE" if code == 2 else ("FAIL" if code == 1 else "PASS")
    verdict_color = Severity.INFO if verdict == "PASS" else Severity.CRITICAL
    lines = [
        "",
        f"  scanned {result.files_scanned} agent file(s)"
        + (f", skipped {result.files_skipped}" if result.files_skipped else ""),
        f"  findings: {breakdown}",
        f"  rule-signal score: {_paint(str(score), verdict_color, color) + '/100' if score is not None else 'unavailable'} (not a safety guarantee)",
        f"  exclusions: {result.files_skipped} path(s), {len(result.suppressed)} suppressed finding(s), {result.filtered_count} display-filtered finding(s)",
        f"  coverage notes: {len(result.coverage_notes)}; errors: {len(result.errors)}",
        f"  verdict: {_paint(verdict, verdict_color, color)} (fail-on: {fail_on.name.lower()})",
    ]
    return "\n".join(lines)


def render(
    result: ScanResult,
    stream=None,
    color: Optional[bool] = None,
    show_details: bool = True,
    fail_on=Severity.HIGH,
    quiet=False,
) -> str:
    stream = stream or sys.stdout
    if color is None:
        color = _supports_color(stream, no_color=False)
    if quiet:
        return f"{'INCOMPLETE' if result.errors else ('FAIL' if result.exit_code(fail_on) else 'PASS')} scanned={result.files_scanned} findings={len(result.findings)} suppressed={len(result.suppressed)} errors={len(result.errors)} fail-on={fail_on.name.lower()}\n"
    out = []
    out.append("")
    out.append("  skillvet — security audit for AI agent skills, hooks and MCP configs")
    out.append("")
    if not result.findings:
        out.append(
            "  no reportable findings"
            if result.errors or result.filtered_count
            else "  ✓ no findings"
        )
    else:
        out.append(render_findings_table(result.findings, color))
        if show_details:
            out.append("")
            out.append(render_details(result.findings, color))
    out.append(render_summary(result, color, fail_on=fail_on))
    return "\n".join(out) + "\n"


def render_rules(stream=None) -> str:
    from . import rules as rules_mod

    lines = ["", "  available rules", ""]
    for rule_id in sorted(rules_mod.RULES):
        rule = rules_mod.RULES[rule_id]
        kinds = ",".join(rule.kinds)
        lines.append(f"  {rule_id}  {rule.severity.name.lower():8} [{kinds}] {rule.title}")
    lines.append("")
    return "\n".join(lines) + "\n"
