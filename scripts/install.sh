#!/usr/bin/env bash
# dotfiles installer (WSL / Linux)
# Creates symlinks from $HOME back into this repo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINKS_JSON="$REPO_ROOT/links.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required (sudo apt install -y jq)" >&2
  exit 1
fi

count=$(jq '.linux | length' "$LINKS_JSON")

for i in $(seq 0 $((count - 1))); do
  src_rel=$(jq -r ".linux[$i].src" "$LINKS_JSON")
  dest_raw=$(jq -r ".linux[$i].dest" "$LINKS_JSON")
  dest="${dest_raw/#\~/$HOME}"
  src="$REPO_ROOT/$src_rel"

  if [ ! -e "$src" ]; then
    echo "Skip (source missing): $src" >&2
    continue
  fi

  mkdir -p "$(dirname "$dest")"

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ -L "$dest" ]; then
      rm "$dest"
    else
      echo "Backing up existing file: $dest -> $dest.backup"
      mv "$dest" "$dest.backup"
    fi
  fi

  ln -s "$src" "$dest"
  echo "Linked: $dest -> $src"
done

echo -e "\nDone. Restart your shell to pick up changes."
