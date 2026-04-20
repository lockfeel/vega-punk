---
name: verify-gate
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
categories: ["code-quality"]
triggers: ["verify gate", "verify this batch", "verify completion", "check verification"]
user-invocable: true
parameters:
  - name: caller
    type: enum
    values: [task-dispatcher, plan-executor, review-request, standalone]
    default: standalone
    description: Identifies which skill or context invoked verify-gate, used to determine failure handling behavior
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is unreliable — evidence before assertions always.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Ensure result storage directory exists */
    IF ~/.vega-punk/ does not exist:
        CREATE ~/.vega-punk/
        TELL: "[verify-gate] Created ~/.vega-punk/ for verification results"

    /* Identify verification commands from project context */
    IF ~/.vega-punk/roadmap.json exists:
        current_step = ~/.vega-punk/roadmap.json current_step
        IF current_step has verify field:
            verification_target = current_step.verify
            /* Use verify.type to determine command */

    /* Auto-detect project test/build/lint commands */
    CHECK package.json scripts (test, build, lint)
    CHECK pyproject.toml, Cargo.toml, go.mod, Makefile
    IF no verification commands found:
        TELL: "[verify-gate] No verification commands detected in project config."
        ASK: "What should I verify? (1) tests, (2) build, (3) lint, (4) specific check"

    /* Previous results are HISTORICAL ONLY — never use as evidence */
    IF ~/.vega-punk/verify-result.json exists:
        last_result = read ~/.vega-punk/verify-result.json
        TELL: "[verify-gate] Previous verification exists but is not fresh evidence. Re-running."
        /* Iron Law: ALWAYS re-run. No exceptions. No cache. */
END
```

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

**No caching. No freshness windows. No shortcuts. Previous results are historical records only.**

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
   - DEFAULT_TIMEOUT = 300 seconds
   - IF project config specifies longer timeout: use that
   - IF timeout exceeded:
     REPORT: "[verify-gate] Command timed out after {timeout}s"
     WRITE result: { passed: false, failures: ["timeout after {timeout}s"] }
     RETURN failure
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - IF NO: Write verification result, state actual status with evidence
   - IF YES: Write verification result, state claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = unverified claim, not a verified result
```

## Verification Result Output

After running verification, write a structured result so the calling skill can act on it:

```
IF ~/.vega-punk/verify-result.json does not exist:
    WRITE ~/.vega-punk/verify-result.json with initial array:
    [
      {
        "timestamp": "<ISO8601>",
        "command": "<command that was run>",
        "exit_code": <0 or non-zero>,
        "output_summary": "<failure-related lines, or last 500 chars if no failures>",
        "passed": true|false,
        "failures": ["<specific failure descriptions if any>"],
        "caller": "<caller parameter value>"
      }
    ]

IF ~/.vega-punk/verify-result.json already exists:
    READ existing array
    APPEND new result entry to the array
    WRITE the complete updated array
```

**Always use array format** — even for the first entry.

**output_summary extraction rule:**
- IF command passed: last 500 characters of output
- IF command failed: all lines containing `FAIL`, `Error`, `error`, `FAILED`, or ` AssertionError`, plus up to 2 lines of context after each match. If no such lines found, fall back to last 500 characters.

## Multi-Command Verification

When multiple verification commands are needed (e.g., test + lint + build):

```
IF multiple verification commands needed:
    RUN commands in parallel WHERE safe
    /* Safe to parallelize: lint + type-check + test (independent)
       NOT safe to parallelize: build then test (sequential dependency) */
    AGGREGATE results into single verify-result entry:
    {
        "command": "<cmd1> && <cmd2> && <cmd3>",
        "exit_code": <0 if ALL passed, non-zero otherwise>,
        "output_summary": "<combined failure lines from all commands>",
        "passed": true IF ALL commands passed ELSE false,
        "failures": ["<union of all failures from all commands>"]
    }
    REPORT per-command results, THEN aggregate verdict
```

## Verification Failure Handling

```
BEGIN VERIFY_FAILURE
    IF verification passed:
        REPORT: "Verified: <command> — all <N> checks passed"
        RETURN control to caller

    IF verification failed:
        /* Detect environment vs code failures */
        IF output contains "connection refused" OR "database not found" OR "ECONNREFUSED" OR "service unavailable":
            REPORT: "[verify-gate] Verification failed due to ENVIRONMENT issue, not code."
            SUGGEST: "Check if required services (database, API, etc.) are running."
            /* Still write result as failed, but flag environment issue */
            ADD to failures: "[ENVIRONMENT] <specific connection/service error>"

        REPORT: "Verification FAILED: <command> — <N> failures"
        LIST each failure with evidence

        IF caller == "task-dispatcher":
            DO NOT advance to next batch
            MARK current batch as "verification_failed"
            RETURN control to caller for fix-and-retry

        IF caller == "plan-executor":
            DO NOT mark step as complete
            RETURN control to caller (STEP_MACHINE handles retry logic)

        IF caller == "review-request":
            DO NOT mark review as passed
            RETURN control to caller for fix-and-reverify

        IF caller == "standalone":
            ASK: "Verification failed. What would you like to do?
                  (1) I'll fix it and re-verify
                  (2) Show me the details
                  (3) Proceed anyway (not recommended)"
            FOLLOW user direction
END
```

