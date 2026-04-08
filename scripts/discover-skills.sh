#!/usr/bin/env bash
# Discover all registered skills across all sources.
# Outputs a JSON array of skill objects with name, description, and source.
# Run from repo root: bash scripts/discover-skills.sh

set -euo pipefail

OUTPUT="${1:-}"  # optional: output file path, defaults to stdout

# Use node or python3 for JSON assembly (macOS-safe, no grep -P)
json_engine() {
  if command -v node &>/dev/null; then
    echo "node"
  elif command -v python3 &>/dev/null; then
    echo "python3"
  else
    echo ""
  fi
}

ENGINE=$(json_engine)
if [[ -z "$ENGINE" ]]; then
  echo "[]"
  exit 0
fi

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

# ── 1. Local sub-skills (references/*/SKILL.md) ──────────────
for f in references/*/SKILL.md; do
  [[ -f "$f" ]] || continue
  name=$(grep '^name:' "$f" | head -1 | sed 's/name: *//')
  desc=$(grep '^description:' "$f" | head -1 | sed 's/description: *//' | sed 's/^"//' | sed 's/"$//')
  [[ -z "$name" ]] && continue
  echo "$name	$desc	local	$f" >> "$TMPFILE"
done

# ── 2. System skills (from main SKILL.md dependency table) ───
# Extract all **skill-name** references from the Skill Dependencies section
if [[ -f "SKILL.md" ]]; then
  # Get everything under "## Skill Dependencies" to end of file
  awk '/^## Skill Dependencies/{found=1; next} found' SKILL.md | \
    grep -o '\*\*[a-z][a-z0-9_-]*\*\*' | sed 's/\*\*//g' | sort -u | while read -r name; do
    # Skip if it's a local skill
    if [[ -f "references/${name}/SKILL.md" ]]; then
      continue
    fi
    # Avoid duplicates
    if grep -q "^${name}	" "$TMPFILE" 2>/dev/null; then
      continue
    fi
    echo "$name	external system skill	system	-" >> "$TMPFILE"
  done
fi

# ── 3. Platform skills (~/.claude/skills, .claude/skills) ───
for dir in "$HOME/.claude/skills" ".claude/skills"; do
  [[ -d "$dir" ]] || continue
  for f in "$dir"/*/SKILL.md "$dir"/*.md; do
    [[ -f "$f" ]] || continue
    name=$(grep '^name:' "$f" | head -1 | sed 's/name: *//')
    desc=$(grep '^description:' "$f" | head -1 | sed 's/description: *//' | sed 's/^"//' | sed 's/"$//')
    [[ -z "$name" ]] && name=$(basename "$(dirname "$f")")
    # Avoid duplicates
    if grep -q "^${name}	" "$TMPFILE" 2>/dev/null; then
      continue
    fi
    echo "$name	$desc	platform	$f" >> "$TMPFILE"
  done
done

# ── 4. Assemble JSON ─────────────────────────────────────────
if [[ ! -s "$TMPFILE" ]]; then
  echo "[]"
else
  if [[ "$ENGINE" == "node" ]]; then
    node -e "
      const fs = require('fs');
      const lines = fs.readFileSync(process.argv[1], 'utf8').trim().split('\n').filter(l => l);
      const skills = lines.map(l => {
        const [name, desc, source, path] = l.split('\t');
        const obj = { name, description: desc, source };
        if (path && path !== '-') obj.path = path;
        return obj;
      });
      console.log(JSON.stringify(skills, null, 2));
    " "$TMPFILE"
  else
    python3 -c "
import json, sys
skills = []
with open(sys.argv[1]) as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) < 3: continue
        name, desc, source = parts[0], parts[1], parts[2]
        obj = {'name': name, 'description': desc, 'source': source}
        if len(parts) > 3 and parts[3] != '-':
            obj['path'] = parts[3]
        skills.append(obj)
print(json.dumps(skills, indent=2, ensure_ascii=False))
    " "$TMPFILE"
  fi
fi

# Write to file if specified
if [[ -n "$OUTPUT" ]]; then
  if [[ "$ENGINE" == "node" ]]; then
    node -e "
      const fs = require('fs');
      const lines = fs.readFileSync(process.argv[1], 'utf8').trim().split('\n').filter(l => l);
      const skills = lines.map(l => {
        const [name, desc, source, path] = l.split('\t');
        const obj = { name, description: desc, source };
        if (path && path !== '-') obj.path = path;
        return obj;
      });
      fs.writeFileSync(process.argv[2], JSON.stringify(skills, null, 2) + '\n');
    " "$TMPFILE" "$OUTPUT"
  else
    python3 -c "
import json, sys
skills = []
with open(sys.argv[1]) as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) < 3: continue
        name, desc, source = parts[0], parts[1], parts[2]
        obj = {'name': name, 'description': desc, 'source': source}
        if len(parts) > 3 and parts[3] != '-':
            obj['path'] = parts[3]
        skills.append(obj)
with open(sys.argv[2], 'w') as f:
    json.dump(skills, f, indent=2, ensure_ascii=False)
    f.write('\n')
    " "$TMPFILE" "$OUTPUT"
  fi
fi
