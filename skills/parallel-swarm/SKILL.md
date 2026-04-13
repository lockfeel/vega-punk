---
name: parallel-swarm
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
categories: ["workflow"]
triggers: ["parallel", "independent tasks", "multiple failures", "different root causes", "dispatch agents", "should these run in parallel"]
---

# Dispatching Parallel Agents

## Overview

You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

**Role:** parallel-swarm is the decision skill for parallelization. It answers: "Should these tasks run in parallel?" and "How do I structure their prompts?" The caller (task-dispatcher or manual workflow) owns dispatch table management, subagent lifecycle, and result collection.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Unified Evaluation Pipeline

Gate and decision logic are unified into a single pipeline. Earlier stages fail fast; later stages add nuance. No logic is duplicated.

```
BEGIN PARALLEL_EVALUATION
    /* ── Stage 1: Quick Fail-Fast ── */

    IF fewer than 2 tasks identified:
        FAIL: "[parallel-swarm] Only 1 task identified. Use sequential dispatch instead."

    /* ── Stage 2: Independence Verification ── */

    FOR EACH pair of tasks (A, B):
        /* File-level overlap */
        IF A.target_files ∩ B.target_files ≠ ∅:
            FAIL: "[parallel-swarm] Tasks {A} and {B} target same files. Use sequential."

        /* Output dependency */
        IF A depends on B's output:
            FAIL: "[parallel-swarm] Task {A} depends on {B}. Use sequential dispatch."

        /* Shared mutable state */
        IF A and B share mutable state (DB, config, env):
            FAIL: "[parallel-swarm] Tasks {A} and {B} share mutable state. Use sequential."

        /* Logical conflict detection */
        IF A modifies interface/contract that B consumes:
            FAIL: "[parallel-swarm] Tasks {A} and {B} have logical dependency (interface/consumer). Use sequential."
        IF A and B modify different files but same conceptual entity (e.g., env var name, DB schema, API contract):
            FAIL: "[parallel-swarm] Tasks {A} and {B} may conflict on shared concept: {entity}. Use sequential."

    /* ── Stage 3: Context Sufficiency ── */

    FOR EACH task:
        IF task has no specific target (file, function, test):
            FAIL: "[parallel-swarm] Task {task} has no specific target. Cannot dispatch."
        IF task has no expected output:
            ADD expected output: "Make these tests pass / Fix this behavior"
        IF task has no success criteria:
            ADD success criteria: "All targeted tests pass / Specific behavior verified"

    /* ── Stage 4: Agent Count Gate ── */

    agent_count = number of tasks passing Stages 1-3

    IF agent_count > 8:
        FAIL: "[parallel-swarm] {agent_count} agents is excessive. Re-evaluate task granularity — likely over-decomposed."
    IF agent_count > 5:
        WARN: "[parallel-swarm] {agent_count} agents — coordination cost may exceed parallel benefit. Consider merging related tasks."

    /* ── Stage 5: Isolation Strategy ── */

    RECOMMEND isolation_mode = "worktree"
    /* Rationale: Even with disjoint files, agents sharing a working directory
       can interfere via git state, build caches, lock files, or env changes.
       worktree isolation is the safe default. Override only when:
       - Tasks are read-only (no file modifications)
       - Platform does not support worktrees */

    /* ── Decision ── */

    IF all stages passed:
        EXIT as "parallel"
        RETURN: {
            strategy: "parallel_swarm",
            isolation: isolation_mode,
            agent_count: agent_count,
            post_merge_verification: REQUIRED
        }
    ELSE:
        EXIT as "sequential"
        RETURN: { strategy: "sequential" }
END
```

## When to Use

**Decision tree:**

```
Multiple failures or independent tasks?
├── No → Sequential execution (don't use parallel-swarm)
└── Yes
    └── Are they independent? (disjoint files, no shared state, no logical conflicts)
        ├── No, related → Single agent investigates all
        └── Yes
            └── Can they run without interfering?
                ├── No, shared resources or logical conflicts → Sequential agents
                └── Yes
                    └── Agent count reasonable (≤ 8)?
                        ├── No → Re-bundle tasks, reduce count
                        └── Yes → Parallel dispatch (this skill)
```

**Use when:**
- 2+ independent tasks that can run without shared state
- Different test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other
- Tasks share an interface/contract (logical dependency)

## Dispatch Table (Caller-managed)

The calling skill owns the dispatch table. The schema below defines **required fields** (marked `[R]`) and **recommended fields** (marked `[O]`). Callers may add extension fields but must not omit required fields.

