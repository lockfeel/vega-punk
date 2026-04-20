---
name: root-cause
description: "Systematic debugging: find root cause before proposing fixes. 做什么：严重性分类→根因调查→模式分析→假设验证→修复。何时用：遇到bug、测试失败或异常行为时。触发词: bug, fix, error, not working, crash, failed, exception, test failure, unexpected behavior, debug, performance problem, 报错, 出错, 调试, 排查"
categories: [ "code-quality", "debugging" ]
triggers: [ "bug" ,"fix" ,"error" , "not working", "crash", "failed", "exception", "test failure", "unexpected behavior", "debug", "performance problem", "报错", "出错", "调试", "排查" ]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Key Terms

| Term | Definition |
|------|-----------|
| **Decision Maker** | The person with final authority on scope/architecture decisions. Defaults to the human operating the session. Configurable per-project. |
| **Severity** | P0 (production down / data loss / security) → P1 (feature broken, workaround exists) → P2 (degraded experience) → P3 (cosmetic / nice-to-fix) |
| **Investigation Budget** | Maximum time/effort per phase before escalating or switching strategy. Varies by severity. |
| **Architecture Escalation** | Meta-level judgment that the problem is structural, not local. Can be triggered from ANY phase. |

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes. Violating this is not a shortcut — it's rework.

## Severity Triage

Before starting Phase 1, classify severity. Severity determines pace, budget, and allowable shortcuts:

| Severity | Pace | Phase 1 Budget | Phase 3 Budget | Special Rules |
|----------|------|----------------|----------------|---------------|
| **P0** (prod down, data loss, security) | Fast triage → minimal fix → harden | 15 min | 2 hypotheses, 10 min | "Stop the bleeding" first: add safeguard/fallback, then investigate root cause fully |
| **P1** (feature broken, workaround exists) | Standard | 30 min | 3 hypotheses, 15 min | Standard four-phase process |
| **P2** (degraded experience) | Standard | 30 min | 3 hypotheses, 15 min | Standard four-phase process |
| **P3** (cosmetic, nice-to-fix) | Relaxed | 15 min | 2 hypotheses, 10 min | If root cause not found in budget, log and defer — don't overspend |

**P0 special protocol:**
```
BEGIN P0_PROTOCOL
    /* Step 1: Stop the bleeding */
    ADD safeguard / fallback / kill-switch to prevent further damage
    DEPLOY safeguard immediately
    /* This is NOT a fix — it's a containment measure */

    /* Step 2: Now investigate root cause with standard process */
    PROCEED to Phase 1 with full rigor
    /* The safeguard gives you time to do this properly */

    /* Step 3: Fix root cause properly */
    IMPLEMENT fix at root cause level
    VERIFY safeguard + fix work together
    REMOVE safeguard only after fix is verified in production
END
```

## Architecture Escalation (Cross-Phase Safety Net)

This is NOT part of Phase 4. It is a meta-level safety net that can be triggered from ANY phase when evidence points to a structural problem.

```
BEGIN ARCHITECTURE_ESCALATION
    /* Trigger conditions — can occur at ANY phase */
    SIGNALS:
        - Each investigation reveals new shared state / coupling in a different place
        - "Fix" requires massive refactoring to implement even a simple change
        - Each attempted fix creates new symptoms elsewhere
        - Multiple components break in correlated ways (not independent failures)
        - No working example exists because the pattern itself is novel/broken
        - Phase 3 has exhausted hypothesis budget without confirmed root cause

    WHEN triggered:
        STOP current phase
        DO NOT attempt more fixes
        PRESENT to Decision Maker:
            "Evidence suggests this is an architectural problem, not a local bug:
             {evidence from investigation}
             Recommend: {redesign / restructure / add abstraction layer / revert to known-good pattern}
             Continue debugging locally? (likely to fail again)
             Or restructure first? (addresses root cause at architecture level)"
        IF invoked from vega-punk:
            SET state = CLARIFY (requirements need redefinition)
                OR DESIGN (architecture needs restructuring)
            BRING execution_result + evidence from all failed attempts
END
```

## Unified Investigation Pipeline

Gate validation and Phase 1 intake are merged. No logic is duplicated.

