"""Data model for skillvet findings and scan results."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional

from .redact import redact_text


class Severity(enum.IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def parse(cls, value: str) -> "Severity":
        try:
            return cls[value.strip().upper()]
        except KeyError:
            valid = ", ".join(s.name.lower() for s in cls)
            raise ValueError(f"unknown severity {value!r} (choose from {valid})")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name.lower()


SEVERITY_ORDER = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

SEVERITY_WEIGHT = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 4,
    Severity.HIGH: 10,
    Severity.CRITICAL: 25,
}

SEVERITY_COLOR = {
    Severity.CRITICAL: "\033[1;31m",
    Severity.HIGH: "\033[31m",
    Severity.MEDIUM: "\033[33m",
    Severity.LOW: "\033[36m",
    Severity.INFO: "\033[90m",
}

RESET = "\033[0m"


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    title: str
    path: str
    line: int
    snippet: str
    remediation: str
    references: List[str] = field(default_factory=list)
    confidence: str = "high"

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": str(self.severity),
            "title": redact_text(self.title),
            "path": redact_text(self.path, controls=False),
            "line": self.line,
            "snippet": redact_text(self.snippet),
            "remediation": redact_text(self.remediation),
            "references": [redact_text(r) for r in self.references],
            "confidence": self.confidence,
        }


@dataclass
class ScanResult:
    root: str
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    errors: List[str] = field(default_factory=list)

    skipped: List[dict] = field(default_factory=list)
    suppressed: List[dict] = field(default_factory=list)
    coverage_notes: List[str] = field(default_factory=list)
    bytes_read: int = 0
    filtered_count: int = 0
    detected_max: Optional[Severity] = None
    score_penalty: Optional[int] = None

    @property
    def complete(self):
        return not self.errors

    def exit_code(self, fail_on=Severity.HIGH):
        if self.errors:
            return 2
        severity = self.max_severity()
        return int(severity is not None and severity >= fail_on)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def by_severity(self, severity: Severity) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]

    def counts(self) -> dict:
        counts = {str(s): 0 for s in SEVERITY_ORDER}
        for f in self.findings:
            counts[str(f.severity)] += 1
        return counts

    def trust_score(self) -> Optional[int]:
        # Compatibility field: a rule-signal score, never a safety probability.
        if self.errors or self.files_skipped or self.suppressed or not self.files_scanned:
            return None
        penalty = (
            self.score_penalty
            if self.score_penalty is not None
            else sum(SEVERITY_WEIGHT[f.severity] for f in self.findings)
        )
        return max(0, 100 - penalty)

    def max_severity(self) -> Optional[Severity]:
        if self.detected_max is not None:
            return self.detected_max
        if not self.findings:
            return None
        return max(f.severity for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "tool": "skillvet",
            "root": ".",
            "complete": self.complete,
            "status": "complete" if self.complete else "incomplete",
            "coverage_notes": list(self.coverage_notes),
            "bytes_read": self.bytes_read,
            "filtered_count": self.filtered_count,
            "skipped": list(self.skipped),
            "suppressed": list(self.suppressed),
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "trust_score": self.trust_score(),
            "counts": self.counts(),
            "findings": [f.to_dict() for f in self.findings],
            "errors": [redact_text(e) for e in self.errors],
        }