```json
{
  "dispatch_table": [
    {
      "task_id": "[R] Unique identifier within this dispatch batch",
      "scope": "[R] Human-readable description of task scope",
      "target_files": "[R] List of files the agent will modify",
      "read_only_files": "[O] List of files the agent will read for context",
      "goal": "[R] What the agent must accomplish",
      "success_criteria": "[R] Observable condition that proves completion",
      "constraints": "[R] What the agent must NOT do",
      "isolation": "[R] Isolation mode (worktree | shared_dir | read_only)",
      "timeout_budget": "[O] { wall_clock: '10m', max_retries: 3 }",
      "status": "dispatched|complete|failed|partial|timeout",
      "agent_ref": "[R] Platform-native agent identifier for lifecycle tracking"
    }
  ]
}
```

## Agent Lifecycle

Each dispatched agent follows a lifecycle managed by the caller:

```
DISPATCHED → (running) → COMPLETE | FAILED | PARTIAL | TIMEOUT
                                           ↓         ↓        ↓
                                    integrate   assess    diagnose
                                    changes     safety    + retry/
                                                partial   rollback
                                                fixes
```

| Status | Meaning | Caller Action |
|--------|---------|---------------|
| `COMPLETE` | All tasks in scope pass, summary returned | Integrate changes |
| `FAILED` | Agent couldn't fix the issue | Diagnose manually or mark for later |
| `PARTIAL` | Some but not all tasks pass | Assess if partial fix is safe to merge |
| `TIMEOUT` | Agent exceeded time budget | Check intermediate output; retry with more context or handle manually |
| `NEEDS_CONTEXT` | Agent lacked information to proceed | Re-dispatch with missing context |

**Handling stuck/timeout agents:**
1. Check intermediate output for progress signals
2. If making progress → extend timeout once (max 2 extensions)
3. If spinning (no meaningful diff for 3+ iterations) → terminate
4. On termination: evaluate partial changes for safety before deciding keep/rollback

## Rollback Protocol

When parallel dispatch produces mixed results, follow this protocol:

```
BEGIN ROLLBACK_DECISION
    count_complete = number of agents with status COMPLETE
    count_failed   = number of agents with status FAILED|TIMEOUT
    count_partial  = number of agents with status PARTIAL

    /* All succeeded → proceed to post-merge verification */
    IF count_failed == 0 AND count_partial == 0:
        PROCEED to post_merge_verification

    /* All failed → rollback all */
    IF count_complete == 0:
        ROLLBACK all changes
        EXIT: "All agents failed. Rollback complete. Investigate sequentially."

    /* Mixed results → assess each independently */
    FOR EACH agent:
        IF status == COMPLETE:
            MARK changes as "candidate for keep"
        IF status == PARTIAL:
            IF partial changes are self-consistent AND non-breaking:
                MARK changes as "candidate for keep"
            ELSE:
                MARK changes as "rollback"
        IF status == FAILED | TIMEOUT:
            ROLLBACK that agent's changes immediately

    /* Re-verify kept changes in isolation */
    IF any changes marked "candidate for keep":
        RUN verification on kept changes alone
        IF verification passes:
            PROCEED to post_merge_verification with kept changes only
        ELSE:
            ROLLBACK all — partial parallel state is worse than clean baseline

    /* Schedule failed tasks for sequential retry */
    QUEUE failed tasks for sequential execution
END
```

**Isolation-aware rollback:** When using worktrees, rollback is simply discarding the worktree. When sharing a directory, use `git checkout -- <files>` or equivalent per-agent file lists from the dispatch table.

## Post-Merge Verification Gate

**Mandatory.** All agents completing individually does NOT guarantee the combined state is valid. This gate runs after integration, before any commit or PR.

```
BEGIN POST_MERGE_VERIFICATION
    /* Step 1: Combine all agent changes into working state */
    /* Step 2: Run full verification suite */

    RUN: linter / type-check on all changed files
    RUN: test suite covering all modified modules
    RUN: integration tests (if available)

    IF all pass:
        MARK: "Parallel dispatch verified — safe to commit"
    ELSE:
        /* Conflict diagnosis */
        FOR EACH failing test/check:
            IDENTIFY: which agent(s) touched the relevant code
            DETERMINE: is this a cross-agent interaction failure?

        IF cross-agent interaction failure:
            ROLLBACK the interacting agents' changes
            RE-DISPATCH those tasks as sequential (they are NOT truly independent)
            WARN: "[parallel-swarm] Independence assumption was wrong — tasks had hidden coupling"

        IF single-agent regression:
            ROLLBACK that agent's changes only
            RE-DISPATCH that single task with additional context
END
```

## Prompt Construction Principles

Good agent prompts are:
1. **Focused** - One clear problem domain
2. **Self-contained** - All context needed to understand the problem
3. **Specific about output** - What should the agent return, in what format
4. **Bounded** - Time/attempt limits to prevent runaway execution

### Template

