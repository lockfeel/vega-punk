---
name: task-dispatcher
description: Use when executing implementation plans with independent tasks in the current session
categories: ["workflow"]
triggers: ["subagent-driven development", "dispatch subagent", "implement tasks", "roadmap execution"]
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Two-stage review order:** Spec compliance review first, then code quality review. Rationale: verify we built the right thing before verifying we built it well. A beautifully coded wrong feature is still wrong.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## The Iron Law

```
NEVER DISPATCH WITHOUT FULL CONTEXT — NEVER PROCEED WITHOUT REVIEW PASS
```

1. Every subagent gets complete, verbatim context — no file references, no summaries
2. No task advances past review until the reviewer says PASS
3. No batch advances until verify-gate confirms mechanical soundness

**Violating the letter of this rule is violating the spirit of this rule.**

## What task-dispatcher Does NOT Do

```
task-dispatcher does NOT:
- Write plans (that's plan-builder)
- Execute tasks inline (that's plan-executor)
- Make architectural decisions (that's the plan's job)
- Fix issues itself (it delegates to subagents)
- Validate spec quality (it validates spec compliance, not spec quality)
- Review code aesthetics (it ensures correctness, not beauty)
```

## Task Lifecycle State Machine

Every task follows this state machine. No task may skip states or transition backwards except via explicit rollback.

```
PENDING ──dispatch──→ IMPLEMENTING ──status:DONE──→ SPEC_REVIEW ──PASS──→ QUALITY_REVIEW ──PASS──→ COMPLETED
                         │                          │                     │
                    status:BLOCKED              FAIL: cycle≤2         FAIL: cycle≤1
                    status:NEEDS_CONTEXT            │                     │
                    timeout                         ↓                     ↓
                         │                    FIX_IMPLEMENTING      FIX_IMPLEMENTING
                         ↓                         │                     │
                    ASSESS_BLOCKER            re-review              re-review
                    (max 2 re-dispatches)     (max 3 cycles)         (max 2 cycles)
                         │                         │                     │
                    unresolvable            cycle exhausted        cycle exhausted
                         ↓                         ↓                     ↓
                      FAILED                   FAILED                FAILED

State meanings:
- PENDING:         Task created, waiting for dependencies to clear
- IMPLEMENTING:    Implementer subagent is working
- SPEC_REVIEW:     Spec compliance reviewer is evaluating
- QUALITY_REVIEW:  Code quality reviewer is evaluating
- FIX_IMPLEMENTING: Implementer is fixing review issues (returns to review after)
- COMPLETED:       All reviews passed, task is done
- FAILED:          Unrecoverable — logged to progress.json
```

