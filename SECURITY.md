# Security policy

skillvet is an offline, finite-rule static scanner. It does not execute scanned code,
contact remote services, or establish that inspected content is safe. A passing gate
is not a sandbox, malware verdict, proof of originality, or privacy clearance.

For a vulnerability in the scanner itself, use a verified private reporting channel
provided by the repository host if one is available. No private mailbox, response
schedule, or enabled reporting service is claimed by this source checkout. Do not
send credentials, personal data, proprietary skills, or full private scan reports to
an unverified contact. A public issue should contain only a fully synthetic, redacted
reproducer and no sensitive details.

Include the source version (`skillvet --version`), operating system, command,
expected and actual behavior, and a minimal synthetic fixture. Special files and
links are refused; the supported secure-read implementation requires POSIX APIs.
Run scans on a stable copy and review all diagnostics, exclusions, suppressions and
coverage notes. Known-pattern redaction does not eliminate all private content.