```markdown
## Task: <brief description>

## Problem
<exact error messages, test names, or failure symptoms>

## Scope
- Files to read: <list>
- Files to modify: <list>
- Do NOT touch: <list or "anything else">

## Context
<relevant code snippets, recent changes, or background info>

## Success Criteria
<observable, testable condition that proves completion>
Example: "All 3 targeted tests pass with `npm test -- agent-tool-abort`"
Example: "Linting passes with zero errors on modified files"

## Constraints
- <constraint 1, e.g., "Fix tests only, no production changes">
- <constraint 2, e.g., "Do NOT increase arbitrary timeouts">

## Resource Budget
- Max attempts: <N> (stop and report if exceeded)
- Time budget: <e.g., "10 minutes">

## Expected Output
Return a structured summary:
1. Root cause: <what you found>
2. Changes made: <file:line → what changed>
3. Verification: <how you confirmed the fix works>
```

### Examples

**Example 1: Test failures (focused scope)**

```markdown
Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:

1. "should abort tool with partial output capture" - expects 'interrupted at' in message
2. "should handle mixed completed and aborted tools" - fast tool aborted instead of completed
3. "should properly track pendingToolCount" - expects 3 results but gets 0

These are timing/race condition issues. Your task:

1. Read the test file and understand what each test verifies
2. Identify root cause - timing issues or actual bugs?
3. Fix by:
   - Replacing arbitrary timeouts with event-based waiting
   - Fixing bugs in abort implementation if found
   - Adjusting test expectations if testing changed behavior

Do NOT just increase timeouts - find the real issue.

Success Criteria: All 3 tests pass with `npm test -- agent-tool-abort`
Resource Budget: Max 5 attempts, 10 minutes

Return:
1. Root cause found
2. Changes made (file:line)
3. Verification steps taken
```

**Example 2: Multi-module feature development**

```markdown
Implement user avatar upload for the profile page.

Scope:
- Files to modify: src/features/profile/avatar-upload.ts, src/features/profile/avatar-preview.tsx
- Files to read: src/api/upload-client.ts, src/types/user.ts
- Do NOT touch: src/api/auth.ts, src/features/settings/*

Context:
- Upload client already exists at src/api/upload-client.ts with `uploadFile(file: File): Promise<string>`
- User type has `avatarUrl?: string` field
- Max file size: 2MB, accepted: image/png, image/jpeg

Success Criteria:
- Avatar upload component renders on profile page
- File validation rejects >2MB and non-image files
- Upload completes and preview updates
- `npm test -- profile/avatar` passes

Constraints:
- Use existing upload client, do not create a new HTTP client
- Follow existing component patterns in src/features/profile/

Resource Budget: Max 3 attempts, 15 minutes
```

**Example 3: Multi-platform config fix**

```markdown
Fix the CORS configuration errors on 3 deployment platforms.

Each platform has its own config file — fixes are independent:

1. platforms/aws/serverless.yml — CORS AllowOrigin uses wrong domain pattern
2. platforms/gcp/app.yaml — Missing CORS headers for OPTIONS preflight
3. platforms/vercel/vercel.json — headers.routes pattern doesn't match API paths

Files to modify: Only the 3 config files listed above
Do NOT touch: src/ directory, any application code

Success Criteria:
- Each config file passes its platform's validation command
- No CORS errors when testing against staging endpoint

Resource Budget: Max 2 attempts per platform, 5 minutes each
```

## Common Mistakes

**❌ Too broad:** "Fix all the tests" — agent gets lost
**✅ Specific:** "Fix agent-tool-abort.test.ts" — focused scope

**❌ No context:** "Fix the race condition" — agent doesn't know where
**✅ Context:** Paste the error messages and test names

**❌ No constraints:** Agent might refactor everything
**✅ Constraints:** "Do NOT change production code" or "Fix tests only"

**❌ Vague output:** "Fix it" — you don't know what changed
**✅ Specific:** "Return summary of root cause and changes"

**❌ Over-parallelization:** Splitting 1 coherent task into 10 micro-agents
**✅ Right granularity:** Each agent owns a meaningful, self-contained problem domain

**❌ Missing logical dependency:** "Agent A rewrites the API, Agent B updates the client" — sounds independent but isn't
**✅ Detect coupling:** Check for interface/contract relationships before dispatching

**❌ No return format:** Each agent returns free-form text, impossible to parse
**✅ Structured output:** All agents use the same return template (root cause, changes, verification)

**❌ Skip post-merge verification:** "All agents passed, ship it!" — but combined state breaks
**✅ Mandatory verification gate:** Run full suite on integrated changes before committing

## Isolation Guidelines

### Default: Use Worktree Isolation

```
RECOMMENDED: isolation = "worktree"
```