**Re-dispatch limits:**
- IMPLEMENTING → re-dispatch for BLOCKED/NEEDS_CONTEXT: **max 2 times** (3 total attempts)
- FIX_IMPLEMENTING → re-dispatch for review failure: follows review cycle limits (spec: 3, quality: 2)
- On limit exhaustion → mark FAILED, log to progress.json, continue if non-critical

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: ~/.vega-punk/roadmap.json */
    IF ~/.vega-punk/roadmap.json does NOT exist:
        FAIL: "[task-dispatcher] ~/.vega-punk/roadmap.json not found. Run plan-builder first."
        EXIT

    READ ~/.vega-punk/roadmap.json

    /* Validate roadmap has executable tasks */
    IF phases field missing OR phases is empty:
        FAIL: "[task-dispatcher] ~/.vega-punk/roadmap.json has no phases. Invalid plan."
        EXIT

    /* Count total tasks and check dependency graph */
    total_tasks = count of all steps across all phases
    IF total_tasks == 0:
        FAIL: "[task-dispatcher] ~/.vega-punk/roadmap.json has no tasks. Nothing to dispatch."
        EXIT

    /* Validate every step has target_files */
    FOR each step in each phase:
        IF step has no target_files OR target_files is empty:
            FAIL: "[task-dispatcher] Step {step.id} has no target_files. Every step must specify which files to create/modify."
            EXIT

    /* Setup worktree */
    IF ~/.vega-punk/vega-punk-state.json exists:
        READ ~/.vega-punk/vega-punk-state.json
        IF worktree_path field missing:
            TELL: "[task-dispatcher] No worktree found. Invoking worktree-setup."
            INVOKE worktree-setup via Skill tool
        ELSE IF worktree_path directory does NOT exist:
            TELL: "[task-dispatcher] Worktree at {worktree_path} missing. Recreating."
            INVOKE worktree-setup via Skill tool
    ELSE:
        INVOKE worktree-setup via Skill tool

    /* Handle worktree-setup failure */
    IF worktree-setup invocation FAILED (tool error, not baseline test failure):
        FAIL: "[task-dispatcher] worktree-setup invocation failed: {error details}"
        ASK user: "Worktree setup failed. How would you like to proceed?"

    /* If worktree-setup reports failing baseline tests → stop and ask user */
    IF worktree-setup reported baseline test failures:
        STOP: "Baseline tests are failing. Fix before proceeding."
        ASK user for direction

    /* Record baseline failure count */
    WRITE ~/.vega-punk/vega-punk-state.json: { "baseline_failure_count": <count from worktree-setup> }

    /* Validate no stale .task-status-*.json files from previous run */
    /* IMPORTANT: status files are written to worktree root, NOT current directory */
    IF worktree_path exists:
        IF worktree_path/.task-status-*.json files exist:
            DELETE all worktree_path/.task-status-*.json files
            TELL: "[task-dispatcher] Cleaned up stale task status files from previous run."
    ELSE:
        /* Fallback: check current directory */
        IF .task-status-*.json files exist:
            DELETE all .task-status-*.json files
            TELL: "[task-dispatcher] Cleaned up stale task status files from previous run."
