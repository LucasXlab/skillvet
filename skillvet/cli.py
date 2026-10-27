"""Command line interface for skillvet."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__
from .model import Severity
from .redact import redact_text
from .report import render, render_rules
from .sarif import dumps as sarif_dumps
from .scanner import Scanner

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        super().error(redact_text(message))


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        prog="skillvet",
        description=(
            "Security audit for AI agent skills, hooks and MCP configs. "
            "Scans a directory for prompt injection, over-broad permissions, "
            "credential exposure and data-exfiltration patterns."
        ),
        epilog="example: skillvet ./my-project   (or just: skillvet)",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="directory to scan (default: current directory)"
    )
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="output machine-readable JSON")
    formats.add_argument("--sarif", action="store_true", help="output SARIF 2.1.0")
    parser.add_argument(
        "--min-severity",
        default="info",
        help="only report findings at or above this severity (default: info)",
    )
    parser.add_argument(
        "--fail-on",
        default="high",
        help="exit 1 when findings at or above this severity exist (default: high)",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="print the findings table and summary only (good for CI logs)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print the summary line")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="GLOB",
        help="extra path pattern to skip (repeatable)",
    )
    parser.add_argument("--list-rules", action="store_true", help="list all rules and exit")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="do not trust target .skillvetignore or inline suppressions (explicit --ignore still applies)",
    )
    parser.add_argument("--max-files", type=int, default=10000, help="maximum selected files")
    parser.add_argument(
        "--max-file-bytes", type=int, default=1048576, help="maximum bytes per file"
    )
    parser.add_argument(
        "--max-total-bytes", type=int, default=16777216, help="maximum bytes read in total"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"skillvet {__version__}")
        return EXIT_OK
    if args.list_rules:
        sys.stdout.write(render_rules())
        return EXIT_OK

    try:
        min_severity = Severity.parse(args.min_severity)
        fail_on = Severity.parse(args.fail_on)
    except ValueError as exc:
        parser.error(str(exc))
        return EXIT_USAGE

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"skillvet: {redact_text(args.path)}: not a directory", file=sys.stderr)
        return EXIT_USAGE

    if min(args.max_files, args.max_file_bytes, args.max_total_bytes) <= 0:
        parser.error("scan limits must be positive integers")
    scanner = Scanner(
        root,
        min_severity=min_severity,
        extra_ignores=args.ignore,
        strict=args.strict,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
    )
    result = scanner.scan()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif args.sarif:
        print(sarif_dumps(result))
    else:
        sys.stdout.write(
            render(
                result,
                color=False if args.no_color else None,
                show_details=not args.no_details,
                fail_on=fail_on,
                quiet=args.quiet,
            )
        )
        for error in result.errors:
            print(f"  ! {error}", file=sys.stderr)

    return result.exit_code(fail_on)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
