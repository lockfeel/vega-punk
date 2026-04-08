---
name: plan-executor
description: Use when you have a written implementation plan (roadmap.json) to execute inline in the current session with review checkpoints
categories: ["workflow"]
triggers: ["execute plan", "roadmap.json", "implementation plan", "execute steps"]
user-invocable: true
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep"
hooks:
  SessionStart:
    - type: command
      command: "bash scripts/planning-resume.sh"
---

# Executing Plans (Inline)

Inline execution of roadmap.json — each step runs in this session. For subagent-driven execution, use `task-dispatcher` instead.

## Entry Protocol

```
1. Read roadmap.json
2. Check .vega-punk-state.json (if exists) for execution context
3. Resume from current_step if previously interrupted
```

## Quick Reference

```
A. Load & Review: Read roadmap.json, raise concerns before starting
B. Setup: Invoke worktree-setup → verify baseline tests pass
C. Execute Loop: in_progress → Execute → Verify (verify-gate) → complete → write back
D. On Completion: vega-punk mode → write execution_result; standalone → deliver summary + branch-landing
```

## The Process

### Step 1: Load and Review

1. Read `roadmap.json` — understand goal, phases, steps, current_step
2. If concerns: raise with user before starting
3. If no concerns: proceed

### Step 2: Execute Steps

Step structure, verification types, failure escalation, and anti-patterns are defined in [../plan-builder/SKILL.md](../plan-builder/SKILL.md). Follow them exactly.

For each step:
1. Mark status `"in_progress"`
2. Execute using the specified `tool` and `target` (use `code` field content if present)
3. Verify per **verify-gate** rules
4. On pass → set `"complete"` with outcome summary; on fail → increment `attempts` (max 3, then mark `"failed"` and ask user)
5. Update `current_step`, `metadata`, and `updated` timestamp
6. Write `roadmap.json` back

### Step 2a: Step Type Handling

| Step type | How to execute | Verify with |
|-----------|---------------|-------------|
| `Write` | Write `code` to `target` | `file_exists` / `content_contains` |
| `Edit` | Apply edit from `code` to `target` (read first to disambiguate) | `content_contains` / `content_not_contains` |
| `Bash` | Run command in `target` (never add `--force`/`--yes` unless plan specifies) | `command_success` / `tests_pass` / `build_pass` |
| `Glob`/`Grep` | Search for context before Write/Edit | Non-empty results |
| `WebSearch`/`WebFetch` | Fetch content, write to `findings.json` (not roadmap.json) | `content_contains` on findings |

### Step 2b: Checkpoint Handling

When a step has `checkpoint: true`: execute, verify, then **pause** and wait for user confirmation before advancing.

### Step 2c: Dependency-Aware Execution

Steps with `depends_on` must wait for all dependency steps to be `"complete"`. Independent steps in the same phase can run sequentially without unnecessary pauses.

### Step 3: Complete Development

After all steps complete and verified:
- Announce: "I'm using the branch-landing skill to complete this work."
- Use `branch-landing` to verify tests, present options, execute choice

## Execution Recovery

**Mid-task disconnect:** Read `roadmap.json` → `current_step` shows resume point. If step was `"in_progress"`, re-verify: pass → mark complete; fail → re-execute from scratch.

**Stale roadmap:** If `updated` > 24 hours ago, re-read codebase, compare remaining steps. If diverged → suggest re-planning.

## Execution Anti-Patterns

| Don't | Do |
|-------|-----|
| Skip verification to go faster | Every step must be verified before marking complete |
| Modify the plan without telling user | Raise concerns, let user decide |
| Retry the exact same failing command | Change approach each retry attempt |
| Execute steps out of dependency order | Respect `depends_on` fields |
| Skip checkpoints | Pause and wait for confirmation |
| Edit code beyond what the step specifies | Follow the plan's `code` field exactly |
| Start on main/master branch | Use worktree-setup for isolation |

## Remember
- Read `roadmap.json` first — single source of truth
- Follow each step's `tool`, `target`, and `code` exactly
- Update `roadmap.json` after every step
- Stop when blocked, don't guess
- Never start on main/master without explicit user consent

## Completion Contract

After execution completes and verification passes (or after branch-landing completes):

**If invoked from vega-punk** (`.vega-punk-state.json` exists): update state to "REVIEW" and add `execution_result` per vega-punk REVIEW section.

**If standalone mode**: no state write-back. Deliver summary to user directly.

**If execution fails** (critical step attempts exhausted): if vega-punk mode, update state with "failed" and error details; if standalone, present failure report with suggested fixes.

## Integration

**Required:** worktree-setup (isolation), verify-gate (each step), plan-builder (defines step structure, verification types, failure escalation)

**On completion:** branch-landing

**Code quality:** test-first (each implementation step), review-intake (process feedback), review-request (checkpoints)
