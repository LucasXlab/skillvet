"""Run independent static rules with explicit coverage and exception receipts."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import List, Optional

from . import rules as rules_mod
from .discovery import Discovery
from .ignore import parse_inline
from .model import SEVERITY_WEIGHT, Finding, ScanResult, Severity
from .redact import collect_secrets, redact_text


class Scanner:
    def __init__(
        self,
        root: str,
        min_severity: Severity = Severity.INFO,
        extra_ignores: Optional[List[str]] = None,
        strict=False,
        max_files=10_000,
        max_file_bytes=1_048_576,
        max_total_bytes=16_777_216,
    ):
        self.root = os.path.abspath(root)
        self.ctx = rules_mod.ScanContext(self.root)
        self.min_severity = min_severity
        self.extra_ignores = extra_ignores or []
        self.strict = strict
        self.limits = dict(
            max_files=max_files, max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes
        )

    def scan(self) -> ScanResult:
        discovery = Discovery(self.root, self.extra_ignores, self.strict, **self.limits).run()
        result = ScanResult(root=".")
        result.errors.extend(discovery.errors)
        result.skipped = discovery.skipped
        result.files_skipped = len(discovery.skipped)
        result.coverage_notes = list(dict.fromkeys(discovery.notes))
        result.bytes_read = discovery.bytes_read
        secrets = set()
        for file in discovery.files:
            secrets.update(collect_secrets(file.text, file.data))
        for file in discovery.files:
            result.files_scanned += 1
            for rule in rules_mod.RULES.values():
                if file.kind not in rule.kinds:
                    continue
                try:
                    findings = list(rule.check(file, self.ctx))
                    for finding in findings:
                        line = (
                            file.lines[finding.line - 1]
                            if 0 < finding.line <= len(file.lines)
                            else ""
                        )
                        ids = parse_inline(line)
                        if not self.strict and (finding.rule_id in ids or "ALL" in ids):
                            receipt = finding.to_dict()
                            receipt["source"] = "inline target-controlled suppression"
                            receipt["reason"] = "target directive: " + ",".join(sorted(ids))
                            result.suppressed.append(receipt)
                        else:
                            result.add(finding)
                except Exception as exc:
                    result.errors.append(
                        f"{file.relpath}: rule {rule.id} failed ({type(exc).__name__})"
                    )
        result.detected_max = result.max_severity()
        # Score uses all detected findings, even when display filtering hides them.
        result.score_penalty = sum(SEVERITY_WEIGHT[f.severity] for f in result.findings)
        result.filtered_count = sum(f.severity < self.min_severity for f in result.findings)
        result.findings = [
            self._safe(f, secrets) for f in result.findings if f.severity >= self.min_severity
        ]
        result.findings.sort(key=lambda f: (-int(f.severity), f.path, f.line, f.rule_id))
        result.errors = [redact_text(e, secrets) for e in result.errors]
        result.coverage_notes = [redact_text(e, secrets) for e in result.coverage_notes]
        for receipt in result.suppressed + result.skipped:
            for key, value in list(receipt.items()):
                if isinstance(value, str):
                    receipt[key] = redact_text(value, secrets)
                elif isinstance(value, list):
                    receipt[key] = [
                        redact_text(v, secrets) if isinstance(v, str) else v for v in value
                    ]
        return result

    @staticmethod
    def _safe(finding: Finding, secrets):
        return replace(
            finding,
            path=redact_text(finding.path, secrets, controls=False),
            title=redact_text(finding.title, secrets),
            snippet=redact_text(finding.snippet, secrets),
            remediation=redact_text(finding.remediation, secrets),
            references=[redact_text(r, secrets) for r in finding.references],
        )
