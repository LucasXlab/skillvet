# Real CLI media and provenance

The recordings and reports here use the installed skillvet CLI on disposable, explicitly synthetic input. No scanned instruction or script is executed. The authoring wrapper never uploads output.

`scripts/showcase.py` runs seven actual commands and checks their exit codes: clean **0**, malformed configuration **2**, compatible suppression receipts **0**, strict review **1**, synthetic-secret masking **1**, frontmatter grants at an explicit medium gate **1**, and SARIF **1**. These are limited pattern signals, not a safety verdict or a real-world accuracy benchmark.

Four command views are **wrapper projections**, clearly labelled in the recording: incomplete JSON, suppression receipts, redaction JSON, and SARIF. They select actual report fields without changing values; `assets/reports/` retains each full, unfiltered CLI stdout and stderr. The projection function in `scripts/showcase.py` is the complete selection rule. No temporary path replacement is needed: the CLI reports the scan root as `.` and synthetic paths are relative. Cast events are unedited.

`terminal.txt` concatenates recorded stdout events, normalizing terminal CRLF to LF only. Feature text files are contiguous command groups from that transcript. PNGs faithfully render those groups with visual line wrapping. `demo.gif` uses the status, strict-review, and redaction groups with extended reading holds; it is not original elapsed timing or a performance claim. The original timestamps remain in `demo.cast`. `demo.png` replaces the old ANSI-damaged asset with the recorded strict-review group.

The logo, social preview, and metadata badges are native illustrations. They are not runtime screenshots. Source version 1.0.0 does not imply a published registry package; CI is prepared and stars are pending. `recording.json` links the cast, reports, transcripts, and generated images with SHA-256 hashes.

## Reproduce

After installing the checkout in `.venv`, run the showcase without optional media dependencies:

```sh
.venv/bin/python scripts/showcase.py --report-dir assets/reports
```

Recording/rendering author tools are asciinema 2.4.0 and Pillow 13.0.0, separate from the CLI's empty runtime dependencies. Use a task-owned HOME, TMPDIR, XDG_CONFIG_HOME, and ASCIINEMA_CONFIG_HOME. Pass an explicit local filename; do not use upload.

```sh
asciinema rec --overwrite --cols 110 --rows 42 -c '.venv/bin/python scripts/showcase.py --pause 1.2 --report-dir assets/reports' assets/demo.cast
python scripts/render_assets.py --cast assets/demo.cast --out assets
```

The renderer rejects ANSI control sequences and machine home paths. It uses Menlo on macOS or DejaVu Sans Mono on Linux; cross-system font differences can change image bytes. The social preview is exactly 1280×640. Review all report text and rendered frames before sharing: finite secret masking is not general anonymization.
