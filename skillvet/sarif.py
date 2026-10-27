"""SARIF 2.1.0 with correctly encoded locations and incomplete-run diagnostics."""

from __future__ import annotations

import json
from urllib.parse import quote

from . import __version__
from .model import ScanResult, Severity
from .redact import redact_text

SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}


def to_sarif(result: ScanResult) -> dict:
    index, descriptors, findings = {}, [], []
    for finding in result.findings:
        data = finding.to_dict()
        if finding.rule_id not in index:
            index[finding.rule_id] = len(descriptors)
            descriptor = {
                "id": finding.rule_id,
                "shortDescription": {"text": data["title"]},
                "fullDescription": {"text": data["remediation"]},
                "help": {"text": data["remediation"]},
                "defaultConfiguration": {"level": SARIF_LEVEL[finding.severity]},
                # Ordinal rule severity is not a calibrated CVSS score.
                "properties": {"tags": ["security"], "ruleSeverity": data["severity"]},
            }
            if data["references"]:
                descriptor["helpUri"] = data["references"][0]
            descriptors.append(descriptor)
        findings.append(
            {
                "ruleId": finding.rule_id,
                "ruleIndex": index[finding.rule_id],
                "level": SARIF_LEVEL[finding.severity],
                "message": {
                    "text": f"{data['title']}. {data['remediation']} Evidence: {data['snippet']}"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": quote(data["path"], safe="/"),
                            },
                            "region": {"startLine": max(1, finding.line)},
                        }
                    }
                ],
                "properties": {"confidence": finding.confidence},
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {"name": "skillvet", "version": __version__, "rules": descriptors}
                },
                "results": findings,
                "invocations": [
                    {
                        "executionSuccessful": result.complete,
                        "toolExecutionNotifications": [
                            {"level": "error", "message": {"text": redact_text(error)}}
                            for error in result.errors
                        ],
                    }
                ],
                "properties": {
                    "pathBase": "scan-root-relative",
                    "ruleSignalScore": result.trust_score(),
                    "filesScanned": result.files_scanned,
                    "filesSkipped": result.files_skipped,
                    "suppressed": result.suppressed,
                    "coverageNotes": result.coverage_notes,
                },
            }
        ],
    }


def dumps(result: ScanResult) -> str:
    return json.dumps(to_sarif(result), indent=2)
