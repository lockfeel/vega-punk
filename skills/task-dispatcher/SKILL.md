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

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: ~/.vega-punk/roadmap.json */
    IF ~/.vega-punk/roadmap.json does NOT exist:
        IF ~/.vega-punk/vega-punk-state.json exists:
            state_dir = directory of ~/.vega-punk/vega-punk-state.json
            IF state_dir/roadmap.json exists:
                USE state_dir/roadmap.json
            ELSE:
                FAIL: "[task-dispatcher] ~/.vega-punk/roadmap.json not found. Run plan-builder first."
                EXIT
        ELSE:
            FAIL: "[task-dispatcher] No ~/.vega-punk/roadmap.json and no state file. Nothing to execute."
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

    /* Check if worktree is needed */
    IF ~/.vega-punk/vega-punk-state.json exists:
        IF worktree_path field missing:
            TELL: "[task-dispatcher] No worktree found. Invoking worktree-setup."
            INVOKE worktree-setup via Skill tool
        ELSE IF worktree_path directory does NOT exist:
            TELL: "[task-dispatcher] Worktree at {worktree_path} missing. Recreating."
            INVOKE worktree-setup via Skill tool

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

**vs. plan-executor:**
- task-dispatcher: subagent per task, two-stage review, faster iteration
- plan-executor: inline execution, simpler, fewer API calls

## The Process

### Step 0: Setup Workspace

Invoke `worktree-setup` via Skill tool.

- If worktree-setup reports failing baseline tests → stop and ask user before proceeding (same as plan-executor Step 1.6)
- Record the baseline failure count so downstream verify-gate can distinguish new vs pre-existing failures

### Step 1: Read Plan

Read `~/.vega-punk/roadmap.json` — extract all phases and steps with full context. Build a task dependency graph from `depends_on` fields.

### Step 2: Create Task Tracker

Create a TodoWrite entry per phase/task from the plan. Track status: `pending` → `dispatched` → `reviewing` → `complete`.

### Step 3: Dispatch Tasks (respects `depends_on`, dispatches independent tasks in parallel)

For each batch of tasks that have all dependencies satisfied:

1. **Check dependencies:** Only dispatch tasks whose `depends_on` steps are all `"complete"`.
2. **Classify each task type** before dispatching:
   - If task involves **bug fix, crash, error, or unexpected behavior** → include `root-cause` skill instructions in the implementer prompt
   - If task involves **new feature, behavior change, or refactoring** → include `test-first` skill instructions (RED-GREEN-REFACTOR) in the implementer prompt
3. **Evaluate parallelism strategy:**
   - IF current batch has ≥ 2 tasks AND all tasks have ZERO mutual depends_on AND tasks target disjoint file sets → invoke `parallel-swarm` via Skill tool for this batch
   - ELSE → dispatch implementer subagents directly in parallel (normal path)