END
```

## When to Use

**Use this skill when:**
- You have an implementation plan (`~/.vega-punk/roadmap.json` from plan-builder)
- Tasks are mostly independent (can be dispatched separately)
- You want to stay in the same session (no context switch)

**Decision criteria vs. plan-executor:**

| Factor | task-dispatcher | plan-executor |
|--------|----------------|---------------|
| Task independence | Mostly independent, parallelizable | Sequential, highly coupled |
| Task count | 3+ tasks | 1-3 tasks |
| Review needs | Two-stage review per task | Inline review, simpler |
| Context pressure | Controller needs clean context for coordination | Single context sufficient |
| Speed | Parallel dispatch = faster | Less overhead per task |
| Complexity tolerance | Higher (subagent orchestration) | Lower (simpler flow) |

**Default:** If unsure, start with plan-executor. Escalate to task-dispatcher when task count exceeds 3 and tasks are clearly independent.

## The Process

### Step 1: Read Plan & Build Dependency Graph

Read `~/.vega-punk/roadmap.json` — extract all phases and steps with full context. Build a task dependency graph from `depends_on` fields.

**Build batch plan via topological sort:**
1. Collect all steps across all phases, each with their `depends_on` references
2. Group steps into batches by dependency depth:
   - Batch 0: steps with no `depends_on`
   - Batch 1: steps whose `depends_on` are all in Batch 0
   - Batch N: steps whose `depends_on` are all in Batch 0..N-1
3. If circular dependency detected → FAIL and report to user
4. Record batch plan to `~/.vega-punk/vega-punk-state.json` under key `batch_plan`:
   ```json
   {
     "batches": [
       { "batch_id": 0, "task_ids": ["1_1", "1_2"] },
       { "batch_id": 1, "task_ids": ["1_3"] }
     ],
     "completed_batches": [],
     "partial_batches": [],
     "batch_progress": {},
     "git_commit_map": {}
   }
   ```

**ID format convention:** Step IDs use underscores (e.g., `1_1`, `2_3`) instead of dots to avoid confusion with file extensions in status filenames (`.task-status-1_1.json`).

### Step 2: Create Task Tracker

Create a `TaskCreate` entry per task from the plan. Use status workflow: `pending` → `in_progress` (dispatched) → `in_progress` (reviewing) → `completed`.

Set up `addBlockedBy` dependencies between TaskCreate entries to mirror the `depends_on` relationships from the roadmap.

### Step 3: Dispatch Tasks (respects `depends_on`, dispatches independent tasks in parallel)

For each batch (by batch_id order) in the batch plan:

1. **Verify batch is next in order:** Only proceed if `completed_batches` contains all prior batch_ids. This enables session-resume after interruption.

2. **Check batch_progress for partial completion** (session resume):
   ```
   IF batch_progress[batch_id] exists:
       stage = batch_progress[batch_id].stage
       tasks_done = batch_progress[batch_id].tasks_done || []
       /* Validate worktree consistency before resuming */
       RUN: git -C <worktree_path> status --porcelain
       IF uncommitted changes exist from previous session:
           COMMIT with message: "WIP: resuming session, preserving partial work"
       /* Resume from the exact stage, do NOT re-dispatch completed tasks */
       GOTO stage with tasks_done context
   ```

3. **Check dependencies:** Only dispatch tasks whose `depends_on` steps are all `"completed"`.

4. **Classify each task type** before dispatching:
   - If task involves **bug fix, crash, error, or unexpected behavior** → include `root-cause` skill instructions in the implementer prompt
   - If task involves **new feature, behavior change, or refactoring** → include `test-first` skill instructions (RED-GREEN-REFACTOR) in the implementer prompt

5. **Evaluate parallelism strategy:**
   - IF current batch has ≥ 2 tasks AND all tasks have ZERO mutual depends_on AND tasks target disjoint file sets → use **parallel dispatch** (send multiple Agent tool calls in a single message — this is the correct way to achieve parallel execution)
     - **WARN:** "target_files are disjoint, but watch for implicit conflicts (shared imports, config files, module-level changes)"
     - After parallel implementers complete: check for git conflicts in worktree, resolve before proceeding to review
   - ELSE → dispatch implementer subagents sequentially (one Agent tool call per message)
   - **NEVER** dispatch multiple implementation subagents in parallel **within the same task** (conflicts on shared files)

6. **Dispatch implementer subagents** for all tasks in this batch. Each subagent gets its own task-specific prompt (see Prompt Templates below). For parallel dispatch, send all Agent tool calls in one message.
   - **Timeout:** IF implementer does not return within reasonable time, TREAT as BLOCKED with details "implementer timeout". FOLLOW BLOCKED handling path.
   - **Re-dispatch limit:** Max 2 re-dispatches for BLOCKED/NEEDS_CONTEXT per task (3 total attempts). On exhaustion → mark FAILED.

7. **Collect implementer results** — wait for all implementers to finish. For each task:
   - Read `.task-status-<task_id>.json` from the **worktree root** (use `worktree_path` from `~/.vega-punk/vega-punk-state.json`)
   - **If status file does not exist:** treat as BLOCKED with details "Implementer did not write status file. Check subagent output for clues."
   - **If status file is invalid JSON:** treat as BLOCKED with details "Status file corrupted: {raw content}"
   - **Handle implementer status** (see Handling Implementer Status) — fix or re-dispatch as needed.
   - **Record progress:** Update `batch_progress[batch_id].tasks_done` with completed task IDs

8. **Dispatch spec reviewer subagents** — the **implementer subagent that built the feature** is responsible for fixing issues found in review. Re-dispatch the same implementer with the review findings appended to its prompt. Reviewer reviews again. Max 3 cycles (see Review Error Recovery).
   - **Record progress:** Update `batch_progress[batch_id].stage = "spec_review_done"` when all spec reviews pass

9. **Dispatch code quality reviewer subagents** — same fix responsibility: the **implementer subagent** fixes issues, reviewer re-reviews. Max 2 cycles (see Review Error Recovery).
   - **Record progress:** Update `batch_progress[batch_id].stage = "code_quality_review_done"` when all quality reviews pass

10. **Git commit per task** — after each task passes both reviews, commit its changes:
    ```
    IN worktree:
    git add <task's target_files>
    git commit -m "<task_id>: <task_action> — reviews passed"
    ```
    Record commit hash in `git_commit_map[task_id]` inside `~/.vega-punk/vega-punk-state.json`. This enables surgical rollback if a later task fails.

11. **Mark batch completion** — determine batch status:
    ```
    IF all tasks in batch passed reviews:
        Mark all tasks complete via TaskUpdate
        Append batch_id to completed_batches
        CLEAR batch_progress[batch_id]
    ELSE IF only non-critical tasks failed (all critical tasks passed):
        IF zero tasks passed (all non-critical failed):
            /* Empty batch serves no purpose — block and escalate */
            BLOCK batch
            ESCALATE: "All tasks in batch {batch_id} failed (non-critical). No value in proceeding."
            ASK user for direction
        ELSE:
            Mark passed tasks complete
            Mark failed tasks as failed
            Append batch_id to completed_batches
            APPEND batch_id to partial_batches
            LOG failures to ~/.vega-punk/progress.json
            CLEAR batch_progress[batch_id]
            /* WARNING: downstream tasks must NOT depend on failed tasks */
    ELSE:
        /* Critical task failed — do NOT proceed */
        BLOCK batch
        LOG to ~/.vega-punk/progress.json
        ESCALATE to user
    ```

12. **Invoke `verify-gate` via Skill tool** — confirm all tasks passed their reviews and verification checks before proceeding to the next batch.
    - **If verify-gate invocation fails** (tool error, not test failure):
        LOG: "verify-gate invocation failed: {error}"
        ASK user: "Cannot run verification. Proceed manually or fix the issue?"
    - **If verify-gate passes:** proceed to next batch.
    - **If verify-gate fails:** log failure to `~/.vega-punk/progress.json`. Attempt fix:
      1. Re-dispatch implementer for the failing task(s) with verify-gate output as context
      2. Re-run verify-gate (max 2 attempts)
      3. If still failing → mark task as failed, ESCALATE to user with full failure context
      4. Do NOT proceed to next batch until current batch passes verify-gate

### Step 4: Final Code Review

Invoke the `review-request` skill via Skill tool. Pass the full git range from first to last commit.

**If review-request invocation fails:**
- LOG the failure
- ASK user: "Final review invocation failed. Skip review or resolve the issue?"

### Step 5: Verify Before Landing

Invoke `verify-gate` via Skill tool one final time after review-request passes — ensures the full implementation is mechanically sound (tests pass, build clean, lint ok) before branch completion.

### Step 6: Complete Development

Invoke `branch-landing` via Skill tool.

## Rollback Strategy

When a task fails and needs to be undone, use the `git_commit_map` to surgically revert:

```
BEGIN ROLLBACK
    /* Single task rollback */
    IF git_commit_map[task_id] exists:
        git -C <worktree_path> revert <commit_hash> --no-edit
        LOG: "Rolled back task {task_id} (commit {commit_hash})"
    ELSE:
        /* Task was never committed — working directory has uncommitted changes */
        git -C <worktree_path> checkout -- <task's target_files>
        LOG: "Discarded uncommitted changes for task {task_id}"

    /* Full batch rollback (rare — use when multiple interdependent tasks failed) */
    IF entire batch needs rollback:
        Find last commit before this batch started
        git -C <worktree_path> reset --soft <commit_before_batch>
        /* --soft preserves changes as staged, allowing selective re-application */
        LOG: "Soft-reset batch {batch_id} to pre-batch state"
        ESCALATE to user for direction on re-approach
