# Source development log

## Unreleased

The source metadata version is `1.0.0`; this log does not assert a published package,
release tag, deployed repository, or successful remote CI run.

- Bounded descriptor-relative file reads, no-follow link policy and pre-read ignores.
- Explicit parsing, traversal and rule-failure diagnostics; incomplete results exit 2.
- A documented frontmatter subset and source-aware permission grant inspection.
- Nested configuration discovery and bounded, non-executing static script references.
- Visible ignore and suppression receipts, plus `--strict` for untrusted targets.
- Shared known-secret redaction, consistent gate/terminal output, safe SARIF locations.
- Lint, format, coverage, wheel/source builds and source-install smoke checks.

The existing registry contains 19 finite rules. `skillvet --list-rules` is the source
of truth; rule count, statement coverage and passing fixtures do not establish
real-world detection accuracy or comparative scanner superiority.
