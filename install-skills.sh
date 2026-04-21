#!/usr/bin/env bash
# Step 1: Copy local skills/ to ~/.agents/skills/ and symlink
# Step 2: Download skills from skill-lock.json and symlink
# Source of truth (local): ~/Judian/vega-punk/skills/
# Source of truth (remote): ~/Judian/vega-punk/skill-lock.json
# Copy target: ~/.agents/skills/
# Symlinks: ~/.claude/skills/ and ~/.openclaw/skills/ → ~/.agents/skills/

set -euo pipefail

SOURCE_DIR="$HOME/Judian/vega-punk/skills"
TARGET_DIR="$HOME/.agents/skills"
LINK_DIRS=("$HOME/.claude/skills" "$HOME/.openclaw/skills")
LOCK_FILE="$HOME/Judian/vega-punk/skill-lock.json"
CLONE_BASE="/tmp/skill-install"

# ── Create directories ──
mkdir -p "$TARGET_DIR"
for link_dir in "${LINK_DIRS[@]}"; do
  mkdir -p "$link_dir"
done

# ═══════════════════════════════════════════════════════════
# Phase 1: Copy local skills/ directory
# ═══════════════════════════════════════════════════════════
echo "=== Phase 1: Local Skills ==="
echo "Source: $SOURCE_DIR"

if [ -d "$SOURCE_DIR" ]; then
  cp -r "$SOURCE_DIR"/. "$TARGET_DIR"/
  echo "  Copied $(ls -1 "$SOURCE_DIR" | wc -l | tr -d ' ') local skills"

  for link_dir in "${LINK_DIRS[@]}"; do
    for skill_dir in "$SOURCE_DIR"/*/; do
      [[ -d "$skill_dir" ]] || continue
      skill_name=$(basename "$skill_dir")
      rm -rf "$link_dir/$skill_name" 2>/dev/null || true
      ln -s "$TARGET_DIR/$skill_name" "$link_dir/$skill_name"
    done
  done
else
  echo "  No local skills directory found, skipping"
fi

# ═══════════════════════════════════════════════════════════
# Phase 2: Download from skill-lock.json
# ═══════════════════════════════════════════════════════════
echo ""
echo "=== Phase 2: Remote Skills ==="
echo "Lock file: $LOCK_FILE"

if [ -f "$LOCK_FILE" ]; then
  skill_list=$(mktemp /tmp/skill-list.XXXXXX)
  python3 -c "
import json
with open('$LOCK_FILE') as f:
    d = json.load(f)
for name, info in d['skills'].items():
    print(f\"{name}|{info['sourceUrl']}|{info['skillPath']}|{info['gitHash']}\")
" > "$skill_list"

  skill_count=$(wc -l < "$skill_list" | tr -d ' ')
  installed=0
  skipped=0
  idx=0

  while IFS='|' read -r skill_name repo_url skill_path git_hash; do
    [ -z "$skill_name" ] && continue
    idx=$((idx + 1))
    echo "[$idx/$skill_count] $skill_name"

    clone_dir="$CLONE_BASE/$skill_name"
    if [ -d "$clone_dir/.git" ]; then
      cd "$clone_dir"
      git fetch --depth 1 origin "$git_hash" 2>/dev/null || true
      git checkout "$git_hash" --quiet 2>/dev/null || true
    else
      rm -rf "$clone_dir"
      git clone --depth 1 "$repo_url" "$clone_dir" --quiet 2>/dev/null || {
        echo "  !! FAIL: clone $repo_url"
        continue
      }
      cd "$clone_dir"
      git fetch --depth 1 origin "$git_hash" 2>/dev/null || true
      git checkout "$git_hash" --quiet 2>/dev/null || true
    fi

    src="$clone_dir/$skill_path"
    dest="$TARGET_DIR/$skill_name"
    rm -rf "$dest"
    mkdir -p "$dest"

    if [ -f "$src" ]; then
      cp "$src" "$dest/SKILL.md"
    elif [ -d "$src" ]; then
      cp -rL "$src"/. "$dest"/
    else
      echo "  !! WARN: not found at $skill_path"
      skipped=$((skipped + 1))
      continue
    fi

    for link_dir in "${LINK_DIRS[@]}"; do
      rm -rf "$link_dir/$skill_name" 2>/dev/null || true
      ln -s "$TARGET_DIR/$skill_name" "$link_dir/$skill_name"
    done

    installed=$((installed + 1))
    echo "  -> $dest"
  done < "$skill_list"

  rm -f "$skill_list"

  # Update lock file timestamps
  now=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
  python3 -c "
import json
with open('$LOCK_FILE') as f:
    d = json.load(f)
for name in d['skills']:
    d['skills'][name]['updatedAt'] = '$now'
with open('$LOCK_FILE', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
"
  echo ""
  echo "  Installed: $installed | Skipped: $skipped"
  echo "  Lock file updated: updatedAt = $now"
else
  echo "  No lock file found, skipping"
fi

echo ""
echo "=== Done ==="
