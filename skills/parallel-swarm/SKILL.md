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

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: 2+ independent tasks */
    IF fewer than 2 independent tasks identified:
        FAIL: "[parallel-swarm] Only 1 task identified. Use sequential dispatch instead."
        EXIT

    /* Validate tasks are truly independent */
    FOR EACH pair of tasks (A, B):
        IF A and B modify same files:
            FAIL: "[parallel-swarm] Tasks {A} and {B} target same files. Not independent — use sequential."
            EXIT
        IF A depends on B's output:
            FAIL: "[parallel-swarm] Task {A} depends on {B}. Use sequential dispatch."
            EXIT

    /* Validate each task has enough context */
    FOR EACH task:
        IF task has no specific target (file, function, test):
            FAIL: "[parallel-swarm] Task {task} has no specific target. Cannot dispatch."
            EXIT
        IF task has no expected output:
            ADD expected output: "Make these tests pass / Fix this behavior"
END
```

## When to Use

**Decision tree:**

```
Multiple failures or independent tasks?
├── No → Sequential execution (don't use parallel-swarm)
└── Yes
    └── Are they independent? (disjoint files, no shared state)
        ├── No, related → Single agent investigates all
        └── Yes
            └── Can they run without interfering?
                ├── No, shared resources → Sequential agents
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

## The Decision Process

```
BEGIN PARALLEL_EVALUATION
    /* Step 1: Classify Independence */
    FOR EACH pair of tasks (A, B):
        IF A and B modify same files:
            MARK: NOT parallel — shared file edits risk conflicts
            EXIT as "sequential"
        IF A depends on B's output:
            MARK: NOT parallel — dependency ordering required
            EXIT as "sequential"
        IF A and B share mutable state (DB, config, env):
            MARK: NOT parallel — interference risk
            EXIT as "sequential"

    /* Step 2: Verify Sufficient Context */
    FOR EACH task:
        IF task has no specific target (file, function, test):
            ADD missing target → cannot dispatch
            EXIT as "needs_context"
        IF task has no expected output:
            ADD expected output: "Make these tests pass / Fix this behavior"

    /* Step 3: Decide Strategy */
    IF all tasks pass Steps 1 and 2:
        EXIT as "parallel"
        RETURN: dispatch strategy = parallel_swarm
    ELSE:
        EXIT as "sequential"
        RETURN: dispatch strategy = sequential
END
```

## Dispatch Table (Caller-managed)

The calling skill (typically task-dispatcher) owns the dispatch table. Use this structure for tracking:

```json
{
  "dispatch_table": [
    {
      "task_id": "1",
      "scope": "Fix 3 timing failures in agent-tool-abort.test.ts",
      "target_files": ["src/agents/agent-tool-abort.test.ts"],
      "goal": "Make all 3 tests pass without increasing timeouts",
      "constraints": "Fix tests only — do NOT change production code",
      "status": "dispatched|complete|failed",
      "agent_ref": "<platform-native agent identifier>"
    }
  ]
}
```

**Note:** `agent_ref` is whatever tracking mechanism your platform provides (sessionKey, process ID, task handle, etc.). Do NOT assume a specific format — use what's available.

## Agent Lifecycle

Each dispatched agent follows a lifecycle managed by the caller:

```
DISPATCHED → (running) → COMPLETE | FAILED | PARTIAL
                                     ↓              ↓
                              integrate        assess safety
                                               partial fixes
```

| Status | Meaning | Caller Action |
|--------|---------|---------------|
| `COMPLETE` | All tasks in scope pass, summary returned | Integrate changes |
| `FAILED` | Agent couldn't fix the issue | Diagnose manually or mark for later |
| `PARTIAL` | Some but not all tasks pass | Assess if partial fix is safe to merge |
| `NEEDS_CONTEXT` | Agent lacked information to proceed | Re-dispatch with missing context |

**Handling stuck agents:** If an agent takes too long or loops:
1. Check its intermediate output
2. If making progress → wait
3. If spinning → terminate and handle manually

## Prompt Construction Principles

Good agent prompts are:
1. **Focused** - One clear problem domain
2. **Self-contained** - All context needed to understand the problem
3. **Specific about output** - What should the agent return?

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

## Constraints
- <constraint 1, e.g., "Fix tests only, no production changes">
- <constraint 2, e.g., "Do NOT increase arbitrary timeouts">

## Expected Output
Return: <summary of root cause, what you changed, and verification steps>
```

### Examples

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

Return: Summary of what you found and what you fixed.
```

## Common Mistakes

**❌ Too broad:** "Fix all the tests" - agent gets lost
**✅ Specific:** "Fix agent-tool-abort.test.ts" - focused scope

**❌ No context:** "Fix the race condition" - agent doesn't know where
**✅ Context:** Paste the error messages and test names

**❌ No constraints:** Agent might refactor everything
**✅ Constraints:** "Do NOT change production code" or "Fix tests only"

**❌ Vague output:** "Fix it" - you don't know what changed
**✅ Specific:** "Return summary of root cause and changes"

## When NOT to Use

**Related failures:** Fixing one might fix others - investigate together first
**Need full context:** Understanding requires seeing entire system
**Exploratory debugging:** You don't know what's broken yet
**Shared state:** Agents would interfere (editing same files, using same resources)

## Real-World Example

**Scenario:** 6 test failures across 3 files after major refactoring (2025-10-03)

**Failures:**
- agent-tool-abort.test.ts: 3 failures (timing/race conditions)
- batch-completion-behavior.test.ts: 2 failures (tools not executing)
- tool-approval-race-conditions.test.ts: 1 failure (execution count = 0)

**Decision:** Independent domains — abort logic ≠ batch completion ≠ race conditions

**Dispatch:** 3 agents in parallel, each with focused prompt + file scope constraint

**Results:**
| Agent | Root Cause | Fix |
|-------|-----------|-----|
| 1 | Arbitrary timeouts masking race conditions | Replaced with event-based waiting |
| 2 | Event structure bug (threadId in wrong place) | Moved threadId to correct field |
| 3 | Missing async wait for tool execution | Added await for completion signal |

**Outcome:** All fixes independent, zero conflicts, full suite green. Time saved: 3 problems solved concurrently vs sequentially.

## Integration

**Called by:**
- **task-dispatcher** (Step 3) — evaluates parallelism strategy and dispatches when criteria are met
- Any workflow with multiple independent debugging tasks across different subsystems

**Responsibility boundary:**
- parallel-swarm owns: decision logic (when to parallelize), prompt construction principles
- caller owns: dispatch table management, subagent lifecycle (launch/track/recycle), result collection, conflict resolution, full test suite verification