```
BEGIN INVESTIGATION_PIPELINE
    /* ═══════════════════════════════════════════
       Pre-Flight: Validate and Triage
       ═══════════════════════════════════════════ */

    IF no error message, test failure, or symptom described:
        FAIL: "[root-cause] No problem identified. Cannot debug without a symptom."

    /* Severity triage (see Severity Triage section) */
    severity = CLASSIFY_SEVERITY(symptom)
    SET investigation budgets per severity table

    /* Reproducibility check */
    ATTEMPT to trigger issue
    IF not reproducible:
        ADD diagnostic instrumentation (logging, tracing, state snapshots)
        COLLECT evidence
        IF evidence still insufficient:
            ASK Decision Maker for reproduction steps
            STOP — do NOT guess at causes

    /* Recent changes check */
    IF git repository:
        recent_changes = git diff HEAD~5..HEAD --stat
        IF no recent changes:
            CHECK environment variables, config files, dependencies
            ANNOTATE: "No recent code changes. Issue may be environmental."

    /* Load existing findings if available */
    IF ~/.vega-punk/vega-punk-state.json exists AND findings field exists:
        LOAD existing findings into context

    /* ═══════════════════════════════════════════
       Phase 1: Root Cause Investigation
       ═══════════════════════════════════════════ */

    /* Entry criteria: symptom identified, severity classified, reproducibility assessed */
    /* Exit criteria (success): understand WHAT is wrong and WHY */
    /* Exit criteria (failure): investigation budget exhausted → ARCHITECTURE_ESCALATION */
    /* Exit criteria (defer): environmental/external issue → document + monitor */

    /* Step 1: Read Error Messages Carefully */
    READ full error output — do NOT skip past errors or warnings
    NOTE: line numbers, file paths, error codes from stack traces

    /* Step 2: Check Recent Changes (already computed in Pre-Flight) */
    REVIEW recent_changes for clues
    IF relevant commit found:
        BISECT: git bisect to isolate exact commit that introduced the issue

    /* Step 3: Gather Evidence in Multi-Component Systems */
    IF system has multiple components:
        FOR EACH component boundary:
            LOG what data enters component
            LOG what data exits component
            VERIFY environment/config propagation
            CHECK state at each layer
        RUN once to gather evidence
        ANALYZE evidence to identify WHERE it breaks
        INVESTIGATE that specific component

    EXAMPLE — multi-layer system (domain-specific: macOS codesign pipeline):
    ```bash
    # Layer 1: Workflow — are secrets available?
    echo "=== Secrets available: ==="
    echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

    # Layer 2: Build script — env propagation?
    echo "=== Env vars in build script: ==="
    env | grep IDENTITY || echo "IDENTITY not in environment"

    # Layer 3: Signing script — keychain state?
    echo "=== Keychain state: ==="
    security list-keychains
    security find-identity -v

    # Layer 4: Actual signing — does it work?
    codesign --sign "$IDENTITY" --verbose=4 "$APP"
    ```
    This reveals which layer fails: secrets → workflow ✓, workflow → build ✗

    /* Step 4: Trace Data Flow */
    IF error is deep in call stack:
        See root-cause-tracing.md for complete backward tracing technique
        TRACE backward: where does bad value originate?
        TRACE upward: what called this with bad value?
        CONTINUE until source found
        FIX at source, NOT at symptom

    /* Step 5: Multi-component parallel investigation */
    IF evidence from Step 3 reveals failures in 2+ independent components:
        EVALUATE for parallel-swarm dispatch:
            IF component investigations are independent (disjoint code, no shared state):
                INVOKE parallel-swarm to dispatch concurrent investigations
            IF component investigations are coupled:
                Continue sequential investigation

    /* Phase 1 exit check */
    IF root cause identified (WHAT + WHY understood):
        PROCEED to Phase 2
    IF investigation budget exhausted:
        TRIGGER ARCHITECTURE_ESCALATION
    IF issue appears environmental/external after thorough investigation:
        EXIT as "environmental" — document findings, add monitoring, implement defensive handling

    /* ═══════════════════════════════════════════
       Phase 2: Pattern Analysis
       ═══════════════════════════════════════════ */

    /* Entry criteria: Phase 1 completed with identified root cause */
    /* Exit criteria (success): differences between working and broken identified */
    /* Exit criteria (no-reference): no working example exists → skip to Phase 3 with hypothesis based on Phase 1 findings */

    /* Step 1: Find Working Examples */
    LOCATE similar working code in same codebase
    IDENTIFY what works that's similar to what's broken

    IF no working example found:
        IF implementing a known pattern (from docs/standards):
            READ reference implementation COMPLETELY — every line
            USE reference as proxy for "working example"
        IF pattern is novel (no reference anywhere):
            ANNOTATE: "No working reference exists. This is a design problem, not just a bug."
            CONSIDER: TRIGGER ARCHITECTURE_ESCALATION (novel patterns may need design, not debugging)
            IF not escalating:
                PROCEED to Phase 3 with hypothesis based on Phase 1 evidence alone

    /* Step 2: Compare Against References */
    IF working example found:
        READ reference implementation COMPLETELY — every line
        UNDERSTAND the pattern fully before comparing

    /* Step 3: Identify Differences */
    LIST every difference between working and broken, however small
    DO NOT assume "that can't matter"
    RANK differences by likelihood of causing the observed symptom

    /* Step 4: Understand Dependencies */
    IDENTIFY: what other components does this need?
    IDENTIFY: what settings, config, environment?
    IDENTIFY: what assumptions does it make?

    /* ═══════════════════════════════════════════
       Phase 3: Hypothesis and Testing
       ═══════════════════════════════════════════ */

    /* Entry criteria: Phase 2 completed (or skipped with justification) */
    /* Exit criteria (success): hypothesis confirmed, proceed to Phase 4 */
    /* Exit criteria (failure): hypothesis budget exhausted → ARCHITECTURE_ESCALATION */

    /* Step 1: Form Hypothesis Set */
    IF multiple plausible hypotheses exist:
        RANK by testability:
            1. Fastest to test (minimal change needed)
            2. Most likely given Phase 1+2 evidence
            3. Most isolated (tests one variable cleanly)
        SELECT top-ranked hypothesis for testing
        RECORD remaining hypotheses as fallback

    STATE clearly: "I think X is the root cause because Y"
    WRITE it down — be specific, not vague

    /* Step 2: Test Minimally */
    Make SMALLEST possible change to test hypothesis
    One variable at a time — do NOT fix multiple things at once

    /* Step 3: Verify Before Continuing */
    IF test confirms hypothesis:
        PROCEED to Phase 4
    IF test does NOT confirm:
        IF remaining hypotheses exist:
            SELECT next hypothesis from ranked list
            RETURN to Step 2
        IF no remaining hypotheses:
            Form NEW hypothesis based on test results (new evidence)
            IF hypothesis budget NOT exhausted:
                RETURN to Step 1
            IF hypothesis budget exhausted:
                TRIGGER ARCHITECTURE_ESCALATION

    /* Step 4: When You Don't Know */
    IF cannot form ANY hypothesis:
        SAY "I don't understand X"
        ASK Decision Maker for help or research more
        DO NOT guess — an unformed hypothesis is worse than admitting uncertainty

    /* ═══════════════════════════════════════════
       Phase 4: Implementation
       ═══════════════════════════════════════════ */

    /* Entry criteria: Phase 3 confirmed a hypothesis */
    /* Exit criteria (success): bug resolved, all tests pass */
    /* Exit criteria (failure): fix doesn't work → return to Phase 1 or escalate */

    /* Step 1: Create Failing Test Case */
    IF bug is deterministic (reliably reproducible):
        WRITE simplest possible reproduction test
        AUTOMATE test (use test-first skill)
        TEST MUST fail before fix, pass after
    IF bug is non-deterministic (flaky/timing/race condition):
        /* Cannot write a deterministic test easily */
        WRITE stress test that triggers the race condition with high probability
        ADD logging/assertions that capture the failure mode when it occurs
        RUN multiple iterations (minimum 100 for race conditions)
        IF failure rate < 5%:
            ADD more specific assertions or increase contention to raise failure rate
            /* A test that passes 95% of the time doesn't reliably prove the fix */
        RECORD: "Non-deterministic bug. Stress test has {X}% failure rate without fix."

    /* Step 2: Implement Single Fix */
    Address root cause only — ONE change at a time
    NO "while I'm here" improvements
    NO bundled refactoring

    /* Step 3: Verify Fix */
    CHECK: failing test now passes?
    CHECK: no other tests broken? (run relevant test suite)
    CHECK: issue actually resolved? (manual verification if needed)
    IF non-deterministic bug:
        RUN stress test 500+ iterations
        IF failure rate drops to 0%:
            MARK: "Fix verified (500 iterations, 0 failures)"
        IF failure rate drops but not to 0%:
            INVESTIGATE: remaining failures may be a different root cause
            DO NOT declare victory prematurely

    /* Step 4: If Fix Doesn't Work */
    IF fix fails:
        REVERT the fix (do NOT keep broken changes)
        COUNT: how many distinct fix attempts have been made?
        IF < 3:
            RETURN to Phase 1, re-analyze with new information from failed fix
        IF >= 3:
            TRIGGER ARCHITECTURE_ESCALATION
END
```

