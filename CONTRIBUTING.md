# Contributing to skillvet

Thanks for helping make agent setups safer. This document explains how to add rules and fix bugs without slowing the project down.

## Ground rules

1. **Deterministic only.** No network calls, no LLM calls, no telemetry. If a rule cannot be decided from the bytes on disk, it does not belong here.
2. **Signals, not verdicts.** Every finding must explain the risk and the fix. If a rule cannot describe a remediation, it is not ready.
3. **Low false-positive rate beats high coverage.** A noisy rule gets disabled by everyone. Prefer specific patterns with clear context.
4. **Tests are part of the rule.** A rule without a failing fixture first is not a rule.

## Adding a rule

1. Open an issue describing the attack or misconfiguration, with a minimal synthetic or safely redacted example.
2. Add a fixture under `tests/fixtures/` that triggers the rule (and a clean counterpart if useful).
3. Implement the rule in `skillvet/rules.py` using the `@register` decorator. Pick the next free `SV0xx` id.
4. Choose severity deliberately:
   - `critical` — high-priority patterns associated with exfiltration or code execution
   - `high` — credential exposure or injection surface
   - `medium` — permission scope or supply-chain hygiene
   - `low` / `info` — maintainability and adoption signals
5. Add tests: trigger case, non-trigger case, and (for config rules) the pinned/clean variant.
6. Update documented support boundaries; `--list-rules` follows the registry automatically.
7. Run `make check` and review every diagnostic. A self-scan is a limited heuristic, not a safety proof.

## Reporting bugs

Use the bug report template. Include the skillvet version, the command you ran, and a **minimal redacted** repro — never paste real credentials or private skill content into an issue.

## Security issues

Do not open public issues for vulnerabilities in skillvet itself. See [SECURITY.md](SECURITY.md).

## Development setup

From this source checkout on a POSIX host:

```sh
make dev
make check
make demo
```

## Style

- Python 3.9 compatible, standard library only.
- Keep functions small and pure where possible; rules are functions `(ScannedFile, ScanContext) -> List[Finding]`.
- No new runtime dependencies without discussion in an issue first.