END
```

**When to rollback:**
- Critical task failed after all retries exhausted → rollback that task's commit
- Parallel dispatch created merge conflicts that can't be resolved → rollback the conflicting tasks
- User requests rollback explicitly

**When NOT to rollback:**
- Non-critical task failed (just skip it, proceed with successful tasks)
- Review found fixable issues (fix, don't rollback)

## Handling Implementer Status

```
BEGIN HANDLE_IMPLEMENTER_STATUS
    /* Track re-dispatch count per task */
    redispatch_count[task_id] = redispatch_count.get(task_id, 0) + 1

    CASE DONE:
        PROCEED to spec compliance review

    CASE DONE_WITH_CONCERNS:
        READ concerns before proceeding
        IF concerns about correctness or scope:
            ADDRESS before review
        IF concerns are observations (e.g., "this file is getting large"):
            NOTE and proceed to review

    CASE NEEDS_CONTEXT:
        IF redispatch_count >= 3:
            MARK task as FAILED
            LOG to progress.json: "exhausted re-dispatches for NEEDS_CONTEXT"
            CONTINUE with remaining tasks
        PROVIDE missing context
        RE-DISPATCH implementer

    CASE BLOCKED:
        IF redispatch_count >= 3:
            MARK task as FAILED
            LOG to progress.json: "exhausted re-dispatches for BLOCKED"
            CONTINUE with remaining tasks
        ASSESS blocker:
            IF context problem:
                PROVIDE more context → RE-DISPATCH
            IF task requires more reasoning:
                RE-DISPATCH with more capable model (model: "opus")
            IF task too large:
                BREAK into smaller pieces → create new TaskCreate entries
            IF plan itself wrong:
                MARK task as failed
                LOG to ~/.vega-punk/progress.json
                CONTINUE with remaining tasks — do NOT block entire pipeline

    CASE IMPLEMENTER_TIMEOUT:
        IF redispatch_count >= 3:
            MARK task as FAILED
            LOG to progress.json: "exhausted re-dispatches for timeout"
            CONTINUE with remaining tasks
        TREAT as BLOCKED with details "implementer did not return within expected time"
        FOLLOW BLOCKED handling path
        ON re-dispatch: consider using more capable model or smaller scope

    CASE MISSING_STATUS_FILE:
        IF redispatch_count >= 3:
            MARK task as FAILED
            LOG to progress.json: "exhausted re-dispatches for missing status file"
            CONTINUE with remaining tasks
        TREAT as BLOCKED with details "Implementer did not write status file"
        CHECK subagent output for clues about what happened
        IF subagent produced output but forgot status file:
            ATTEMPT to assess completion from output → RE-DISPATCH if uncertain
        IF subagent produced no output:
            RE-DISPATCH with clearer instructions about status file requirement
