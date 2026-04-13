---
name: plan-executor
description: Use when you have a written implementation plan (~/.vega-punk/roadmap.json) to execute inline in the current session with review checkpoints
categories: ["workflow"]
triggers: ["execute plan", "~/.vega-punk/roadmap.json", "implementation plan", "execute steps"]
user-invocable: true
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep"
hooks:
  SessionStart:
    - type: command
      command: "bash scripts/planning-resume.sh"
---

# Executing Plans (Inline)

Inline execution of ~/.vega-punk/roadmap.json — each step runs in this session. For subagent-driven execution, use `task-dispatcher` instead.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations. 

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: ~/.vega-punk/roadmap.json */
    IF ~/.vega-punk/roadmap.json does NOT exist:
        IF ~/.vega-punk/vega-punk-state.json exists:
            /* Try to find roadmap in same directory as state file */
            state_dir = directory of ~/.vega-punk/vega-punk-state.json
            IF state_dir/roadmap.json exists:
                USE state_dir/roadmap.json
            ELSE:
                FAIL: "[plan-executor] ~/.vega-punk/roadmap.json not found. Planning phase may not have completed."
                EXIT
        ELSE:
            FAIL: "[plan-executor] No ~/.vega-punk/roadmap.json and no state file. Nothing to execute."
            EXIT

    READ ~/.vega-punk/roadmap.json

    /* Validate roadmap structure */
    IF phases field missing OR phases is empty:
        FAIL: "[plan-executor] ~/.vega-punk/roadmap.json has no phases. Invalid plan."
        EXIT

    IF current_step field missing:
        /* Auto-initialize to first step */
        current_step = phases[0].steps[0].id
        current_phase = phases[0].id
        WRITE ~/.vega-punk/roadmap.json
        TELL: "[plan-executor] current_step was missing. Auto-set to {current_step}."

    /* Check if worktree is needed */
    IF ~/.vega-punk/vega-punk-state.json exists:
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
BEGIN ENTRY_PROTOCOL
    READ ~/.vega-punk/roadmap.json (same directory as ~/.vega-punk/vega-punk-state.json)
    CHECK ~/.vega-punk/vega-punk-state.json for execution context (if exists)

    IF resuming (current_step != first step AND branch already exists):
        RE-READ current step's target files
        RE-RUN step's verification method
        IF already passing:
            MARK complete, advance current_step
        IF failing:
            KEEP status "in_progress", re-execute from scratch
    ELSE (fresh start):
        INVOKE worktree-setup skill via Skill tool
        IF worktree-setup reports failing baseline tests:
            STOP and ask user before proceeding

    /* File locations: ~/.vega-punk/vega-punk-state.json, roadmap.json, findings.json, progress.json all in same directory */
END
```

## Quick Reference

```
BEGIN QUICK_REFERENCE
    A. Load & Review:
        READ ~/.vega-punk/roadmap.json
        CHECK concerns → resolve or raise before starting

    B. Setup:
        INVOKE worktree-setup (fresh start only)
        /* worktree-setup handles baseline tests internally */

    C. Execute Loop:
        FOR each step (respecting depends_on):
            CHECK deps → status "in_progress"
            CLASSIFY step type:
                bug fix / crash / error → INVOKE root-cause first
                new feature / behavior change / refactoring → INVOKE test-first
                context gathering → execute directly
            EXECUTE using tool + target + code
            INVOKE verify-gate via Skill tool
            IF pass → "complete" with outcome summary
            IF fail → increment attempts, "retrying" (max 3, then "failed")
            UPDATE current_step, metadata, updated
            WRITE ~/.vega-punk/roadmap.json back

    D. On Completion:
        INVOKE branch-landing via Skill tool
        /* branch-landing handles test re-verify, options, cleanup */
END
```

## The Process

### Step 1: Load and Review

```
BEGIN STEP1_LOAD_REVIEW
    READ ~/.vega-punk/roadmap.json — understand goal, phases, steps, current_step
    REVIEW schema awareness:
        - Each step: id, description, tool, target, code, status, attempts (default 0), checkpoint (optional), depends_on (optional)
        - attempts auto-incremented on failed verification (max 3)
        - Phase objects: name, status, steps
    IF concerns: raise with user before starting
    IF no concerns: proceed

    /* Resume path */
    IF resuming (current_step != first step, branch exists):
        RE-READ current step's target files
        RE-RUN step's verification method
        IF passing → mark complete, advance current_step
        IF failing → keep "in_progress", re-execute from scratch
    /* Fresh start path */
    ELSE:
        INVOKE worktree-setup skill via Skill tool
        IF failing baseline tests → stop and ask user
END
```

### Step 2: Execute Steps

```
BEGIN STEP2_EXECUTE
    FOR each step (respecting depends_on — skip if dependencies not "complete"):
        /* Mark in progress */
        step.status = "in_progress"

        /* Classify step type */
        IF bug fix / crash / error / unexpected behavior:
            INVOKE root-cause skill — follow Phase 1-3 before writing code
        IF new feature / behavior change / refactoring:
            INVOKE test-first skill — follow RED-GREEN-REFACTOR cycle
        IF context gathering (Glob, Grep, WebSearch):
            EXECUTE directly

        /* Execute using specified tool and target */
        CASE tool = "Write":
            WRITE code to target → verify: file_exists + content_contains
        CASE tool = "Edit":
            APPLY edit (read first to disambiguate) → verify: content_contains + content_not_contains
        CASE tool = "Bash":
            RUN command (never add --force/--yes unless plan specifies)
            → verify: command_success / tests_pass / build_pass
        CASE tool = "Glob" / "Grep":
            SEARCH for context → verify: non-empty results
        CASE tool = "WebSearch" / "WebFetch":
            FETCH content, write to findings.json → verify: content_contains on findings

        /* Verify with verify-gate */
        INVOKE verify-gate via Skill tool with step's verification target

        /* Handle result */
        IF pass:
            step.status = "complete"
            step.result = "<brief outcome summary>"
        IF fail:
            step.attempts++
            IF attempts >= 3:
                step.status = "failed"
                APPEND to ~/.vega-punk/progress.json: { timestamp, step_id, error }
                IF step.critical == true:
                    ASK user for direction — do NOT advance
                ELSE:
                    ADVANCE to next pending step
            ELSE:
                step.status = "retrying"
                step.result = "<attempt N failed: brief reason>"
                RE-READ target → ANALYZE → ADJUST approach → RETRY

        /* Checkpoint handling */
        IF step.checkpoint == true:
            PAUSE and wait for user confirmation before advancing

        UPDATE current_step, metadata, updated timestamp
        WRITE ~/.vega-punk/roadmap.json back
