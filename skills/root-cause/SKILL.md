---
name: root-cause
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
categories: ["code-quality"]
triggers: ["bug", "fix", "error", "not working", "crash", "failed", "exception", "test failure", "unexpected behavior", "debug", "performance problem"]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: a problem to debug */
    IF no error message, test failure, or symptom described:
        FAIL: "[root-cause] No problem identified. Cannot debug without a symptom."
        EXIT

    /* Validate reproducibility */
    IF issue is not reproducible:
        TELL: "[root-cause] Issue not reproducible. Gathering more data before investigation."
        ADD diagnostic instrumentation
        COLLECT evidence
        IF evidence still insufficient:
            TELL: "[root-cause] Cannot reproduce after instrumentation. Need more context."
            ASK user for reproduction steps

    /* Check recent changes for clues */
    IF git repository:
        recent_changes = git diff HEAD~5..HEAD --stat
        IF no recent changes:
            TELL: "[root-cause] No recent code changes. Issue may be environmental."
            CHECK environment variables, config files, dependencies

    /* Check for existing findings */
    IF ~/.vega-punk/vega-punk-state.json exists AND findings field exists:
        LOAD existing findings into context
END
```

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Manager wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

```
BEGIN PHASE1_ROOT_CAUSE
    /* Step 1: Read Error Messages Carefully */
    READ full error output — do NOT skip past errors or warnings
    NOTE: line numbers, file paths, error codes from stack traces

    /* Step 2: Reproduce Consistently */
    ATTEMPT to trigger issue reliably
    IF not reproducible:
        ADD diagnostic instrumentation
        COLLECT evidence
        IF evidence still insufficient:
            ASK user for reproduction steps
            STOP — do NOT guess

    /* Step 3: Check Recent Changes */
    IF git repository:
        CHECK git diff, recent commits, new dependencies, config changes
        IF no recent changes:
            CHECK environment variables, config files, dependencies

    /* Step 4: Gather Evidence in Multi-Component Systems */
    IF system has multiple components:
        FOR EACH component boundary:
            LOG what data enters component
            LOG what data exits component
            VERIFY environment/config propagation
            CHECK state at each layer
        RUN once to gather evidence
        ANALYZE evidence to identify WHERE it breaks
        INVESTIGATE that specific component

    EXAMPLE — multi-layer system (codesign pipeline):
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

    /* Step 5: Trace Data Flow */
    IF error is deep in call stack:
        See root-cause-tracing.md for complete backward tracing technique
        TRACE backward: where does bad value originate?
        TRACE upward: what called this with bad value?
        CONTINUE until source found
        FIX at source, NOT at symptom
END
```

### Phase 2: Pattern Analysis

```
BEGIN PHASE2_PATTERN
    /* Step 1: Find Working Examples */
    LOCATE similar working code in same codebase
    IDENTIFY what works that's similar to what's broken

    /* Step 2: Compare Against References */
    IF implementing a known pattern:
        READ reference implementation COMPLETELY — every line
        UNDERSTAND the pattern fully before applying

    /* Step 3: Identify Differences */
    LIST every difference between working and broken, however small
    DO NOT assume "that can't matter"

    /* Step 4: Understand Dependencies */
    IDENTIFY: what other components does this need?
    IDENTIFY: what settings, config, environment?
    IDENTIFY: what assumptions does it make?
END
```

### Phase 3: Hypothesis and Testing

```
BEGIN PHASE3_HYPOTHESIS
    /* Step 1: Form Single Hypothesis */
    STATE clearly: "I think X is the root cause because Y"
    WRITE it down — be specific, not vague

    /* Step 2: Test Minimally */
    Make SMALLEST possible change to test hypothesis
    One variable at a time — do NOT fix multiple things at once

    /* Step 3: Verify Before Continuing */
    IF it worked:
        PROCEED to Phase 4
    IF it didn't work:
        Form NEW hypothesis — do NOT add more fixes on top

    /* Step 4: When You Don't Know */
    IF cannot form hypothesis:
        SAY "I don't understand X"
        ASK for help or research more
END
```

### Phase 4: Implementation

```
BEGIN PHASE4_IMPLEMENTATION
    /* Step 1: Create Failing Test Case */
    WRITE simplest possible reproduction
    AUTOMATE test if possible (use test-first skill)
    MUST have before fixing

    /* Step 2: Implement Single Fix */
    Address root cause only — ONE change at a time
    NO "while I'm here" improvements
    NO bundled refactoring

    /* Step 3: Verify Fix */
    CHECK: test passes?
    CHECK: no other tests broken?
    CHECK: issue actually resolved?

    /* Step 4: If Fix Doesn't Work */
    IF fix fails:
        COUNT: how many fixes tried?
        IF < 3:
            RETURN to Phase 1, re-analyze with new information
        IF >= 3:
            GOTO STEP 5 (Question Architecture)

    /* Step 5: If 3+ Fixes Failed — Question Architecture */
    IF pattern matches architectural problem:
        - Each fix reveals new shared state/coupling in different place
        - Fixes require "massive refactoring" to implement
        - Each fix creates new symptoms elsewhere
    THEN:
        STOP — this is NOT a failed hypothesis, this is a wrong architecture
        DISCUSS with human partner before more fixes
        IF invoked from vega-punk:
            SET state = CLARIFY (requirements need redefinition)
                OR DESIGN (architecture needs restructuring)
            BRING execution_result + evidence from all failed attempts
END
```

## Red Flags - STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals new problem in different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (see Phase 4.5)

## your human partner's Signals You're Doing It Wrong

**Watch for these redirections:**
- "Is that not happening?" - You assumed without verifying
- "Will it show us...?" - You should have added evidence gathering
- "Stop guessing" - You're proposing fixes without understanding
- "Ultrathink this" - Question fundamentals, not just symptoms
- "We're stuck?" (frustrated) - Your approach isn't working

**When you see these:** STOP. Return to Phase 1.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## When Process Reveals "No Root Cause"

If systematic investigation reveals issue is truly environmental, timing-dependent, or external:

1. You've completed the process
2. Document what you investigated
3. Implement appropriate handling (retry, timeout, error message)
4. Add monitoring/logging for future investigation

**But:** 95% of "no root cause" cases are incomplete investigation.

## Supporting Techniques

These techniques are part of systematic debugging and available in this directory:

- **`root-cause-tracing.md`** - Trace bugs backward through call stack to find original trigger
- **`defense-in-depth.md`** - Add validation at multiple layers after finding root cause
- **`condition-based-waiting.md`** - Replace arbitrary timeouts with condition polling

**Related skills:**
- **test-first** - For creating failing test case (Phase 4, Step 1)
- **verify-gate** - Verify fix worked before claiming success

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common
