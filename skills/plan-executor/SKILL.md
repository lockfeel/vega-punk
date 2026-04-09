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

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: roadmap.json */
    IF roadmap.json does NOT exist:
        IF .vega-punk-state.json exists:
            /* Try to find roadmap in same directory as state file */
            state_dir = directory of .vega-punk-state.json
            IF state_dir/roadmap.json exists:
                USE state_dir/roadmap.json
            ELSE:
                FAIL: "[plan-executor] roadmap.json not found. Planning phase may not have completed."
                EXIT
        ELSE:
            FAIL: "[plan-executor] No roadmap.json and no state file. Nothing to execute."
            EXIT

    READ roadmap.json

    /* Validate roadmap structure */
    IF phases field missing OR phases is empty:
        FAIL: "[plan-executor] roadmap.json has no phases. Invalid plan."
        EXIT

    IF current_step field missing:
        /* Auto-initialize to first step */
        current_step = phases[0].steps[0].id
        current_phase = phases[0].id
        WRITE roadmap.json
        TELL: "[plan-executor] current_step was missing. Auto-set to {current_step}."

    /* Check if worktree is needed */
    IF .vega-punk-state.json exists:
        IF worktree_path field missing:
            TELL: "[plan-executor] No worktree found. Invoking worktree-setup to create one."
            INVOKE worktree-setup via Skill tool
        ELSE IF worktree_path directory does NOT exist:
            TELL: "[plan-executor] Worktree at {worktree_path} no longer exists. Recreating."
            INVOKE worktree-setup via Skill tool
    /* else: standalone mode — no worktree needed */
END
```

## Entry Protocol

```
1. Read roadmap.json (same directory as .vega-punk-state.json)
2. Check .vega-punk-state.json (same directory, if exists) for execution context
3. IF resuming (current_step != first step AND branch already exists):
       GOTO Step 1.5 (resume path)
   ELSE:
       GOTO Step 1.6 (fresh start path)
   Resume from current_step