END
```

### Step 3: Complete Development

```
BEGIN STEP3_COMPLETE
    /* Check completion eligibility */
    FOR EACH step:
        IF critical == true AND status != "complete":
            DO NOT proceed to review
            REPORT status, wait for user direction
            STOP

    /* All critical steps done */
    INVOKE review-request via Skill tool (full git range from first to last commit)
    INVOKE verify-gate via Skill tool (final mechanical check: tests, build, lint)
    INVOKE branch-landing via Skill tool
    /* branch-landing re-verifies tests, presents merge/PR/keep/discard options */
END
```

```
BEGIN STEP_MACHINE
    READ current ~/.vega-punk/roadmap.json
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
        WRITE ~/.vega-punk/roadmap.json
        EXIT

    /* ── Step Failure — unified retry logic ── */
    CASE step verification FAILED:
        step.status = "retrying"
        step.attempts++
        roadmap.updated = now

        IF step.attempts >= 3:
            step.status = "failed"
            step.result = "<error description>"
            WRITE ~/.vega-punk/roadmap.json
            APPEND to ~/.vega-punk/progress.json (same directory): { timestamp, step_id, error }
            IF step.critical == true:
                ASK user for direction — do not advance to next steps
            ELSE:
                roadmap.current_step = next pending step id
                WRITE ~/.vega-punk/roadmap.json
                CONTINUE loop
        ELSE IF step.attempts == 1:
            /* First failure — planned approach didn't work */
            step.result = "<attempt 1 failed: brief reason>"
            WRITE ~/.vega-punk/roadmap.json
            RE-READ target → ANALYZE → ADJUST approach → RETRY
        ELSE IF step.attempts == 2:
            /* Second failure — need a different strategy */
            step.result = "<attempt 2 failed: brief reason>"
            WRITE ~/.vega-punk/roadmap.json
            TRY completely different approach or tool → RETRY
END
```

### Step 2a: Step Type Handling

(Already integrated in STEP2_EXECUTE above. See verify-gate's SKILL.md for full rule set.)

### Step 2b: Checkpoint Handling

(Already integrated in STEP2_EXECUTE above.)

### Step 2c: Dependency-Aware Execution

(Already integrated in STEP2_EXECUTE above.)

## Execution Recovery

**Mid-task disconnect:** Read `~/.vega-punk/roadmap.json` → `current_step` shows resume point. If step was `"in_progress"` or `"retrying"`, re-verify by running the step's verification method (tests, build, or file content check): pass → mark complete; fail → re-execute from scratch.

**Stale roadmap:** If `updated` > 24 hours ago, re-read codebase, compare remaining steps against actual file state. If diverged → suggest re-planning.

**Progress logging:** On step failures, append to `~/.vega-punk/progress.json` (same directory as `~/.vega-punk/roadmap.json` and `~/.vega-punk/vega-punk-state.json`). Format: `{ "timestamp": "<ISO8601>", "step_id": "<id>", "error": "<description>" }`. This file is optional — skip logging if it doesn't exist.

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
- Read `~/.vega-punk/roadmap.json` first — single source of truth
- Follow each step's `tool`, `target`, and `code` exactly
- Update `~/.vega-punk/roadmap.json` after every step
- Stop when blocked, don't guess
- Never start on main/master without explicit user consent

## Completion Contract

After execution completes and verification passes (or after branch-landing completes):

```
BEGIN COMPLETION_CONTRACT
    /* Invoked from vega-punk — write back execution_result */
    IF ~/.vega-punk/vega-punk-state.json exists (same directory as ~/.vega-punk/roadmap.json):
        IF all critical steps completed successfully:
            WRITE ~/.vega-punk/vega-punk-state.json:
                state = "REVIEW"
                execution_result = {
                    status: "success",
                    summary: "<brief outcome>",
                    artifacts: ["<list of created/modified files>"],
                    verification: "<pass/fail + method>",
                    notes: "<any caveats or follow-ups>"
                }
        ELSE IF any critical steps failed:
            WRITE ~/.vega-punk/vega-punk-state.json:
                state = "REVIEW"
                execution_result = {
                    status: "failed",
                    summary: "<error summary>",
                    notes: "<failed step IDs + suggested fixes>"
                }
        ELSE:
            /* Partial success — all critical steps done, some non-critical skipped/failed */
            WRITE ~/.vega-punk/vega-punk-state.json:
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
- `plan-builder` — upstream; creates ~/.vega-punk/roadmap.json schema and step structure

**Delegation:**
- When invoking a skill, the skill's SKILL.md takes over the conversation. You become the orchestrator — follow the skill's instructions, don't override them.
- After the skill completes, it returns control to you. Resume your own flow from where you left off.
