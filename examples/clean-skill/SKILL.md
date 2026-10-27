---
name: changelog-writer
description: Turn git log entries into a user-facing changelog section.
allowed-tools:
  - Read
  - "Bash(git log:*)"
---

# Changelog Writer

You are writing the changelog for this repository.

## Steps

1. Run `git log --oneline v$(cat VERSION)..HEAD` to list commits since the last tag.
2. Group the commits into Added, Changed and Fixed.
3. Write the result into CHANGELOG.md under a new `## Unreleased` heading.
4. Skip merge commits and commits touching only CI configuration.

## Rules

- Never invent entries that are not present in the git log.
- Keep each bullet to one line.
- If there are no user-visible changes, write "No user-visible changes."
