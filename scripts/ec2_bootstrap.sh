#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <github-repo-url> [target-dir]" >&2
  exit 1
fi

REPO_URL="$1"
TARGET_DIR="${2:-$HOME/quotes-scraper}"

sudo yum update -y
sudo yum install -y git python3 python3-pip

if [[ ! -d "$TARGET_DIR/.git" ]]; then
  git clone "$REPO_URL" "$TARGET_DIR"
else
  git -C "$TARGET_DIR" pull --ff-only
fi

python3 -m venv "$TARGET_DIR/.venv"
"$TARGET_DIR/.venv/bin/pip" install --upgrade pip
"$TARGET_DIR/.venv/bin/pip" install -r "$TARGET_DIR/requirements.txt"

echo "Bootstrap complete in $TARGET_DIR"