END
```

## Model Selection

```
BEGIN MODEL_SELECTION
    CASE implementer (mechanical, 1-2 files, clear spec):
        USE model: "haiku"
    CASE implementer (integration, multi-file):
        USE model: "sonnet"
    CASE reviewer (spec compliance):
        USE model: "sonnet"
    CASE reviewer (code quality):
        USE model: "sonnet"
    CASE final review / escalation:
        USE model: "opus"
END
```

## Prompt Templates

Build each prompt inline. Do NOT reference external template files — construct the full prompt in your dispatch call.

### Implementer Prompt

```
## Task: <task_id> - <task_action>

## Context
- Project: <project_name>
- Branch: <branch_name>
- Worktree: <worktree_path>

## What to do
<full step description from ~/.vega-punk/roadmap.json — pasted verbatim, NOT a file reference>

## Code to write
<exact code block from ~/.vega-punk/roadmap.json code field — pasted verbatim>

## Constraints
- Write ONLY the files specified below. Do NOT modify other files.
- Verify your work by running the relevant tests before reporting done.
- Report the actual test output (command, exit code, pass/fail counts) — not "tests should pass".
- If the code field is empty or unclear, report BLOCKED with what's missing.

## Discipline (apply based on your task type)

If this task is a bug fix, crash, or error:
1. Read error messages carefully before changing anything
2. Reproduce the issue consistently
3. Check recent changes (git diff) for what might have caused this
4. Form a single hypothesis, test minimally
5. Write a failing test that reproduces the bug
6. Fix the root cause, not the symptom
7. Verify test passes

If this task is a new feature, behavior change, or refactoring:
1. Write the failing test first (RED)
2. Verify it fails for the expected reason
3. Write minimal code to pass (GREEN)
4. Verify all tests pass
5. Refactor only if needed, keep tests green
6. Never add features no test requires

## Files to create/modify
<list target files from the step's target_files field>

## Report
When done, write your status to `.task-status-<task_id>.json` in the worktree root:
```json
{ "status": "DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED", "details": "<message>" }
```
The controller reads this file. Do NOT leave it empty.
If DONE_WITH_CONCERNS, list specific concerns.
If BLOCKED, explain what's preventing completion.
IMPORTANT: You MUST write this file even if you encounter an error — write { "status": "BLOCKED", "details": "..." } instead of skipping it.
```

### Spec Reviewer Prompt

```
## Review: Spec Compliance for Task <task_id>

## The Spec
<paste the relevant requirements from roadmap.json verbatim — do NOT reference the file path>

