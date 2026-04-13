---
name: verify-gate
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
categories: ["code-quality"]
triggers: ["verify gate", "verify this batch", "verify completion", "check verification"]
user-invocable: true
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
    /* Identify verification commands from project context */
    IF ~/.vega-punk/roadmap.json exists:
        /* Check if there are verification targets in current step/phase */
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

    /* Check for previous verification results */
    IF ~/.vega-punk/verify-result.json exists:
        last_result = read ~/.vega-punk/verify-result.json
        IF last_result.passed == true AND last_result.timestamp < 5 minutes ago:
            TELL: "[verify-gate] Previous verification passed {time} ago. Re-verifying for freshness."
            /* Still re-run — iron law requires fresh evidence */
END
```

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: Write verification result, state actual status with evidence
   - If YES: Write verification result, state claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = unverified claim, not a verified result
```

## Verification Result Output

After running verification, write a structured result so the calling skill can act on it:

```
WRITE ~/.vega-punk/verify-result.json (same directory as ~/.vega-punk/roadmap.json and ~/.vega-punk/vega-punk-state.json):
{
  "timestamp": "<ISO8601>",
  "command": "<command that was run>",
  "exit_code": <0 or non-zero>,
  "output_summary": "<first 200 chars of output>",
  "passed": true|false,
  "failures": ["<specific failure descriptions if any>"]
}
```

If ~/.vega-punk/verify-result.json already exists, append to an array instead of overwriting.

## Verification Failure Handling

```
BEGIN VERIFY_FAILURE
    IF verification passed:
        REPORT: "Verified: <command> — all <N> checks passed"
        RETURN control to caller

    IF verification failed:
        REPORT: "Verification FAILED: <command> — <N> failures"
        LIST each failure with evidence

        CASE caller is task-dispatcher (batch mode):
            DO NOT advance to next batch
            MARK current batch as "verification_failed"
            RETURN control to caller for fix-and-retry
            /* Max 3 verify-gate invocations per batch.
               If still failing: mark task failed, log to progress.json, escalate if critical */

        CASE caller is plan-executor (step mode):
            DO NOT mark step as complete
            RETURN control to caller (STEP_MACHINE handles retry logic)
            /* STEP_MACHINE retries up to 3 attempts. On 3rd failure: marks step "failed", asks user */

        CASE caller is standalone (direct invocation):
            ASK: "Verification failed. What would you like to do?
                  (1) I'll fix it and re-verify
                   (2) Show me the details
                   (3) Proceed anyway (not recommended)"
            FOLLOW user direction
END
```

## Failure Retry Loop

verify-gate itself does not fix — it only reports. The **caller** is responsible for fixing and re-invoking:

| Caller | Who fixes | Max retries | On exhaustion |
|--------|-----------|-------------|---------------|
| task-dispatcher | Implementer subagent (same task) | 3 verify-gate invocations | Mark task failed, log to ~/.vega-punk/progress.json, escalate if critical |
| plan-executor | Current session (STEP_MACHINE) | 3 step attempts | Mark step failed, ask user |
| review-request | Implementer fixes flagged issues | 2 review cycles | Escalate disagreement to user |
| standalone | Current session or user | User-directed | Follow user choice |

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

## Key Patterns

**Tests:**
```
[Run test command] → [See: 34/34 pass] → "All tests pass"
NOT: "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
NOT: "I've written a regression test" (without red-green verification)
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
- **task-dispatcher** — Step 3.7 after each batch passes spec + code quality reviews
- **plan-executor** — verification rules are defined inline in Step 2a (verify-gate principles apply)
- **Any skill** before making success claims

**Does NOT call other skills** — verify-gate is a terminal verification step. It returns control to the caller.

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. Write the result. THEN claim the result.

This is non-negotiable.
