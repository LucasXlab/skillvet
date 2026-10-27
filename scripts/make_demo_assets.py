#!/usr/bin/env python3
"""Compatibility entry point: faithfully render the checked-in local CLI cast.

Uses scripts/render_assets.py. To capture changed CLI behavior, first follow
assets/README.md and rerun the actual installed-CLI recording locally.
"""

from render_assets import main

if __name__ == "__main__":
    raise SystemExit(main())