## Checkpoint Protocol

verify-gate requires user confirmation at these decision boundaries — never auto-proceed:

| Checkpoint | Trigger | Action |
|------------|---------|--------|
| `NO_COMMANDS_FOUND` | Auto-detect finds zero verification commands | ASK user what to verify before proceeding |
| `TIMEOUT_EXCEEDED` | Command exceeds timeout (default 300s) | REPORT timeout, ASK: extend timeout / skip / abort |
| `MULTI_COMMAND_FAIL` | Multiple verification commands, some pass some fail | REPORT per-command results, ASK: proceed with partial / abort |
| `ENV_ISSUE_DETECTED` | Output contains connection/service errors | FLAG as environment issue (not code), ASK: check services / proceed anyway |
| `STANDALONE_VERIFY_FAIL` | caller=standalone AND verification fails | ASK user: (1) fix and re-verify, (2) show details, (3) proceed anyway |

**Rule:** Checkpoints gate user-facing decisions, not mechanical execution. Running the command is mandatory; asking what to do with the result follows the checkpoint table.

## Failure Retry Loop

verify-gate itself does not fix — it only reports. The **caller** is responsible for fixing and re-invoking:

| Caller | Who fixes | Max retry cycles | On exhaustion |
|--------|-----------|-----------------|---------------|
| task-dispatcher | Implementer subagent (same task) | 3 retry cycles per verification type | Mark task failed, log to ~/.vega-punk/progress.json, escalate if critical |
| plan-executor | Current session (STEP_MACHINE) | 3 step attempts | Mark step failed, ask user |
| review-request | Implementer fixes flagged issues | 2 review cycles | Escalate disagreement to user |
| standalone | Current session or user | User-directed | Follow user choice |

**Retry cycle definition:** 1 retry cycle = fix attempt → invoke verify-gate → pass or fail. The initial verification does NOT count as a retry cycle.

**Retry flow:** verify-gate fails → caller fixes → caller re-invokes verify-gate → pass or retry again. Never auto-escalate retries — the caller controls the loop.

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |
| Migration works | Migration command: exit 0 | Schema looks right |
| API contract valid | Contract test passes | Manual review |
| No regressions | Full suite green | Only changed-file tests |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |
| "It passed 5 minutes ago" | Stale evidence = no evidence |

## Key Patterns

**Tests:**
```
[Run test command] → [See: 34/34 pass] → "All tests pass"
NOT: "Should pass now" / "Looks correct"
```

**Build:**
```
[Run build] → [See: exit 0] → "Build passes"
NOT: "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
Re-read plan → Create checklist → Verify each → Report gaps or completion
NOT: "Tests pass, phase complete"
```

**Agent delegation:**
```
Agent reports success → Check VCS diff → Verify changes → Report actual state
NOT: Trust agent report
```

**Note:** TDD Red-Green regression verification (revert fix → verify test fails → restore → verify test passes) is outside verify-gate's scope. That workflow belongs to the `test-first` skill. verify-gate only validates command-level pass/fail.

## How to Identify the Right Command

When you need to verify a claim, infer the correct command from project context:
- **Node.js:** Check `package.json` → `scripts` section for test/build/lint commands
- **Python:** Look for `pyproject.toml`, `Makefile`, or `tox.ini`
- **Rust:** `cargo test`, `cargo check`, `cargo clippy`
- **Go:** `go test ./...`, `go vet ./...`
- **Generic:** If no build system found, ask the user or use language-level tools (`python -m py_compile`, `tsc --noEmit`)

Never assume a command exists. Always check the project's configuration first.

## What verify-gate Does NOT Do

verify-gate is a **command-level verifier**. It runs test/lint/build commands and checks their output. It does NOT:

- Check individual file content (that's plan-executor's inline `content_contains` checks)
- Re-run branch-landing's test verification (branch-landing does its own final check)
- Make architectural judgments (it only checks pass/fail of commands)
- Review code quality, naming, architecture, or design patterns (that's `review-request`)
- Check spec compliance (that's the task-dispatcher's spec compliance review)
- Perform TDD Red-Green regression cycles (that's `test-first`)

**Boundary with review-request:**
- verify-gate: "Do the tests pass? Does the build succeed?" (binary, command-level)
- review-request: "Is the code well-structured? Does it follow best practices?" (qualitative, architectural)
- verify-gate runs AFTER reviews pass — it's the final mechanical gate before proceeding

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task or batch
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## Integration

**Called by:**
- **task-dispatcher** — after each batch passes spec + code quality reviews
- **plan-executor** — verification rules are defined inline in step execution (verify-gate principles apply)
- **review-request** — after code quality issues are addressed, before marking review as passed
- **Any skill** before making success claims

**Does NOT call other skills** — verify-gate is a terminal verification step. It returns control to the caller.

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. Write the result. THEN claim the result.

This is non-negotiable.
