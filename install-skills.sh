#!/usr/bin/env bash
# Copy all skills to ~/.agents/skills/ and create symlinks in ~/.claude/skills/ and ~/.openclaw/skills/
# Source of truth: ~/Judian/vega-punk/skills/
# Copy target: ~/.agents/skills/
# Symlinks: ~/.claude/skills/ and ~/.openclaw/skills/ → ~/.agents/skills/

set -euo pipefail

SOURCE_DIR="$HOME/Judian/vega-punk/skills"
TARGET_DIR="$HOME/.agents/skills"
LINK_DIRS=("$HOME/.claude/skills" "$HOME/.openclaw/skills")

echo "=== Skill Installation ==="
echo "Source: $SOURCE_DIR (source of truth)"
echo "Copy: $TARGET_DIR"
echo "Symlinks: ${LINK_DIRS[*]} → $TARGET_DIR"
echo ""

# ── 1. Create target directories ──
mkdir -p "$TARGET_DIR"
for link_dir in "${LINK_DIRS[@]}"; do
  mkdir -p "$link_dir"
done

# ── 2. Copy entire skills directory into ~/.agents/skills/ ──
echo "  Copying all skills..."
cp -r "$SOURCE_DIR"/. "$TARGET_DIR"/
echo "  Done."

# ── 3. Create symlinks in all link directories ──
for link_dir in "${LINK_DIRS[@]}"; do
  echo ""
  echo "  Creating symlinks in $link_dir..."
  for skill_dir in "$SOURCE_DIR"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name=$(basename "$skill_dir")

    # Remove existing (real dir, symlink, or file)
    if [[ -e "$link_dir/$skill_name" || -L "$link_dir/$skill_name" ]]; then
      rm -rf "$link_dir/$skill_name"
    fi

    ln -s "$TARGET_DIR/$skill_name" "$link_dir/$skill_name"
    echo "    $skill_name → $TARGET_DIR/$skill_name"
  done
done

echo ""
echo "=== Done ==="
