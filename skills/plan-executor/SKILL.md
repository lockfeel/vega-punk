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
   - Invoke the `worktree-setup` skill by saying: "I'm using the worktree-setup skill to set up an isolated workspace."
   - worktree-setup will auto-detect project setup, create the worktree, install dependencies, and run baseline tests
   - If worktree-setup reports failing baseline tests → stop and ask user before proceeding

### Step 2: Execute Steps

For each step (respecting `depends_on` — skip steps whose dependencies are not `"complete"`):
1. Mark status `"in_progress"`
2. Execute using the specified `tool` and `target` (use `code` field content if present)
3. Verify per **verify-gate** rules (see Step 2a)
4. On pass → set `"complete"` with outcome summary; on fail → increment `attempts` and set status to `"retrying"` (max 3, then mark `"failed"` and ask user)
5. Update `current_step`, `metadata`, and `updated` timestamp
6. Write `roadmap.json` back

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

### Step 2a: Step Type Handling & Verification Rules (verify-gate)

| Step type | How to execute | Verify with |
|-----------|---------------|-------------|
| `Write` | Write `code` to `target` | `file_exists` + `content_contains` |
| `Edit` | Apply edit from `code` to `target` (read first to disambiguate) | `content_contains` + `content_not_contains` |
| `Bash` | Run command in `target` (never add `--force`/`--yes` unless plan specifies) | `command_success` / `tests_pass` / `build_pass` |
| `Glob`/`Grep` | Search for context before Write/Edit | Non-empty results |
| `WebSearch`/`WebFetch` | Fetch content, write to `findings.json` in the plan directory (not roadmap.json) | `content_contains` on findings |

**verify-gate rules:**
- Every step MUST be verified before marking complete
- `Bash` steps: verify exit code is 0 and/or expected output appears
- `Write`/`Edit` steps: re-read the file, confirm `code` content is present and correct
- `tests_pass`: run the test command specified in the step or the project's default test suite
- `build_pass`: run the project's build command (e.g., `npm run build`, `cargo build`)
- `command_success`: the Bash command exited 0 and produced expected output

### Step 2b: Checkpoint Handling

When a step has `checkpoint: true`: execute, verify, then **pause** and wait for user confirmation before advancing.

### Step 2c: Dependency-Aware Execution

Dependencies are checked before each step in the main Step 2 loop. Steps with `depends_on` must wait for all dependency steps to be `"complete"`. Independent steps in the same phase run sequentially without unnecessary pauses.

### Step 3: Complete Development

After all steps complete and verified:
1. Invoke the `branch-landing` skill by saying: "I'm using the branch-landing skill to complete this work."
2. branch-landing will re-verify tests, present merge/PR/keep/discard options, and execute the user's choice
3. If branch-landing asks for user input, present the options clearly to the user

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

**Required skills — auto-invoked by saying the trigger phrase:**
- `worktree-setup` — at Step 1.6 (fresh start only). Say: "I'm using the worktree-setup skill to set up an isolated workspace." The skill handles directory selection, worktree creation, dependency install, and baseline tests automatically.
- `branch-landing` — at Step 3. Say: "I'm using the branch-landing skill to complete this work." The skill handles test re-verification, user options (merge/PR/keep/discard), and worktree cleanup automatically.
- `plan-builder` — upstream; creates roadmap.json schema and step structure

**Delegation:**
- When invoking a skill, the skill's SKILL.md takes over the conversation. You become the orchestrator — follow the skill's instructions, don't override them.
- After the skill completes, it returns control to you. Resume your own flow from where you left off.
