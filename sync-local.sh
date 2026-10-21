#!/usr/bin/env bash
# Sync the four overlay skills from this repo into the local agent skills dir.
# Usage:
#   bash sync-local.sh              # copy repo skills into ~/.agents/skills
#   bash sync-local.sh --check      # exit 1 if installed copies drift from repo
#   bash sync-local.sh [dest-dir]   # override destination (default ~/.agents/skills)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="install"
DEST=""
for arg in "$@"; do
  case "$arg" in
    --check) MODE="check" ;;
    *) DEST="$arg" ;;
  esac
done
DEST="${DEST:-$HOME/.agents/skills}"

SKILLS=(
  using-cursor-superpowers
  cursor-agent-bridge
  executing-plans-with-cursor
  reviewing-cursor-changes
)

drift=0
for skill in "${SKILLS[@]}"; do
  src="$REPO_ROOT/skills/$skill"
  dst="$DEST/$skill"
  if [[ ! -d "$src" ]]; then
    echo "missing source skill: $src" >&2
    exit 1
  fi
  if [[ "$MODE" == "check" ]]; then
    if [[ ! -d "$dst" ]] \
      || ! diff -rq --exclude=__pycache__ --exclude=.DS_Store "$src" "$dst" >/dev/null 2>&1; then
      echo "drift: $skill differs between repo and $DEST" >&2
      drift=1
    fi
    continue
  fi
  mkdir -p "$DEST"
  rm -rf "$dst"
  mkdir -p "$dst"
  (cd "$src" && tar cf - --exclude=__pycache__ --exclude=.DS_Store .) | (cd "$dst" && tar xf -)
  echo "synced: $skill -> $dst"
done

if [[ "$MODE" == "check" ]]; then
  if [[ "$drift" -ne 0 ]]; then
    echo "installed skills drift from repo; run 'bash sync-local.sh' to sync" >&2
    exit 1
  fi
  echo "installed skills match repo"
fi