## What was built — full diff
<paste the FULL git diff output verbatim — do NOT summarize>

## Changed files for reference
<list of file paths from git diff>

## Task
Compare what was built against what the spec requires.
Check every requirement has a corresponding implementation.
For each requirement, verify it in the actual code (not just the diff summary).
Read the actual source files in the worktree if you need more context beyond the diff.
Report: PASS (with evidence: which lines satisfy which requirements) or FAIL (with specific gaps: spec says X, built Y, missing at file:line).
```

### Code Quality Reviewer Prompt

```
## Review: Code Quality for Task <task_id>

## Context
- Project: <project_name>
- Worktree: <worktree_path>
- Files changed: <list from git diff>

## Full diff
<paste the FULL git diff output verbatim>

## Task
Review the implementation for:
1. Correctness: logic bugs, edge cases, error handling
2. Readability: naming, structure, comments where non-obvious
3. Consistency: matches existing codebase patterns
4. Performance: no O(n^2) on unbounded data, no N+1 queries
5. Safety: no injection vulnerabilities, no unvalidated external input

Read the actual source files in the worktree for full context beyond the diff.
Report: PASS or FAIL (with specific file:line issues).
Mark severity: Critical / Important / Minor.
```

### Fix Dispatch Prompt (re-dispatch implementer to fix review issues)

```
## Fix Task: <task_id> - Review Issues

## Context
- You previously implemented this task. A reviewer found issues.
- Project: <project_name>
- Branch: <branch_name>
- Worktree: <worktree_path>

## The original spec (re-stated for reference — do NOT break spec compliance while fixing)
<paste the relevant requirements from roadmap.json verbatim>

## Review findings
<paste reviewer's FAIL report verbatim>

## Your previous implementation
<summary of what you built, from git diff>

## Discipline (apply based on your task type — same as initial dispatch)

If the original task was a bug fix, crash, or error:
1. Reproduce the issue the reviewer found before changing anything
2. Write a test that demonstrates the issue
3. Fix the root cause
4. Verify the test passes and original tests still pass

If the original task was a new feature, behavior change, or refactoring:
1. Write a failing test that demonstrates the review issue
2. Fix the code to pass the test
3. Verify all existing tests still pass
4. Do NOT add changes beyond what the review requires

## What to do
Fix ALL issues listed in the review findings. Do NOT introduce new changes beyond what the review requires.
While fixing, verify you do NOT break any spec requirement listed in the original spec above.

## Files to modify
<list target files from the step's target_files field>

## Report
When done, write your status to `.task-status-<task_id>.json` in the worktree root:
```json
{ "status": "DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED", "details": "<message>" }
```
IMPORTANT: You MUST write this file even if you encounter an error.
```

## Review Error Recovery

```
BEGIN REVIEW_RECOVERY
    /* Spec compliance review — max 3 cycles */
    FOR cycle 1 to 3:
        IF reviewer passes:
            BREAK → proceed to code quality review
        IF cycle <= 2:
            RE-DISPATCH implementer with Fix Dispatch Prompt → wait for fix → RE-REVIEW
        IF cycle == 3:
            /* Spec itself may be ambiguous — escalate */
            ESCALATE: "spec says X, implementer built Y, who's right?"
            IF user resolves → apply resolution, proceed
            IF user unavailable → mark task as failed, log to progress.json, continue

    /* Code quality review — max 2 cycles */
    FOR cycle 1 to 2:
        IF reviewer passes:
            BREAK → task complete
        IF cycle == 1:
            RE-DISPATCH implementer with Fix Dispatch Prompt → wait for fix → RE-REVIEW
        IF cycle == 2:
            /* Implementer misunderstanding pattern — escalate */
            ESCALATE with conflicting perspectives
            IF user resolves → apply resolution, proceed
            IF user unavailable → mark task as failed, log to progress.json, continue

    /* If all retries exhausted */
    MARK task as failed
    LOG to ~/.vega-punk/progress.json: { timestamp, step_id, error: "review cycles exhausted" }
    IF task is critical:
        STOP and ask user for direction
    ELSE:
        CONTINUE with remaining tasks
