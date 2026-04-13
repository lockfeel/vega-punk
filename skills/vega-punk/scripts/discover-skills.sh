#!/usr/bin/env bash

set -euo pipefail

OUTPUT="${1:-}"

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

if [[ -f "SKILL.md" ]]; then
  awk '/^## Skill Dependencies/{found=1; next} found' SKILL.md | \
    grep -o '\*\*[a-z][a-z0-9_-]*\*\*' | sed 's/\*\*//g' | sort -u | while read -r name; do
    echo "$name	external system skill	system	-" >> "$TMPFILE"
  done
fi

platform_dirs=(
  "$HOME/.claude/skills"
  "$HOME/.openclaw/skills"
  "$HOME/.openclaw/workspace/skills"
)

for dir in "${platform_dirs[@]}"; do
  [[ -d "$dir" ]] || continue
  for f in "$dir"/*/SKILL.md "$dir"/*.md; do
    [[ -f "$f" ]] || continue
    name=$(grep '^name:' "$f" 2>/dev/null | head -1 | sed 's/name: *//' || true)
    desc=$(grep '^description:' "$f" 2>/dev/null | head -1 | sed 's/description: *//' | sed 's/^"//' | sed 's/"$//' || true)
    [[ -z "$name" ]] && name=$(basename "$(dirname "$f")")
    echo "$name	$desc	platform	$f" >> "$TMPFILE"
  done
done

if [[ ! -s "$TMPFILE" ]]; then
  echo "[]"
else
  if [[ "$ENGINE" == "node" ]]; then
    node -e "
      const fs = require('fs');
      const lines = fs.readFileSync(process.argv[1], 'utf8').trim().split('\n').filter(l => l);
      const priority = { local: 0, system: 1, platform: 2 };
      const seen = {};
      for (const l of lines) {
        const [name, desc, source, path] = l.split('\t');
        if (!seen[name] || priority[source] < priority[seen[name].source]) {
          seen[name] = { name, description: desc, source };
          if (path && path !== '-') seen[name].path = path;
        }
      }
      console.log(JSON.stringify(Object.values(seen), null, 2));
    " "$TMPFILE"
  else
    python3 -c "
import json, sys
priority = {'local': 0, 'system': 1, 'platform': 2}
seen = {}
with open(sys.argv[1]) as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) < 3: continue
        name, desc, source = parts[0], parts[1], parts[2]
        if name not in seen or priority.get(source, 99) < priority.get(seen[name]['source'], 99):
            obj = {'name': name, 'description': desc, 'source': source}
            if len(parts) > 3 and parts[3] != '-':
                obj['path'] = parts[3]
            seen[name] = obj
print(json.dumps(list(seen.values()), indent=2, ensure_ascii=False))
    " "$TMPFILE"
  fi
fi

if [[ -n "$OUTPUT" ]]; then
  if [[ "$ENGINE" == "node" ]]; then
    node -e "
      const fs = require('fs');
      const lines = fs.readFileSync(process.argv[1], 'utf8').trim().split('\n').filter(l => l);
      const priority = { local: 0, system: 1, platform: 2 };
      const seen = {};
      for (const l of lines) {
        const [name, desc, source, path] = l.split('\t');
        if (!seen[name] || priority[source] < priority[seen[name].source]) {
          seen[name] = { name, description: desc, source };
          if (path && path !== '-') seen[name].path = path;
        }
      }
      fs.writeFileSync(process.argv[2], JSON.stringify(Object.values(seen), null, 2) + '\n');
    " "$TMPFILE" "$OUTPUT"
  else
    python3 -c "
import json, sys
priority = {'local': 0, 'system': 1, 'platform': 2}
seen = {}
with open(sys.argv[1]) as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) < 3: continue
        name, desc, source = parts[0], parts[1], parts[2]
        if name not in seen or priority.get(source, 99) < priority.get(seen[name]['source'], 99):
            obj = {'name': name, 'description': desc, 'source': source}
            if len(parts) > 3 and parts[3] != '-':
                obj['path'] = parts[3]
            seen[name] = obj
with open(sys.argv[2], 'w') as f:
    json.dump(list(seen.values()), f, indent=2, ensure_ascii=False)
    f.write('\n')
    " "$TMPFILE" "$OUTPUT"
  fi
fi
