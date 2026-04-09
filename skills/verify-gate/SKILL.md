---
name: verify-gate
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
categories: ["code-quality"]
triggers: ["verify gate", "verify this batch", "verify completion", "check verification"]
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is unreliable — evidence before assertions always.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

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
WRITE verify-result.json (same directory as roadmap.json and .vega-punk-state.json):
{
  "timestamp": "<ISO8601>",
  "command": "<command that was run>",
  "exit_code": <0 or non-zero>,
  "output_summary": "<first 200 chars of output>",
  "passed": true|false,
  "failures": ["<specific failure descriptions if any>"]
}
```

If verify-result.json already exists, append to an array instead of overwriting.

## Verification Failure Handling

```
IF verification passed:
    Report: "Verified: <command> — all <N> checks passed"
    Return control to caller

IF verification failed:
    Report: "Verification FAILED: <command> — <N> failures"
    List each failure with evidence

    IF caller is task-dispatcher (batch mode):
        DO NOT advance to next batch
        Mark current batch as "verification_failed"
        Return control to caller for fix-and-retry

    IF caller is plan-executor (step mode):
        DO NOT mark step as complete
        Return control to caller (STEP_MACHINE handles retry logic)

    IF caller is standalone (direct invocation):
        ASK: "Verification failed. What would you like to do?
              (1) I'll fix it and re-verify
               (2) Show me the details
               (3) Proceed anyway (not recommended)"
        FOLLOW user direction
```

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
