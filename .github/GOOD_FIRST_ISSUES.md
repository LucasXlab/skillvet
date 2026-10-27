# Good first issues

These five issues are intentionally small, well-scoped and suitable for a first contribution. Create them as GitHub issues after the repo is public (labels: `good first issue`, `help wanted`).

## 1. Add a rule for `allowed-tools` entries that combine network + write access

**What:** Flag manifests where a single agent is granted both `WebFetch` and `Write`/`Edit` without any path or domain restriction (SV013).
**Where:** `skillvet/rules.py`, new rule + fixture + test + README table row.
**Why:** Excessive agency (OWASP LLM06) is currently only covered per-tool; the combination is the real risk.
**Acceptance:** `tests/fixtures/malicious-skill`-style fixture with both tools triggers exactly one SV013 finding; clean fixture unaffected.

## 2. Support `.skillvetignore` negation (`!pattern`)

**What:** gitignore-style negation so a broad ignore can be re-included for a subpath.
**Where:** `skillvet/ignore.py`.
**Acceptance:** unit tests for include/exclude/negate ordering; existing behavior unchanged.

## 3. Add `--count` summary flag for CI logs

**What:** `skillvet . --count` prints only `4 critical, 10 high, …` plus the trust score, for compact CI annotations.
**Where:** `skillvet/cli.py`, `skillvet/report.py`.
**Acceptance:** works with `--json` (as a top-level field), tested in `tests/test_cli.py`.

## 4. Detect skills that instruct the agent to disable its own safety features

**What:** New rule (SV009, medium) for instruction text like "skip confirmation", "do not ask before running", "auto-approve", "run without review".
**Where:** `skillvet/rules.py` + fixtures + tests.
**Acceptance:** triggers on at least three phrasings; does not trigger on legitimate "you may proceed without asking for confirmation" style disclaimers in documentation about *humans*.

## 5. Render findings as GitHub Actions workflow commands (`--format github`)

**What:** `::error file=…,line=…::SV005 …` annotations so results show inline on PRs without SARIF setup.
**Where:** `skillvet/cli.py` (a `_github_annotations` helper already exists as a starting point).
**Acceptance:** output parses as valid workflow commands; documented in README usage section.
