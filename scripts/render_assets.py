"""Render a local asciinema recording into faithful, readable project assets.

Optional authoring dependency: Pillow. This is not a skillvet runtime dependency.
The .cast file is read without modification. GIF holds are extended for readability;
the recording's original timestamps remain available in assets/demo.cast.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKGROUND = "#faf6eb"
PANEL = "#173d3b"
TEXT = "#faf6eb"
MUTED = "#bfd0c7"
MINT = "#f4ba5b"
AMBER = "#f4ba5b"
INK = "#173d3b"


def font(size: int, mono: bool = True):
    candidates = (
        [
            "/System/Library/Fonts/Menlo.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
        if mono
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def wrapped(text: str, width: int = 92) -> list[str]:
    wrapper = textwrap.TextWrapper(
        width=width,
        expand_tabs=False,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=False,
    )
    lines = []
    for line in text.expandtabs(4).splitlines():
        lines.extend(wrapper.wrap(line) if line else [""])
    return lines


def terminal(title: str, text: str, *, height: int | None = None) -> Image.Image:
    lines = wrapped(text)
    natural_height = 185 + len(lines) * 27
    height = height or max(420, natural_height)
    if natural_height > height:
        raise ValueError(f"Terminal content does not fit: {title}")
    image = Image.new("RGB", (1280, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((42, 24), "skillvet / local review", font=font(22), fill=INK)
    draw.text((42, 64), title, font=font(24, False), fill=INK)
    draw.text((935, 30), "SYNTHETIC INPUT", font=font(17), fill=INK)
    draw.rounded_rectangle((24, 111, 1256, height - 28), radius=10, fill=PANEL)
    for index, line in enumerate(lines):
        color = MINT if line.startswith("$ ") else TEXT
        if line.startswith("[wrapper") or line.startswith("[exit "):
            color = MUTED
        elif "FAIL" in line or '"complete": false' in line:
            color = AMBER
        draw.text((45, 132 + index * 27), line, font=font(20), fill=color)
    return image


def social() -> Image.Image:
    image = Image.new("RGB", (1280, 640), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((68, 58, 148, 138), radius=18, fill=PANEL)
    draw.ellipse((85, 75, 122, 112), outline=TEXT, width=4)
    draw.line((117, 107, 134, 124), fill=TEXT, width=4)
    draw.line((94, 88, 113, 88), fill=MINT, width=3)
    draw.line((94, 98, 106, 98), fill=MINT, width=3)
    draw.text((170, 61), "skillvet", font=font(63, False), fill=INK)
    draw.text((70, 230), "Review what an agent", font=font(44, False), fill=INK)
    draw.text((70, 288), "skill can ask for.", font=font(44, False), fill=INK)
    draw.text((73, 395), "SIGNALS + COVERAGE + RECEIPTS", font=font(20), fill=INK)
    draw.text((73, 553), "OFFLINE / FINITE RULES / NO EXECUTION", font=font(18), fill=INK)
    draw.rounded_rectangle((777, 64, 1207, 564), radius=17, fill=PANEL)
    draw.text((810, 103), "REVIEW RECORD", font=font(23), fill=TEXT)
    for y, name, detail in [
        (184, "01 / FINDINGS", "What triggered a rule?"),
        (294, "02 / COVERAGE", "What stayed uninspected?"),
        (404, "03 / EXCEPTIONS", "Who suppressed a result?"),
    ]:
        draw.line((811, y - 20, 1173, y - 20), fill="#56726a", width=2)
        draw.text((812, y), name, font=font(20), fill=MINT)
        draw.text((812, y + 39), detail, font=font(17), fill=TEXT)
    return image


def badge(label: str, value: str) -> str:
    left, right = 16 + len(label) * 7, 16 + len(value) * 7
    label, value = html.escape(label), html.escape(value)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{left + right}" height="24" role="img" aria-label="{label}: {value}">'
        f'<rect width="{left + right}" height="24" rx="5" fill="#173d3b"/>'
        f'<path d="M{left} 0h{right - 5}q5 0 5 5v14q0 5-5 5h-{right - 5}z" fill="#425e53"/>'
        f'<g fill="#faf6eb" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{left / 2}" y="16">{label}</text>'
        f'<text x="{left + right / 2}" y="16">{value}</text></g></svg>\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cast", type=Path, default=Path("assets/demo.cast"))
    parser.add_argument("--out", type=Path, default=Path("assets"))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.cast.read_text(encoding="utf-8").splitlines()]
    transcript = "".join(event[2] for event in rows[1:] if event[1] == "o")
    transcript = transcript.replace("\r\n", "\n").replace("\r", "")
    if "\x1b" in transcript:
        raise ValueError("ANSI controls are not supported; do not conceal them by stripping")
    if re.search(r"/(?:Users|home)/[^/\s]+", transcript):
        raise ValueError("Recording contains a machine home path")
    sections = [s for s in re.split(r"(?m)(?=^\$ skillvet )", transcript) if s.strip()]
    if len(sections) != 7:
        raise ValueError("Expected the seven actual commands from scripts/showcase.py")
    assets = args.out
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "terminal.txt").write_text(transcript, encoding="utf-8")
    features = [
        ("status", "Distinguish a clean gate from an incomplete scan", "".join(sections[:2])),
        ("receipts", "Inspect target-controlled exception receipts", sections[2]),
        ("strict", "Strict review ignores the target's own suppressions", sections[3]),
        ("redaction", "Known-pattern masking in actual JSON findings", sections[4]),
        ("permissions", "Inspect the supported frontmatter grant fields", sections[5]),
        ("sarif", "Keep rule, location, and execution state in SARIF", sections[6]),
    ]
    for name, title, text in features:
        terminal(title, text).save(assets / f"feature-{name}.png", optimize=True)
        (assets / f"feature-{name}.txt").write_text(text, encoding="utf-8")
    terminal(features[2][1], features[2][2]).save(assets / "demo.png", optimize=True)
    displayed = [features[0], features[2], features[3]]
    height = max(600, max(185 + len(wrapped(text)) * 27 for _, _, text in displayed))
    frames = [terminal(title, text, height=height) for _, title, text in displayed]
    frames[0].save(
        assets / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=[3600, 4000, 3600],
        loop=0,
        optimize=False,
        disposal=2,
    )
    social().save(assets / "social-preview.png", optimize=True)
    for name, (label, value) in {
        "ci": ("CI", "prepared"),
        "license": ("license", "MIT"),
        "version": ("source", "v1.0.0"),
        "python": ("Python", "3.9+"),
        "stars": ("stars", "pending"),
    }.items():
        (assets / f"badge-{name}.svg").write_text(badge(label, value), encoding="utf-8")
    manifest = {
        "source_cast_sha256": hashlib.sha256(args.cast.read_bytes()).hexdigest(),
        "event_count": len(rows) - 1,
        "actual_commands": 7,
        "view_selection": "showcase.py selects explicitly labelled JSON/SARIF fields; full unfiltered CLI output retained under assets/reports. No path replacement or edited cast events.",
        "rendering": "Faithful stdout text with visual wrapping; GIF extended reading holds, not elapsed runtime.",
        "features": [
            {"name": name, "transcript_sha256": hashlib.sha256(text.encode()).hexdigest()}
            for name, _, text in features
        ],
        "reports": {},
        "assets": {},
    }
    report_directory = args.cast.parent / "reports"
    if report_directory.is_dir():
        manifest["reports"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(report_directory.iterdir())
            if p.is_file()
        }
    for name in ["demo.png", "demo.gif", "social-preview.png"] + [
        f"feature-{name}.png" for name, _, _ in features
    ]:
        p = assets / name
        with Image.open(p) as im:
            manifest["assets"][name] = {
                "width": im.width,
                "height": im.height,
                "frames": getattr(im, "n_frames", 1),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
    (assets / "recording.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
