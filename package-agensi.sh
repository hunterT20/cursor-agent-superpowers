#!/usr/bin/env bash
# Build one Agensi-compatible ZIP containing the four Cursor Agent Superpowers skills.
# Usage: bash package-agensi.sh [path-to-repo] [optional-output-directory]
set -euo pipefail

if ! REPO_ROOT="$(cd "${1:-.}" 2>/dev/null && pwd)"; then
  echo "Repository path does not exist: ${1:-.}" >&2
  exit 1
fi
OUT_DIR="${2:-$REPO_ROOT/dist/agensi}"
ZIP_NAME="cursor-agent-superpowers.zip"
ZIP_PATH="$OUT_DIR/$ZIP_NAME"

for cmd in zip unzip mktemp; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

SKILLS=(
  using-cursor-superpowers
  cursor-agent-bridge
  executing-plans-with-cursor
  reviewing-cursor-changes
)

for skill in "${SKILLS[@]}"; do
  skill_file="$REPO_ROOT/skills/$skill/SKILL.md"
  if [[ ! -f "$skill_file" ]]; then
    echo "Missing required skill: $skill_file" >&2
    exit 1
  fi
  # Extract frontmatter (lines between the first and second '---' markers).
  frontmatter="$(awk 'NR==1 && $0=="---" {in_fm=1; next} in_fm && $0=="---" {exit} in_fm {print}' "$skill_file")"
  if [[ -z "$frontmatter" ]] \
    || ! grep -Eq "^name:[[:space:]]+$skill[[:space:]]*$" <<<"$frontmatter" \
    || ! grep -Eq '^description:[[:space:]]+' <<<"$frontmatter"; then
    echo "Invalid SKILL.md frontmatter: $skill_file" >&2
    exit 1
  fi
done

if [[ ! -f "$REPO_ROOT/LICENSE" ]]; then
  echo "Missing LICENSE in repository root" >&2
  exit 1
fi
if [[ ! -f "$REPO_ROOT/skills/cursor-agent-bridge/scripts/run_cursor_agent.py" ]]; then
  echo "Missing local Cursor Agent runner" >&2
  exit 1
fi
if [[ ! -f "$REPO_ROOT/skills/executing-plans-with-cursor/references/execution-contracts.md" ]]; then
  echo "Missing execution contracts" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agensi-pack.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
PKG_DIR="$TMP_DIR/package"
mkdir -p "$PKG_DIR/skills" "$OUT_DIR"

for skill in "${SKILLS[@]}"; do
  cp -R "$REPO_ROOT/skills/$skill" "$PKG_DIR/skills/$skill"
done
cp "$REPO_ROOT/LICENSE" "$PKG_DIR/LICENSE"
if [[ -f "$REPO_ROOT/README.md" ]]; then
  cp "$REPO_ROOT/README.md" "$PKG_DIR/README.md"
fi

# Create a single discoverable entry-point skill; the four original SKILL.md
# files remain intact as supporting instructions and are NOT separately registered.
cat > "$PKG_DIR/SKILL.md" <<'SKILL'
---
name: cursor-agent-superpowers
description: Coordinate coding tasks with Codex or Superpowers as controller and Cursor Agent as implementer, using evidence-based review and verification. Bundles the four cooperating Cursor Agent Superpowers skills.
---

# Cursor Agent Superpowers (Agensi Distribution)

This is the **single entry point** for the `cursor-agent-superpowers` bundle.
All four original skills are included under `skills/` as supporting instructions.
Do not assume those nested `SKILL.md` files are independently registered by the host.

## Mandatory routing

1. For every relevant task, read `skills/using-cursor-superpowers/SKILL.md` first.
2. For an approved plan, read `skills/executing-plans-with-cursor/SKILL.md` and `skills/executing-plans-with-cursor/references/execution-contracts.md` before dispatch.
3. To delegate implementation or semantic review fixes, read `skills/cursor-agent-bridge/SKILL.md` and use its local runner at `skills/cursor-agent-bridge/scripts/run_cursor_agent.py`.
4. To evaluate worker changes and test evidence, read `skills/reviewing-cursor-changes/SKILL.md`.
5. Follow all child-skill constraints: Cursor handles semantic edits; the controller plans, reviews and verifies. Upstream Superpowers is optional and its use requires the user's task-level confirmation when available.

## Environment requirements

- Codex or compatible controller, local Cursor Agent CLI, Python 3 and Git.
- The packaged supporting files must be physically available on disk for file reads and Python execution.
- This ZIP preserves project-relative paths: resolve them from the **directory containing this SKILL.md**.
- If the host only exposes `SKILL.md` as remote text and does **not** materialize included scripts and references locally, do **not** pretend the bridge will execute. Recommend installing the original repository locally instead.

## Project and license

MIT License. Full source, documentation, and original four-skill installer:
https://github.com/hunterT20/cursor-agent-superpowers
SKILL

# Build the archive. Remove any previous ZIP first so reruns do not merge
# stale entries, and exclude macOS metadata files copied by `cp -R`.
rm -f "$ZIP_PATH"
(cd "$PKG_DIR" && zip -qr "$ZIP_PATH" . -x "*.DS_Store" "__MACOSX/*" "*/__pycache__/*" "*.pyc")

if ! unzip -tqq "$ZIP_PATH" >/dev/null; then
  echo "Corrupt ZIP produced: $ZIP_PATH" >&2
  exit 1
fi

echo "Built $ZIP_PATH"
