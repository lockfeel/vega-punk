---
name: executing-plans
description: Use when you have a written implementation plan (roadmap.json) to execute in the current session with review checkpoints
user-invocable: true
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep"
hooks:
  SessionStart:
    - type: command
      command: "bash scripts/planning-resume.sh"
metadata:
  version: "9.0"
---

# Executing Plans

## Entry Protocol

This skill is invoked from the planning-with-json sub-skill's Execution Handoff section.
The `roadmap.json` in the working directory is the **single source of truth** for all tasks.

```
1. Read roadmap.json
2. Check .vega-punk-state.json (if exists) for execution context
3. Resume from current_step if previously interrupted
```

## Quick Reference

```
A. Load & Review:
   - Read roadmap.json, review plan structure critically
   - If concerns → raise with user before starting

B. Execute Loop:
   - Mark step in_progress → Execute tool/target → Verify → Mark complete
   - Write roadmap.json back after each step

C. On Completion:
   - If vega-punk mode → write execution_result to .vega-punk-state.json
   - If standalone → deliver summary + invoke finishing-a-development-branch
```

## The Process

### Step 1: Load and Review Plan

1. Read `roadmap.json`
2. Review the plan structure:
   - `project` / `goal` / `architecture` — understand what we're building
   - `phases[].steps[]` — each step has `action`, `tool`, `target`, `code`, `verify`
   - `current_step` — resume from here if previously interrupted
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Proceed to Step 2

### Step 2: Execute Steps

For each step in `roadmap.json`:

1. Mark the step's `status` as `"in_progress"`
2. Execute the step using the specified `tool` and `target`
   - If `code` field is present, write/edit the exact code as specified
   - If `verify` field is present, run the verification after execution
3. **On verification pass:** Set `status` to `"complete"`, set `result` to a brief outcome summary
4. **On verification fail:** Increment `attempts`. If attempts < 3, retry with different approach. If attempts >= 3, set `status` to `"failed"` and stop.
5. Update `current_step` to the next pending step's id
6. Update `metadata.completed_steps` and `metadata.completion_rate`
7. Write `roadmap.json` back after each step

### Step 3: Complete Development

After all steps complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly (attempts >= 3)

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Read `roadmap.json` first — it is the single source of truth
- Follow each step's `tool`, `target`, and `code` exactly
- Don't skip verifications specified in `verify` field
- Update `roadmap.json` after every step
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Completion Contract — State Write-Back

After execution completes and verification passes (or after finishing-a-development-branch completes):

**If invoked from vega-punk** (`.vega-punk-state.json` exists):

```
1. Read .vega-punk-state.json
2. Update state to "REVIEW"
3. Add execution_result:
   {
     "status": "success|partial|failed",
     "summary": "<brief outcome>",
     "artifacts": ["path/to/file1", "path/to/file2"],
     "verification": "passed|failed",
     "notes": "<any issues or observations>"
   }
4. Write .vega-punk-state.json back
5. This triggers vega-punk's REVIEW state automatically
```

**If standalone mode** (no `.vega-punk-state.json`):
- No state write-back needed. Deliver summary to user directly.

**If execution fails** (attempts exhausted on critical steps):
- If vega-punk mode: update `.vega-punk-state.json` with status "failed" and error details in notes
- If standalone: present failure report with specific step(s) that failed and suggested fixes

## Integration

**Required workflow skills:**
- **using-git-worktrees** — REQUIRED: Set up isolated workspace before starting
- **vega-punk** — Creates the design that leads to planning-with-json
- **planning-with-json** — Creates the `roadmap.json` this skill executes
- **finishing-a-development-branch** — Complete development after all tasks