```

**File locations** — `.vega-punk-state.json`, `roadmap.json`, `findings.json`, and `progress.json` all live in the same directory.

## Quick Reference

```
A. Load & Review: Read roadmap.json, check concerns, resolve or raise before starting
B. Setup: Invoke worktree-setup (fresh start only) — it handles baseline tests internally
C. Execute Loop: check deps → in_progress → Execute → Verify (verify-gate) → complete → write back
D. On Completion: Invoke branch-landing — it handles test re-verify, options, and cleanup
```

## The Process

### Step 1: Load and Review

1. Read `roadmap.json` — understand goal, phases, steps, current_step
2. Review `roadmap.json` schema awareness:
   - Each step has: `id`, `description`, `tool`, `target`, `code`, `status`, `attempts` (default 0), `checkpoint` (optional bool), `depends_on` (optional array of step IDs)
   - `attempts` is auto-incremented on each failed verification (max 3)
   - Phase objects have: `name`, `status`, `steps`
3. If concerns: raise with user before starting
4. If no concerns: proceed
5. IF resuming from a previous session (current_step != first step, branch already exists):
   - Re-read the current step's target files
   - Re-run the step's verification method
   - If already passing → mark complete, advance current_step
   - If failing → keep status `in_progress`, re-execute from scratch
6. ELSE (fresh start):
   - Invoke the `worktree-setup` skill via Skill tool — it handles baseline tests internally
   - worktree-setup will auto-detect project setup, create the worktree, install dependencies, and run baseline tests
   - If worktree-setup reports failing baseline tests → stop and ask user before proceeding

### Step 2: Execute Steps

For each step (respecting `depends_on` — skip steps whose dependencies are not `"complete"`):
1. Mark status `"in_progress"`
2. **Classify step type** before executing:
   - If step involves **bug fix, crash, error, or unexpected behavior** → invoke `root-cause` skill first, follow its Phase 1-3 before writing any code
   - If step involves **new feature, behavior change, or refactoring** → invoke `test-first` skill, follow RED-GREEN-REFACTOR cycle
   - If step is **context gathering** (Glob, Grep, WebSearch) → execute directly
3. Execute using the specified `tool` and `target` (use `code` field content if present)
4. **Explicitly invoke `verify-gate` via Skill tool** — pass the step's verification target. verify-gate will run the command, check output, and return pass/fail.
5. On pass → set `"complete"` with outcome summary; on fail → increment `attempts` and set status to `"retrying"` (max 3, then mark `"failed"` and ask user)
6. Update `current_step`, `metadata`, and `updated` timestamp
7. Write `roadmap.json` back

Use the `Write` tool to rewrite roadmap.json after each step.

```
BEGIN STEP_MACHINE
    READ current roadmap.json
    IDENTIFY step = roadmap[current_step]

    /* ── Step Success ── */
    CASE step verification PASSED:
        step.status = "complete"
        step.result = "<brief outcome summary>"
        roadmap.current_step = next pending step id
        roadmap.metadata.completed_steps++
        roadmap.metadata.completion_rate = STRING(ROUND(roadmap.metadata.completed_steps / roadmap.metadata.total_steps * 100)) + "%"
        roadmap.updated = now

        /* Phase boundary check */
        IF all steps in current phase are complete:
            current_phase.status = "complete"
            IF next phase exists:
                next_phase.status = "in_progress"
                roadmap.current_phase++
        WRITE roadmap.json
        EXIT

    /* ── Step Failure — unified retry logic ── */
    CASE step verification FAILED:
        step.status = "retrying"
        step.attempts++
        roadmap.updated = now

        IF step.attempts >= 3:
            step.status = "failed"
            step.result = "<error description>"
            WRITE roadmap.json
            APPEND to progress.json (same directory): { timestamp, step_id, error }
            IF step.critical == true:
                ASK user for direction — do not advance to next steps
            ELSE:
                roadmap.current_step = next pending step id
                WRITE roadmap.json
                CONTINUE loop
        ELSE IF step.attempts == 1:
            /* First failure — planned approach didn't work */
            step.result = "<attempt 1 failed: brief reason>"
            WRITE roadmap.json
            RE-READ target → ANALYZE → ADJUST approach → RETRY
        ELSE IF step.attempts == 2:
            /* Second failure — need a different strategy */
            step.result = "<attempt 2 failed: brief reason>"
            WRITE roadmap.json
            TRY completely different approach or tool → RETRY