## Red Flags — STOP and Follow Process

If you catch yourself doing any of these, STOP and return to the appropriate phase:

| Red Flag | What Phase To Return To | Why |
|----------|------------------------|-----|
| "Quick fix for now, investigate later" | Phase 1 | Symptom fixes mask root cause and create rework |
| "Just try changing X and see if it works" | Phase 3 | Random changes aren't hypothesis testing |
| "Add multiple changes, run tests" | Phase 3 Step 2 | Can't isolate what worked; causes new bugs |
| "Skip the test, I'll manually verify" | Phase 4 Step 1 | Untested fixes don't stick |
| "It's probably X, let me fix that" | Phase 1 | Assuming cause without evidence |
| "I don't fully understand but this might work" | Phase 1 | Incomplete understanding = wrong fix |
| "Pattern says X but I'll adapt it differently" | Phase 2 | Partial understanding guarantees bugs |
| "Here are the main problems: [lists fixes without investigation]" | Phase 1 | Solutions without investigation are guesses |
| Proposing solutions before tracing data flow | Phase 1 Step 4 | Symptom ≠ root cause |
| "One more fix attempt" (when already tried 2+) | Architecture Escalation | Repeated failure = structural problem |
| Each fix reveals new problem in different place | Architecture Escalation | Coupling/entanglement, not local bug |

