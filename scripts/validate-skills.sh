#!/usr/bin/env bash
# Validate all sub-SKILL frontmatters, references, and routing table consistency.
# Run from repo root: bash scripts/validate-skills.sh

set -euo pipefail

errors=0
warnings=0
skills=0

say()  { echo "[validate] $*"; }
err()  { echo "  ERROR: $*"; ((errors++)); }
warn() { echo "  WARN:  $*"; ((warnings++)); }

# ── 1. Frontmatter completeness ──────────────────────────────
say "Checking frontmatter..."
for f in references/*/SKILL.md; do
  name=$(grep '^name:' "$f" | head -1 | sed 's/name: *//' || true)
  desc=$(grep '^description:' "$f" | head -1 | sed 's/description: *//' || true)
  cats=$(grep '^categories:' "$f" | head -1 || true)
  trig=$(grep '^triggers:' "$f" | head -1 || true)
  [[ -z "$name" ]]  && { err "$f: missing name"; continue; }
  [[ -z "$desc" ]]  && err "$f: missing description"
  [[ -z "$cats" ]]  && err "$f: missing categories"
  [[ -z "$trig" ]]  && err "$f: missing triggers"
  ((skills++))
done

# ── 2. Referenced files exist ────────────────────────────────
say "Checking referenced files..."
for md in references/*/SKILL.md; do
  dir=$(dirname "$md")
  # Find all .md references inside the file
  while IFS= read -r ref; do
    # Resolve relative paths
    if [[ "$ref" != /* ]]; then
      ref="$dir/$ref"
    fi
    if [[ ! -f "$ref" ]]; then
      err "$md references non-existent: $ref"
    fi
  done < <(grep -oP '\]\(\K[^)]+\.md' "$md" 2>/dev/null || true)
done

# ── 3. Routing table sync ───────────────────────────────────
say "Checking routing table..."
routing_file="references/skill-routing.md"
[[ -f "$routing_file" ]] || { err "routing table missing: $routing_file"; exit 1; }

for f in references/*/SKILL.md; do
  name=$(grep '^name:' "$f" | head -1 | sed 's/name: *//' || true)
  [[ -z "$name" ]] && continue
  if ! grep -q "\*\*${name}\*\*" "$routing_file"; then
    warn "$name not in routing table"
  fi
done

# ── 4. Script existence ─────────────────────────────────────
say "Checking scripts..."
for s in sync-routing.sh validate-skills.sh planning-resume.sh session-hook.sh; do
  [[ -f "scripts/$s" ]] || warn "missing script: scripts/$s"
done

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "${skills} skills checked — ${errors} errors, ${warnings} warnings"
[[ $errors -gt 0 ]] && exit 1
exit 0