4. **Dispatch implementer subagents in parallel** for all tasks in this batch (use `run_in_background: true` or your platform's equivalent). Each subagent gets its own task-specific prompt (see Prompt Templates below).
5. **Collect implementer results** — wait for all implementers to finish. Read each `.task-status-<task_id>.json` from the **worktree root** (use `worktree_path` from `~/.vega-punk/vega-punk-state.json`). **Handle implementer status** (see Handling Implementer Status) — fix or re-dispatch as needed.
6. **Dispatch spec reviewer subagents in parallel** — fix issues → re-review until ✅ (max 3 cycles).
7. **Dispatch code quality reviewer subagents in parallel** — fix issues → re-review until ✅ (max 2 cycles).
8. **Mark all tasks in batch complete**
9. **Invoke `verify-gate` via Skill tool** — confirm all tasks passed their reviews and verification checks before proceeding to the next batch.

### Step 4: Final Code Review

Invoke the `review-request` skill via Skill tool. Pass the full git range from first to last commit.

### Step 5: Verify Before Landing

Invoke `verify-gate` via Skill tool one final time after review-request passes — ensures the full implementation is mechanically sound (tests pass, build clean, lint ok) before branch completion.

### Step 6: Complete Development

Invoke `branch-landing` via Skill tool.

## Handling Implementer Status

Implementer subagents report one of four statuses. Handle each appropriately:

**DONE:** Proceed to spec compliance review.

**DONE_WITH_CONCERNS:** The implementer completed the work but flagged doubts. Read the concerns before proceeding. If the concerns are about correctness or scope, address them before review. If they're observations (e.g., "this file is getting large"), note them and proceed to review.

**NEEDS_CONTEXT:** The implementer needs information that wasn't provided. Provide the missing context and re-dispatch.

**BLOCKED:** The implementer cannot complete the task. Assess the blocker:
1. If it's a context problem, provide more context and re-dispatch
2. If the task requires more reasoning, re-dispatch with a more capable model
3. If the task is too large, break it into smaller pieces
4. If the plan itself is wrong, **mark the task as failed, log to ~/.vega-punk/progress.json, and continue with remaining tasks** — do not block the entire pipeline on one broken task

## Model Selection

Use the least capable model that can handle each role:

| Role | Claude Code | OpenClaw / Generic | Signal |
|------|-------------|--------------------|--------|
| Implementer (mechanical, 1-2 files, clear spec) | haiku | fast model | "write this exact function" |
| Implementer (integration, multi-file) | sonnet | standard model | "wire up X to Y" |
| Reviewer (spec compliance) | sonnet | standard model | "verify against spec" |
| Reviewer (code quality) | sonnet | standard model | "review for patterns/best practices" |
| Final review / escalation | opus | most capable model | "review entire implementation" |

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
<full step description from ~/.vega-punk/roadmap.json>

## Code to write
<exact code block from ~/.vega-punk/roadmap.json code field>

## Constraints
- Write ONLY the files specified below. Do NOT modify other files.
- Verify your work by running the relevant tests before reporting done.
- If the code field is empty or unclear, report BLOCKED with what's missing.

## Discipline (applies based on task type)
CASE task is bug fix / crash / error:
    1. Read error messages carefully before changing anything
    2. Reproduce the issue consistently
    3. Check recent changes (git diff) for what might have caused this
    4. Form a single hypothesis, test minimally
    5. Write a failing test that reproduces the bug
    6. Fix the root cause, not the symptom
    7. Verify test passes

CASE task is new feature / behavior change / refactoring:
    1. Write the failing test first (RED)
    2. Verify it fails for the expected reason
    3. Write minimal code to pass (GREEN)
    4. Verify all tests pass
    5. Refactor only if needed, keep tests green
    6. Never add features no test requires

## Files to create/modify
<list target files from the step>

## Report
When done, write your status to `.task-status-<task_id>.json` in the worktree root:
```json
{ "status": "DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED", "details": "<message>" }
```
The controller reads this file. Do NOT leave it empty.
If DONE_WITH_CONCERNS, list specific concerns.
If BLOCKED, explain what's preventing completion.
```

### Spec Reviewer Prompt

```
## Review: Spec Compliance for Task <task_id>

## The Spec
<relevant requirements from ~/.vega-punk/roadmap.json or spec file>

## What was built
<summary of changes from git diff or implementer report>

## Task
Compare what was built against what the spec requires.
Check every requirement has a corresponding implementation.
Report: PASS (with evidence) or FAIL (with specific gaps: spec says X, built Y).
```

### Code Quality Reviewer Prompt

```
## Review: Code Quality for Task <task_id>

## Context
- Project: <project_name>
- Files changed: <list from git diff>

## Task
Review the implementation for:
1. Correctness: logic bugs, edge cases, error handling
2. Readability: naming, structure, comments where non-obvious
3. Consistency: matches existing codebase patterns
4. Performance: no O(n²) on unbounded data, no N+1 queries

Report: PASS or FAIL (with specific file:line issues).
Mark severity: Critical / Important / Minor.
```

## Review Error Recovery

**Spec compliance review — max 3 cycles:**
- Cycle 1-2: Implementer fixes, reviewer re-reviews
- Cycle 3: If still failing, the spec itself may be ambiguous. Escalate with specific discrepancy (spec says X, implementer built Y, who's right?)

**Code quality review — max 2 cycles:**
- Cycle 1: Implementer fixes, reviewer re-reviews
- Cycle 2: If reviewer still finds Important/Critical issues, implementer may be misunderstanding the pattern. Escalate with conflicting perspectives.

**If reviewer is wrong:** Implementer should push back with technical reasoning (file:line evidence, test results, spec quotes). The controller (you) makes the final call — don't let the review loop indefinitely.

**If all retries exhausted on a task:**
- Mark the task as `failed`
- Log to `~/.vega-punk/progress.json` (same directory as `~/.vega-punk/roadmap.json` and `~/.vega-punk/vega-punk-state.json`): `{ "timestamp": "<ISO8601>", "step_id": "<id>", "error": "review cycles exhausted: <summary>" }`
- If task is `critical: false` → continue with remaining tasks
- If task is `critical: true` → stop and ask user for direction

## Example Workflow

```
You: [Invoke worktree-setup via Skill tool]
[worktree created, baseline tests pass]

You: [Invoke task-dispatcher flow — subagent-driven development]
[Extract all tasks from ~/.vega-punk/roadmap.json → Create TodoWrite entries]
[Build dependency graph from depends_on fields]

For each batch of tasks with all dependencies satisfied:
  1. Classify each task: bug fix → root-cause discipline, feature/refactor → test-first (RED-GREEN-REFACTOR)
  2. Dispatch implementers in parallel (haiku/sonnet, full task text + context + discipline)
  3. Wait for all, handle status (DONE → review, NEEDS_CONTEXT → re-dispatch, BLOCKED → assess)
  4. Dispatch spec reviewers in parallel (sonnet) → fix → re-review until ✅
  5. Dispatch code quality reviewers in parallel (sonnet) → fix → re-review until ✅
  6. Invoke verify-gate via Skill tool.
  7. Mark batch complete → next batch

After all tasks:
  You: [Invoke review-request via Skill tool]
  You: [Invoke verify-gate via Skill tool — final mechanical check]
  You: [Invoke branch-landing via Skill tool]
```

## Advantages

**vs. Manual execution:**
- Subagents follow TDD naturally
- Fresh context per task (no confusion)
- Parallel-safe (subagents don't interfere)
- Subagent can ask questions (before AND during work)

**vs. plan-executor:**
- Same session (no handoff)
- Continuous progress (no waiting)
- Review checkpoints automatic

**Efficiency gains:**
- No file reading overhead (controller provides full text)
- Controller curates exactly what context is needed
- Subagent gets complete information upfront
- Questions surfaced before work begins (not after)

**Quality gates:**
- Self-review catches issues before handoff
- Two-stage review: spec compliance, then code quality
- Review loops ensure fixes actually work
- Spec compliance prevents over/under-building
- Code quality ensures implementation is well-built

## Red Flags

**Never:**
- Start implementation on main/master branch without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel **within the same task** (conflicts on shared files)
- Dispatch dependent tasks in parallel — always respect `depends_on` ordering; only parallelize tasks with no mutual dependencies
- Make subagent read plan file (provide full text instead)
- Skip scene-setting context (subagent needs to understand where task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance (spec reviewer found issues = not done)
- Skip review loops (reviewer found issues = implementer fixes = review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is ✅** (wrong order)
- Move to next batch while any task in current batch has open review issues
- Skip the verify-gate after each batch

**If subagent asks questions:**
- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

**If reviewer finds issues:**
- Implementer (same subagent) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

**If subagent fails task after all retries:**
- Mark task as failed, log to ~/.vega-punk/progress.json
- Continue with remaining tasks if non-critical
- Escalate to user if critical task failed

## Integration

**Required skills — auto-invoked via Skill tool:**
- `worktree-setup` — invoke at Step 0 before dispatching any tasks
- `root-cause` — inject discipline into implementer prompts for bug fix tasks
- `test-first` — inject discipline into implementer prompts for feature/refactor tasks
- `parallel-swarm` — invoke at Step 3 when batch has ≥ 2 fully independent tasks with disjoint file targets
- `verify-gate` — invoke at Step 3.9 after each batch passes reviews, and at Step 5 before landing
- `review-request` — invoke at Step 4 for final code review
- `branch-landing` — invoke at Step 6 after all tasks complete
- `plan-builder` — upstream; creates the `~/.vega-punk/roadmap.json` this skill executes

**Auto-invocation rule:** All skills are invoked via the `Skill` tool — trigger phrases are deprecated and should not be used.

**Subagents should use:**
- test-first approach for each task

**Alternative execution path:**
- `plan-executor` — use for inline sequential execution instead of subagent dispatch
