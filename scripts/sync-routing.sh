#!/usr/bin/env bash
# Auto-generate skill-routing.md from sub-skill frontmatters.
# Run from repo root: bash scripts/sync-routing.sh

set -euo pipefail

ROUTING_FILE="references/skill-routing.md"

# ---------- collect rows from frontmatter ----------
declare -a rows=()
for f in references/*/SKILL.md; do
  name=$(grep '^name:' "$f" | head -1 | sed 's/name: *//')
  desc=$(grep '^description:' "$f" | head -1 | sed 's/description: *//' | sed 's/^"//' | sed 's/"$//')
  triggers=$(grep '^triggers:' "$f" | head -1 | sed 's/triggers: *\[//; s/\]//; s/, */, /g; s/"/`/g')
  [[ -z "$name" ]] && continue
  rows+=("| **${name}** | ${desc} | ${triggers} |")
done

# ---------- known category boundaries (manually curated) ----------
# We keep the section headers but regenerate the table bodies.
# For now, replace the entire file body between the known headers.

# Read existing file to preserve header + categories structure
cat > "$ROUTING_FILE" <<'HEADER'
# Skill Routing Table

Complete dispatch logic for all installed skills. Use during SCAN state to match tasks to skills.

**Auto-generated.** Run `bash scripts/sync-routing.sh` to regenerate after adding or editing a sub-skill.

## How to Route

1. Read the user's task intent
2. Match against categories below (top to bottom)
3. Select ALL relevant skills — tasks often need multiple
4. Note execution order if skills chain (e.g., design → code → test)

---

HEADER

# Build Development Workflow table (vega-punk sub-skills)
{
echo "## Development Workflow"
echo ""
echo "| Skill | When to Use | Triggers |"
echo "|-------|-------------|----------|"
for row in "${rows[@]}"; do
  if echo "$row" | grep -qE '\*\*(plan-builder|plan-executor|task-dispatcher|parallel-swarm|worktree-setup|branch-landing)\*\*'; then
    echo "$row"
  fi
done
echo ""
echo "## Code Quality"
echo ""
echo "| Skill | When to Use | Triggers |"
echo "|-------|-------------|----------|"
for row in "${rows[@]}"; do
  if echo "$row" | grep -qE '\*\*(test-first|root-cause|review-intake|review-request|verify-gate)\*\*'; then
    echo "$row"
  fi
done
echo ""
echo "## External Skills (not in this repo)"
echo ""
echo "| Skill | When to Use | Triggers |"
echo "|-------|-------------|----------|"
for row in "${rows[@]}"; do
  if echo "$row" | grep -qE '\*\*(docx|pdf|pptx|xlsx|frontend-design|flutter-lens|ui-ux-pro-max|brand-guidelines|theme-factory|canvas-design|algorithmic-art|agent-browser|mcp-builder|slack-gif-creator|find-skills|self-improving-agent|skill-creator|internal-comms)\*\*'; then
    echo "$row"
  fi
done
echo ""
cat <<'FOOTER'
---

## Common Skill Chains

Tasks often require multiple skills in sequence. Recognize these patterns:

### Web App Development
```
ui-ux-pro-max → frontend-design → test-first → verify-gate → review-request
```

### Bug Fix
```
root-cause → test-first → verify-gate
```

### Feature Development
```
plan-builder → task-dispatcher → review-request → branch-landing
```

### Design to Code
```
flutter-lens → verify-gate → review-request
```

### Skill Development
```
skill-creator → self-improving-agent (to learn from the experience)
```

---

## Decision Rules

1. **Always select verify-gate** for any implementation task
2. **Always select test-first** for any feature/bugfix in codebases with tests
3. **Always select root-cause** when something is broken or failing
4. **Prefer ui-ux-pro-max over frontend-design** when design decisions come first
5. **Prefer task-dispatcher over parallel-swarm** when there's a roadmap.json
6. **CONDENSED mode** for tasks completable in < 5 minutes of work
7. **Full flow** for anything spanning multiple files, components, or subsystems
FOOTER
} >> "$ROUTING_FILE"

echo "[sync-routing] Regenerated $ROUTING_FILE with ${#rows[@]} skills."
