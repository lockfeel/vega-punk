#!/usr/bin/env bash
# discover-skills.sh — Scans all installed skills and outputs { name, description, source, path } as JSON.
# Exit code 0 = success, 1 = no skills found, 2 = partial success (some skills unreadable).

set -euo pipefail

SKILL_DIRS=()
ERRORS=0
RESULTS="[]"

# 1. Scan project-local skills
if [ -d "skills" ]; then
  for d in skills/*/; do
    if [ -f "${d}SKILL.md" ]; then
      SKILL_DIRS+=("${d}")
    fi
  done
fi

# 2. Scan Claude Code global skills
if [ -d "$HOME/.claude/skills" ]; then
  for d in "$HOME/.claude/skills"/*/; do
    if [ -f "${d}SKILL.md" ]; then
      SKILL_DIRS+=("${d}")
    fi
  done
fi

if [ ${#SKILL_DIRS[@]} -eq 0 ]; then
  echo "[]"
  exit 1
fi

# 3. Parse each SKILL.md frontmatter for name + description
JSON="["
FIRST=true
for d in "${SKILL_DIRS[@]}"; do
  SKILL_FILE="${d}SKILL.md"

  # Extract name from frontmatter
  NAME=$(sed -n '/^---$/,/^---$/p' "$SKILL_FILE" 2>/dev/null | sed -n 's/^name: *//p' | head -1 | sed 's/^["'\'']\?\(.*\)\1["'\'']\?$/\1/' | tr -d '"')

  # Extract description from frontmatter
  DESC=$(sed -n '/^---$/,/^---$/p' "$SKILL_FILE" 2>/dev/null | sed -n 's/^description: *//p' | head -1 | sed 's/^["'\'']\?\(.*\)\1["'\'']\?$/\1/' | tr -d '"')

  # Determine source
  if [[ "$d" == "$HOME/.claude/skills/"* ]]; then
    SOURCE="global"
  else
    SOURCE="project"
  fi

  # Normalize path
  ABS_PATH=$(realpath "$SKILL_FILE" 2>/dev/null || echo "$SKILL_FILE")

  # Skip if name is empty
  if [ -z "$NAME" ]; then
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if [ "$FIRST" = true ]; then
    FIRST=false
  else
    JSON+=","
  fi

  # Escape for JSON (minimal: escape quotes and backslashes)
  NAME_ESC=$(echo "$NAME" | sed 's/\\/\\\\/g; s/"/\\"/g')
  DESC_ESC=$(echo "$DESC" | sed 's/\\/\\\\/g; s/"/\\"/g')
  PATH_ESC=$(echo "$ABS_PATH" | sed 's/\\/\\\\/g; s/"/\\"/g')

  JSON+="{\"name\":\"$NAME_ESC\",\"description\":\"$DESC_ESC\",\"source\":\"$SOURCE\",\"path\":\"$PATH_ESC\"}"
done

JSON+="]"

echo "$JSON"

if [ $ERRORS -gt 0 ]; then
  exit 2
fi

exit 0