Each dispatched agent should run in an isolated worktree. Benefits:
- No git state conflicts (independent index/working tree)
- No build cache collisions
- No lock file contention
- Clean rollback (just discard the worktree)

**Override to shared_dir only when:**
- All tasks are read-only (zero file modifications)
- Platform does not support worktrees
- Single very-small task where worktree overhead exceeds benefit

**Override to read_only only when:**
- Agent's purpose is investigation/analysis with no modifications

### Isolation-Aware Dispatch

When constructing agent prompts, include the isolation mode so the agent knows its constraints:

```markdown
## Environment
- Isolation: worktree (you have your own copy of the repo)
- Working directory: <worktree_path>
- When done: your changes will be merged back by the orchestrator
```

## Timeout and Budget Guidelines

### Per-Agent Defaults

| Task Complexity | Wall-Clock Budget | Max Retries | Max Diff Iterations |
|----------------|-------------------|-------------|---------------------|
| Simple fix (1-2 files) | 5 minutes | 2 | 3 |
| Moderate (3-5 files) | 10 minutes | 3 | 5 |
| Complex (6+ files) | 15 minutes | 3 | 7 |

### Spinning Detection

An agent is "spinning" if:
- 3+ consecutive iterations produce no meaningful diff (same edits applied and reverted)
- Same error message appears 2+ times without progress
- Agent output becomes repetitive without new information

**Action:** Terminate immediately on spinning detection. Do not extend timeout.

### Total Budget

```
total_wall_clock = max(per_agent_budgets) + 5m_overhead
/* Parallel agents run concurrently, so total ≈ longest single agent + overhead */
```

If total budget exceeds 30 minutes, reconsider whether the task is suitable for parallel dispatch.

## Real-World Examples

### Example A: Test Failure Batch (2025-10-03)

**Scenario:** 6 test failures across 3 files after major refactoring

**Failures:**
- agent-tool-abort.test.ts: 3 failures (timing/race conditions)
- batch-completion-behavior.test.ts: 2 failures (tools not executing)
- tool-approval-race-conditions.test.ts: 1 failure (execution count = 0)

**Decision:** Independent domains — abort logic ≠ batch completion ≠ race conditions

**Dispatch:** 3 agents in parallel, worktree isolation, each with focused prompt + file scope constraint

**Results:**
| Agent | Root Cause | Fix |
|-------|-----------|-----|
| 1 | Arbitrary timeouts masking race conditions | Replaced with event-based waiting |
| 2 | Event structure bug (threadId in wrong place) | Moved threadId to correct field |
| 3 | Missing async wait for tool execution | Added await for completion signal |

**Post-merge verification:** Full test suite green. Zero conflicts.

**Outcome:** All fixes independent, zero conflicts, full suite green. Time saved: 3 problems solved concurrently vs sequentially.

### Example B: Multi-Platform Config Fix (2025-11-15)

**Scenario:** Staging deployment fails on 3 different platforms with different CORS issues

**Decision:** Each platform config is independent — separate files, no shared state

**Dispatch:** 3 agents in parallel, each scoped to one platform config file

**Results:** All 3 agents completed within 5 minutes. Post-merge verification confirmed all platforms passed validation.

**Lesson:** Platform-specific configs are ideal parallel targets — naturally isolated, well-bounded.

### Example C: Failed Parallelization — Hidden Coupling (2025-12-01)

**Scenario:** 2 tasks: "Refactor User interface" and "Fix user profile rendering bug"

**Initial decision:** Appeared independent — different files (types.ts vs profile.tsx)

**Result:** Agent A renamed fields on the User interface. Agent B's fix used the old field names. Post-merge verification caught 4 type errors.

**Resolution:** Rolled back both agents, re-dispatched sequentially. Updated independence check to include interface/consumer analysis.

**Lesson:** Shared type definitions create logical dependencies even when files don't overlap. The logical conflict detection in Stage 2 now catches this pattern.

## When NOT to Use

**Related failures:** Fixing one might fix others — investigate together first
**Need full context:** Understanding requires seeing entire system
**Exploratory debugging:** You don't know what's broken yet
**Shared state:** Agents would interfere (editing same files, using same resources)
**Logical coupling:** Tasks share an interface, contract, or conceptual entity even if files differ
**Over-decomposed:** More than 8 agents signals wrong granularity — merge related tasks

## Integration

**Called by:**
- **task-dispatcher** (Step 3) — evaluates parallelism strategy and dispatches when criteria are met
- Any workflow with multiple independent debugging tasks across different subsystems

**Responsibility boundary:**
- parallel-swarm owns: decision logic (when to parallelize), independence verification, prompt construction principles, rollback protocol, post-merge verification gate
- caller owns: dispatch table management, subagent lifecycle (launch/track/recycle), result collection, conflict resolution