## Decision Maker's Signals You're Doing It Wrong

**Watch for these redirections:**

| Signal | What It Means | What To Do |
|--------|--------------|------------|
| "Is that not happening?" | You assumed without verifying | Phase 1: add evidence gathering, verify assumption |
| "Will it show us...?" | You should have added diagnostics | Phase 1: add logging/tracing to observe the failure |
| "Stop guessing" | You're proposing fixes without understanding | Phase 1: investigate before fixing |
| "Ultrathink this" | Question fundamentals, not symptoms | Return to Phase 1, re-examine assumptions |
| "We're stuck?" (frustrated) | Your approach isn't working | Consider Architecture Escalation |

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. For P0: use P0 protocol — contain first, then investigate. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | Repeated failure = architectural problem. Escalate, don't retry. |

## Quick Reference

| Phase | Key Activities | Success Criteria | Failure/Exit Criteria |
|-------|---------------|------------------|----------------------|
| **Pre-Flight** | Validate symptom, triage severity, check reproducibility | Problem identified, severity classified, budgets set | No symptom = cannot debug |
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY | Budget exhausted → Architecture Escalation; Environmental → document + monitor |
| **2. Pattern** | Find working examples, compare, identify differences | Differences between working and broken identified | No reference → skip to Phase 3 with Phase 1 hypothesis; Novel pattern → Architecture Escalation |
| **3. Hypothesis** | Form hypothesis set, rank by testability, test minimally | Confirmed hypothesis | Budget exhausted → Architecture Escalation; No hypothesis → ask for help |
| **4. Implementation** | Create test (deterministic or stress), fix, verify | Bug resolved, tests pass | Fix fails → Phase 1 (if <3) or Architecture Escalation (if ≥3) |

## When Process Reveals Environmental/External Issue

If systematic investigation reveals issue is truly environmental, timing-dependent, or external:

1. You've completed the process — this IS a valid finding
2. Document what you investigated and what you ruled out
3. Implement appropriate defensive handling (retry with backoff, timeout, graceful degradation, clear error message)
4. Add monitoring/logging for future investigation
5. DO NOT implement a "fix" for something that isn't a code bug — implement resilience instead

**Note:** Many "no root cause" cases are incomplete investigation. Before concluding environmental, verify:
- You traced the full data flow (Phase 1 Step 4)
- You checked all component boundaries (Phase 1 Step 3)
- You compared against working references (Phase 2)

## Supporting Techniques

These techniques are part of systematic debugging and available in this directory:

- **`root-cause-tracing.md`** — Trace bugs backward through call stack to find original trigger
- **`defense-in-depth.md`** — Add validation at multiple layers after finding root cause
- **`condition-based-waiting.md`** — Replace arbitrary timeouts with condition polling

**Related skills:**
- **test-first** — For creating failing test case (Phase 4, Step 1)
- **verify-gate** — Verify fix worked before claiming success
- **parallel-swarm** — When Phase 1 identifies failures in 2+ independent components, dispatch concurrent investigations

## Integration

**Called by:**
- **vega-punk** — when execution encounters errors, before proposing fixes
- **review-intake** — when reviewer identifies a bug, investigate before fixing
- **task-dispatcher** — when a task fails, investigate root cause before retrying
- Any skill encountering unexpected behavior

**Calls next (conditionally):**
- **parallel-swarm** — when multi-component investigation reveals independent failures
- **test-first** — when entering Phase 4 to create failing test case
- **verify-gate** — after Phase 4 fix is implemented

**Architecture Escalation connects to:**
- **vega-punk** state machine — CLARIFY or DESIGN state transition
- Decision Maker — for architectural decision authority