END
```

### Step 2a: Step Type Handling

| Step type | How to execute | Verify with |
|-----------|---------------|-------------|
| `Write` | Write `code` to `target` | `file_exists` + `content_contains` |
| `Edit` | Apply edit from `code` to `target` (read first to disambiguate) | `content_contains` + `content_not_contains` |
| `Bash` | Run command in `target` (never add `--force`/`--yes` unless plan specifies) | `command_success` / `tests_pass` / `build_pass` |
| `Glob`/`Grep` | Search for context before Write/Edit | Non-empty results |
| `WebSearch`/`WebFetch` | Fetch content, write to `findings.json` in the plan directory (not roadmap.json) | `content_contains` on findings |

**verify-gate rules** — invoke the `verify-gate` skill via the `Skill` tool at each verification point. See verify-gate's SKILL.md for the full rule set: evidence before claims, no success claims without fresh verification output, etc.

### Step 2b: Checkpoint Handling

When a step has `checkpoint: true`: execute, verify, then **pause** and wait for user confirmation before advancing.

### Step 2c: Dependency-Aware Execution

Dependencies are checked before each step in the main Step 2 loop. Steps with `depends_on` must wait for all dependency steps to be `"complete"`. Independent steps in the same phase run sequentially without unnecessary pauses.

### Step 3: Complete Development

After all steps reach a terminal state (`"complete"` or non-critical `"failed"`):

1. **Check completion eligibility:**
   - All `critical: true` steps must be `"complete"`
   - `critical: false` steps may be `"complete"` or `"failed"`
   - If any `critical: true` step is not `"complete"` → do NOT proceed to review, report status and wait for user direction
2. **Invoke the `review-request` skill via Skill tool** — pass the full git range from first to last commit for final pre-merge code quality review
3. **Invoke `verify-gate` via Skill tool** — final mechanical check (tests pass, build clean, lint ok) after review-request passes
4. **Invoke the `branch-landing` skill via Skill tool** — branch-landing will re-verify tests, present merge/PR/keep/discard options, and execute the user's choice
5. If branch-landing asks for user input, present the options clearly to the user

## Execution Recovery

**Mid-task disconnect:** Read `roadmap.json` → `current_step` shows resume point. If step was `"in_progress"` or `"retrying"`, re-verify by running the step's verification method (tests, build, or file content check): pass → mark complete; fail → re-execute from scratch.

**Stale roadmap:** If `updated` > 24 hours ago, re-read codebase, compare remaining steps against actual file state. If diverged → suggest re-planning.

**Progress logging:** On step failures, append to `progress.json` (same directory as `roadmap.json` and `.vega-punk-state.json`). Format: `{ "timestamp": "<ISO8601>", "step_id": "<id>", "error": "<description>" }`. This file is optional — skip logging if it doesn't exist.

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
| Let a long step hang indefinitely | If a step takes > 5 minutes with no progress, report status and ask user |

## Remember
- Read `roadmap.json` first — single source of truth
- Follow each step's `tool`, `target`, and `code` exactly
- Update `roadmap.json` after every step
- Stop when blocked, don't guess
- Never start on main/master without explicit user consent

## Completion Contract

After execution completes and verification passes (or after branch-landing completes):

```
BEGIN COMPLETION_CONTRACT
    /* Invoked from vega-punk — write back execution_result */
    IF .vega-punk-state.json exists (same directory as roadmap.json):
        IF all critical steps completed successfully:
            WRITE .vega-punk-state.json:
                state = "REVIEW"
                execution_result = {
                    status: "success",
                    summary: "<brief outcome>",
                    artifacts: ["<list of created/modified files>"],
                    verification: "<pass/fail + method>",
                    notes: "<any caveats or follow-ups>"
                }
        ELSE IF any critical steps failed:
            WRITE .vega-punk-state.json:
                state = "REVIEW"
                execution_result = {
                    status: "failed",
                    summary: "<error summary>",
                    notes: "<failed step IDs + suggested fixes>"
                }
        ELSE:
            /* Partial success — all critical steps done, some non-critical skipped/failed */
            WRITE .vega-punk-state.json:
                state = "REVIEW"
                execution_result = {
                    status: "partial",
                    summary: "<completed X of Y steps>",
                    artifacts: ["<list of created/modified files>"],
                    verification: "<pass/fail + method>",
                    notes: "<skipped non-critical step IDs + reason>"
                }
    /* Standalone mode — no state write-back, present to user directly */
    ELSE:
        IF all critical steps completed successfully:
            PRESENT final summary: completed steps, artifacts, verification status
        ELSE IF any critical steps failed:
            PRESENT failure report: specific step(s) that failed, suggested fixes
        ELSE:
            PRESENT partial report: completed steps, skipped non-critical steps, artifacts
END
```

## Integration

**Required skills — auto-invoked via Skill tool:**
- `worktree-setup` — at Step 1.6 (fresh start only) via Skill tool
- `root-cause` — at Step 2 when step involves bug fix, crash, error, or unexpected behavior
- `test-first` — at Step 2 when step involves new feature, behavior change, or refactoring
- `verify-gate` — invoked via Skill tool at each step verification point (Step 2.4); and at Step 3.3 before landing
- `review-request` — at Step 3.2 for final pre-merge code quality review
- `branch-landing` — at Step 3.4 via Skill tool
- `plan-builder` — upstream; creates roadmap.json schema and step structure

**Delegation:**
- When invoking a skill, the skill's SKILL.md takes over the conversation. You become the orchestrator — follow the skill's instructions, don't override them.
- After the skill completes, it returns control to you. Resume your own flow from where you left off.
