#!/usr/bin/env bash
# End-to-end verification for vega-punk state machine.
# Run from repo root: bash scripts/verify-punk.sh

set -euo pipefail

errors=0
checks=0
pass=0

ok()   { echo "  PASS: $1"; ((++pass)); ((++checks)); }
fail() { echo "  FAIL: $1"; ((++errors)); ((++checks)); }

say() { echo "[verify-punk] $*"; }

# ── 1. Core files exist ──────────────────────────────────────
say "Checking core files..."
[[ -f "SKILL.md" ]]               && ok "SKILL.md exists"               || fail "SKILL.md missing"
[[ -f "scripts/session-hook.sh" ]] && ok "session-hook.sh exists"        || fail "session-hook.sh missing"
[[ -f "scripts/discover-skills.sh" ]] && ok "discover-skills.sh exists"  || fail "discover-skills.sh missing"
[[ -f "scripts/validate-skills.sh" ]] && ok "validate-skills.sh exists"  || fail "validate-skills.sh missing"

# ── 2. SKILL.md structure ────────────────────────────────────
say "Checking SKILL.md structure..."
grep -q "^name: vega-punk" SKILL.md && ok "frontmatter name" || fail "frontmatter name missing"
grep -q "^description:" SKILL.md   && ok "frontmatter description" || fail "frontmatter description missing"
grep -q "^user-invocable: true" SKILL.md && ok "user-invocable flag" || fail "user-invocable flag missing"

# ── 3. All state sections present ────────────────────────────
say "Checking state sections..."
for state in ROUTE SCAN CLARIFY DESIGN DESIGN_QA DEPENDENCIES SPEC SPEC_QA CONDENSED QUICK HANDOFF REVIEW; do
  grep -q "^## ${state}" SKILL.md && ok "section: $state" || fail "section: $state missing"
done

# ── 4. Required supporting sections ──────────────────────────
say "Checking supporting sections..."
grep -q "^## Three Hard Disciplines" SKILL.md   && ok "Three Hard Disciplines" || fail "Three Hard Disciplines missing"
grep -q "^## Core Operating Principles" SKILL.md && ok "Core Operating Principles" || fail "Core Operating Principles missing"
grep -q "^## State Machine" SKILL.md             && ok "State Machine diagram"   || fail "State Machine diagram missing"
grep -q "^## Allowed Rollbacks" SKILL.md         && ok "Allowed Rollbacks"       || fail "Allowed Rollbacks missing"
grep -q "^## Reusable QA Pattern" SKILL.md       && ok "Reusable QA Pattern"     || fail "Reusable QA Pattern missing"
grep -q "^## Post-Completion Cleanup" SKILL.md   && ok "Post-Completion Cleanup" || fail "Post-Completion Cleanup missing"
grep -q "^## Self-Recovery Guide" SKILL.md       && ok "Self-Recovery Guide"     || fail "Self-Recovery Guide missing"
grep -q "^## Red Flags" SKILL.md                 && ok "Red Flags table"          || fail "Red Flags table missing"
grep -q "^## Skill Dependencies" SKILL.md        && ok "Skill Dependencies"      || fail "Skill Dependencies missing"
grep -q "^## Key Principles" SKILL.md            && ok "Key Principles"           || fail "Key Principles missing"
grep -q "^## Skill Trigger Reference" SKILL.md   && ok "Skill Trigger Reference" || fail "Skill Trigger Reference missing"

# ── 5. No stale references ───────────────────────────────────
say "Checking for stale references..."
grep -q "skill-routing.md" SKILL.md && fail "still references skill-routing.md" || ok "no stale skill-routing.md ref"
grep -q "self-recovery.md" SKILL.md && fail "still references self-recovery.md" || ok "no stale self-recovery.md ref"

# ── 6. Scripts run cleanly ───────────────────────────────────
say "Checking script execution..."
bash scripts/discover-skills.sh >/dev/null 2>&1 && ok "discover-skills.sh runs" || fail "discover-skills.sh fails"
bash scripts/validate-skills.sh >/dev/null 2>&1 && ok "validate-skills.sh runs" || fail "validate-skills.sh fails"
bash scripts/session-hook.sh >/dev/null 2>&1 && ok "session-hook.sh runs" || fail "session-hook.sh fails"

# ── 7. Git hygiene ──────────────────────────────────────────
say "Checking git hygiene..."
if [[ -f ".gitignore" ]]; then
  grep -q ".vega-punk-state.json" .gitignore && ok "state file in gitignore" || fail "state file not in gitignore"
else
  fail ".gitignore missing"
fi

# ── 8. No time-based metrics ─────────────────────────────────
say "Checking for time-based metrics..."
if grep -qE '< *5 *min|5-minute|< *5 *minutes' SKILL.md; then
  fail "still uses time-based metrics"
else
  ok "no time-based metrics"
fi

# ── 9. New fields present ────────────────────────────────────
say "Checking state file fields..."
grep -q "transition_count" SKILL.md && ok "transition_count documented" || fail "transition_count missing"
grep -q "skill_selection" SKILL.md  && ok "skill_selection documented"  || fail "skill_selection missing"
grep -q "user_satisfaction" SKILL.md && ok "user_satisfaction documented" || fail "user_satisfaction missing"

# ── Summary ──────────────────────────────────────────────────
echo ""
say "$pass/$checks passed, $errors failures"
[[ $errors -gt 0 ]] && exit 1
exit 0