END
```

## progress.json Schema

File location: `~/.vega-punk/progress.json`

```json
{
  "max_entries": 100,
  "entries": [
    {
      "timestamp": "2026-04-13T10:30:00Z",
      "step_id": "1_2",
      "event": "task_failed",
      "error": "review cycles exhausted: spec says X, implementer built Y",
      "resolution": "skipped_non_critical"
    }
  ]
}
```

- Created on first write, appended to on subsequent events
- `event` values: `task_failed`, `task_blocked`, `batch_verify_failed`, `escalation`, `rollback`
- `resolution` values: `skipped_non_critical`, `escalated_to_user`, `user_resolved`, `retried`, `rolled_back`
- Controller reads this at session resume to understand past failures
- **Maintenance:** When `entries` exceeds `max_entries` (100), remove oldest entries to maintain the limit

## batch_progress Schema

Stored inside `~/.vega-punk/vega-punk-state.json` under key `batch_progress`. Enables fine-grained session resume — when a session crashes mid-batch, the next session can continue from the exact stage rather than re-dispatching already-completed tasks.

```json
{
  "batch_progress": {
    "1": {
      "stage": "implementing|spec_review_done|code_quality_review_done",
      "tasks_done": ["1_1", "1_2"],
      "tasks_failed": [],
      "tasks_committed": ["1_1"]
    }
  }
}
```

- `stage` values: `"implementing"`, `"spec_review_done"`, `"code_quality_review_done"`
- `tasks_committed`: task IDs whose changes have been git-committed (for rollback targeting)
- On session resume: read `batch_progress[batch_id]`, GOTO the stage, skip already-done tasks
- Cleared when batch completes (all tasks pass or batch is marked partial/failed)

## git_commit_map Schema

Stored inside `~/.vega-punk/vega-punk-state.json` under key `git_commit_map`. Maps task IDs to their commit hashes for surgical rollback.

```json
{
  "git_commit_map": {
    "1_1": "abc1234",
    "1_2": "def5678"
  }
}
```

- Written when a task's changes are committed (Step 3.10)
- Used by Rollback Strategy to revert specific tasks without affecting others

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Task complete | Status file: DONE + spec review PASS + quality review PASS + git committed | Implementer reports "done" |
| Batch complete | All tasks pass reviews + verify-gate PASS | All tasks dispatched |
| Spec compliant | Reviewer PASS with evidence (which lines satisfy which requirements) | Implementer says "matches spec" |
| Ready to land | Final review PASS + final verify-gate PASS | All batches complete |
| Parallel safe | target_files disjoint + no implicit conflicts + post-merge check | target_files disjoint alone |
| Session resumable | batch_progress written after each stage + git commits preserved | completed_batches alone |
| Rollback possible | git_commit_map populated + commits per task | Single monolithic commit |

## Red Flags

### Hard Blocks (violate = STOP immediately)
- Starting implementation on main/master branch without explicit user consent
- Skipping reviews (spec compliance OR code quality)
- Starting code quality review before spec compliance is PASS
- Proceeding to next batch while any task in current batch has open review issues
- Skipping verify-gate after each batch
- Proceeding to next batch if verify-gate fails
- Dispatching dependent tasks in parallel (violates depends_on ordering)
- Proceeding when all tasks in a batch failed (even if non-critical)

### Quality Risks (may cause incorrect results)
- Letting implementer self-review replace actual review (both are needed)
- Accepting "close enough" on spec compliance (reviewer found issues = not done)
- Skipping review loops (reviewer found issues = implementer fixes = review again)
- Fix Dispatch without discipline injection (same rigor as initial dispatch)
- Fix Dispatch without original spec (may fix review but break spec compliance)
- Parallel dispatch with only target_files check (implicit conflicts: shared imports, config, module-level changes)
- Skipping git commit per task (no rollback capability if later task fails)

### Efficiency Traps (not fatal but waste resources)
- Making subagent read plan file (provide full text instead — paste verbatim)
- Skipping scene-setting context (subagent needs to understand where task fits)
- Re-dispatching completed tasks on session resume (use batch_progress instead)
- Ignoring subagent questions (answer before letting them proceed)
- Infinite re-dispatch loops (enforce max 2 re-dispatches per task)

## Integration

**Required skills — auto-invoked via Skill tool:**
- `worktree-setup` — invoke in Pre-Execution Gate before dispatching any tasks
- `root-cause` — inject discipline into implementer prompts for bug fix tasks
- `test-first` — inject discipline into implementer prompts for feature/refactor tasks
- `parallel-swarm` — decision skill for parallelism evaluation (Step 3); provides independence check and prompt construction principles, not dispatch mechanics
- `verify-gate` — invoke at Step 3.12 after each batch passes reviews, and at Step 5 before landing
- `review-request` — invoke at Step 4 for final code review
- `branch-landing` — invoke at Step 6 after all tasks complete
- `plan-builder` — upstream; creates the `~/.vega-punk/roadmap.json` this skill executes

**Skill invocation failure handling:**
- worktree-setup fails → STOP, ask user (no worktree = no work)
- verify-gate fails (tool error) → LOG, ask user how to proceed
- review-request fails (tool error) → LOG, ask user whether to skip or resolve
- branch-landing fails (tool error) → LOG, ask user — do NOT push/merge without landing procedure

**Auto-invocation rule:** All skills are invoked via the `Skill` tool — trigger phrases are deprecated and should not be used.

**Subagents should use:**
- test-first approach for each task

**Alternative execution path:**
- `plan-executor` — use for inline sequential execution instead of subagent dispatch

**Session resume:**
- On session restart, read `~/.vega-punk/vega-punk-state.json` for `batch_plan`, `completed_batches`, `batch_progress`, and `git_commit_map`
- Resume from the first incomplete batch
- If `batch_progress[batch_id]` exists, resume from the recorded stage, skip already-done tasks
- Validate worktree consistency: commit any uncommitted partial work before resuming
- Read `~/.vega-punk/progress.json` for past failures to avoid repeating them

## Example Workflow

```
You: [Pre-Execution Gate: validate roadmap, invoke worktree-setup, record baseline_failure_count]
[worktree created, baseline tests pass]

You: [Read ~/.vega-punk/roadmap.json → build dependency graph → topological sort into batches]
[Store batch_plan to ~/.vega-punk/vega-punk-state.json with batch_progress: {}, git_commit_map: {}]
[Create TaskCreate entries for each task, set addBlockedBy from depends_on]

For each batch in batch_plan:
  1. Verify completed_batches contains all prior batch_ids (enables session resume)
  2. Check batch_progress for partial completion — resume from stage if exists
     Validate worktree consistency: commit uncommitted partial work
  3. Classify each task: bug fix → root-cause discipline, feature/refactor → test-first
  4. Dispatch implementers: parallel (multiple Agent calls in one message) or sequential
     WARN on parallel: "watch for implicit conflicts"
     Check for merge conflicts after parallel implementers complete
  5. Wait for all, read .task-status-*.json from worktree root (fallback: treat missing as BLOCKED)
     Handle timeout: treat as BLOCKED if implementer hangs
     Enforce re-dispatch limit: max 2 re-dispatches (3 total attempts)
  6. Handle status (DONE → review, NEEDS_CONTEXT → re-dispatch, BLOCKED → assess, MISSING → re-dispatch)
  7. Dispatch spec reviewers (with FULL git diff, not summaries) → if FAIL: re-dispatch implementer with Fix Prompt (includes original spec + discipline) → re-review (max 3 cycles)
     Record: batch_progress[batch_id].stage = "spec_review_done"
  8. Dispatch code quality reviewers (with FULL git diff + file access) → if FAIL: re-dispatch implementer with Fix Prompt (includes original spec + discipline) → re-review (max 2 cycles)
     Record: batch_progress[batch_id].stage = "code_quality_review_done"
  9. Git commit per task: commit target_files, record hash in git_commit_map
  10. Determine batch completion: all pass → complete; non-critical fail → partial (unless ALL failed); critical fail → block
      Clear batch_progress[batch_id] on batch completion
  11. Invoke verify-gate via Skill tool → if FAIL: fix and retry (max 2), then escalate
  12. Next batch

After all tasks:
  You: [Invoke review-request via Skill tool]
  You: [Invoke verify-gate via Skill tool — final mechanical check]
  You: [Invoke branch-landing via Skill tool]
```
