---
name: review-intake
description: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
categories: ["code-quality"]
triggers: ["code review feedback", "reviewer suggestion", "fix review comments", "implement feedback", "reviewer said"]
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations. 

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: review feedback items */
    IF no review feedback items provided:
        FAIL: "[review-intake] No review feedback to process. Request a review first."
        EXIT

    /* Validate feedback has actionable items */
    PARSE feedback items:
        IF no specific issues identified:
            TELL: "[review-intake] Review found no issues. No action needed."
            EXIT

    /* Check if feedback references valid file:line locations */
    FOR EACH feedback item:
        IF item references file:line:
            IF file does NOT exist OR line out of range:
                TELL: "[review-intake] Feedback references stale location {file:line}. Skipping."
                MARK item as unactionable

    /* Clarify ambiguous items before implementing */
    IF any item unclear:
        STOP — do not implement anything yet
        ASK for clarification on unclear items
        /* Items may be related. Partial understanding = wrong implementation. */
END
```

## The Response Pattern

```
BEGIN REVIEW_RESPONSE
    /* Step 1: READ — Complete feedback without reacting */
    READ all feedback items fully

    /* Step 2: UNDERSTAND — Restate or ask */
    FOR EACH feedback item:
        RESTATE requirement in own words
        IF unclear:
            MARK as needing clarification

    /* Step 3: VERIFY — Check against codebase reality */
    FOR EACH feedback item referencing file:line:
        VERIFY file exists AND line is in range
        IF stale location:
            MARK item as unactionable

    /* Step 4: EVALUATE — Technically sound for THIS codebase? */
    FOR EACH actionable item:
        CHECK: technically correct for this codebase?
        CHECK: breaks existing functionality?
        CHECK: works on all platforms/versions?

    /* Step 5: RESPOND — Technical acknowledgment or reasoned pushback */
    IF items need clarification:
        STOP — do not implement anything
        ASK for clarification on all unclear items
    ELSE:
        PROCEED to Step 6

    /* Step 6: IMPLEMENT — One item at a time, test each */
    FOR EACH item (ordered: blocking → simple → complex):
        IMPLEMENT fix
        TEST individually
        VERIFY no regressions
END
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" (explicit CLAUDE.md violation)
- "Great point!" / "Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)
- Brief genuine acknowledgment is fine, but lead with substance

## Handling Unclear Feedback

```
BEGIN HANDLE_UNCLEAR
    IF any item is unclear:
        STOP — do not implement anything yet
        ASK for clarification on all unclear items
    /* WHY: Items may be related. Partial understanding = wrong implementation. */
END
```

**Example:**
```
your human partner: "Fix 1-6"
You understand 1,2,3,6. Unclear on 4,5.

❌ WRONG: Implement 1,2,3,6 now, ask about 4,5 later
✅ RIGHT: "I understand items 1,2,3,6. Need clarification on 4 and 5 before proceeding."
```

## Source-Specific Handling

### From your human partner
- **Trusted** - implement after understanding
- **Still ask** if scope unclear
- **No performative agreement**
- **Skip to action** or technical acknowledgment

### From External Reviewers
```
BEGIN EXTERNAL_REVIEW
    FOR EACH suggestion:
        /* Check 1: Technically correct for THIS codebase? */
        /* Check 2: Breaks existing functionality? */
        /* Check 3: Reason for current implementation? */
        /* Check 4: Works on all platforms/versions? */
        /* Check 5: Does reviewer understand full context? */

        IF suggestion seems wrong:
            PUSH BACK with technical reasoning

        IF can't easily verify:
            SAY: "I can't verify this without [X]. Should I [investigate/ask/proceed]?"

        IF conflicts with human partner's prior decisions:
            STOP and discuss with human partner first
END
```

**your human partner's rule:** "External feedback - be skeptical, but check carefully"

## YAGNI Check for "Professional" Features

```
BEGIN YAGNI_CHECK
    IF reviewer suggests "implementing properly":
        GREP codebase for actual usage of suggested feature
        IF unused:
            PROPOSE: "This endpoint isn't called. Remove it (YAGNI)?"
        IF used:
            IMPLEMENT properly
END
```

**your human partner's rule:** "You and reviewer both report to me. If we don't need this feature, don't add it."

## Implementation Order

```
BEGIN IMPLEMENTATION_ORDER
    /* Step 1: Clarify anything unclear FIRST */
    IF any item unclear:
        ASK → WAIT → do NOT proceed

    /* Step 2: Implement in priority order */
    FOR EACH item in order [blocking → simple → complex]:
        blocking_items:     /* breaks, security */
        simple_fixes:       /* typos, imports */
        complex_fixes:      /* refactoring, logic */
        IMPLEMENT fix
        TEST individually
        VERIFY no regressions
END
```

## When To Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Legacy/compatibility reasons exist
- Conflicts with your human partner's architectural decisions

**How to push back:**
- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Involve your human partner if architectural

**Signal if uncomfortable pushing back out loud:** "Strange things are afoot at the Circle K"

## Acknowledging Correct Feedback

```
BEGIN ACKNOWLEDGE_CORRECT
    WHEN feedback IS correct:
        OUTPUT ONE OF:
            "Fixed. [Brief description of what changed]"
            "Good catch - [specific issue]. Fixed in [location]."
            [Just fix it and show in the code]
        AVOID EMPTY GRATITUDE:
            "You're absolutely right!"
            "Great point!"
            "Thanks for catching that!"
            "Thank you!" without substance
        /* Prefer stating the fix factually. Brief genuine acknowledgment is fine — empty praise is not. */
END
```

## Gracefully Correcting Your Pushback

```
BEGIN CORRECT_PUSHPBACK
    IF you pushed back and were wrong:
        OUTPUT ONE OF:
            "You were right - I checked [X] and it does [Y]. Implementing now."
            "Verified this and you're correct. My initial understanding was wrong because [reason]. Fixing."
        NEVER:
            Long apology
            Defending why you pushed back
            Over-explaining
        /* State the correction factually and move on. */
END
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State requirement or just act |
| Blind implementation | Verify against codebase first |
| Batch without testing | One at a time, test each |
| Assuming reviewer is right | Check if breaks things |
| Avoiding pushback | Technical correctness > comfort |
| Partial implementation | Clarify all items first |
| Can't verify, proceed anyway | State limitation, ask for direction |

## Real Examples

**Performative Agreement (Bad):**
```
Reviewer: "Remove legacy code"
❌ "You're absolutely right! Let me remove that..."
```

**Technical Verification (Good):**
```
Reviewer: "Remove legacy code"
✅ "Checking... build target is 10.15+, this API needs 13+. Need legacy for backward compat. Current impl has wrong bundle ID - fix it or drop pre-13 support?"
```

**YAGNI (Good):**
```
Reviewer: "Implement proper metrics tracking with database, date filters, CSV export"
✅ "Grepped codebase - nothing calls this endpoint. Remove it (YAGNI)? Or is there usage I'm missing?"
```

**Unclear Item (Good):**
```
your human partner: "Fix items 1-6"
You understand 1,2,3,6. Unclear on 4,5.
✅ "Understand 1,2,3,6. Need clarification on 4 and 5 before implementing."
```

## GitHub Thread Replies

When replying to inline review comments on GitHub, reply in the comment thread (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), not as a top-level PR comment.

## The Bottom Line

**External feedback = suggestions to evaluate, not orders to follow.**

Verify. Question. Then implement.

No performative agreement. Technical rigor always.

## Completion Contract

After processing all review feedback items:

```
BEGIN COMPLETION_CONTRACT
    COUNT total_items = number of feedback items received
    COUNT implemented = items with code changes made
    COUNT pushed_back = items rejected with technical reasoning
    COUNT unactionable = items with stale locations or unclear feedback

    IF pushed_back > 0:
        PRESENT: list of pushed-back items with reasoning

    IF unactionable > 0:
        PRESENT: list of unactionable items with reason

    WRITE structured result for caller:
        {
            "status": "complete",
            "total_items": total_items,
            "implemented": implemented,
            "pushed_back": pushed_back,
            "unactionable": unactionable,
            "changes": ["<list of modified files>"],
            "regression_check": "<tests pass/fail + method>"
        }
END
```

Callers use this result to decide whether to proceed to the next task/batch or re-review.

## Integration

**Called by:**
- **review-request** (Step 3) — after reviewer subagent returns feedback. review-request dispatches the reviewer; review-intake evaluates and acts on the feedback.
- Any workflow receiving code review comments from external reviewers

**Does NOT call other skills** — review-intake is a terminal processing step. It returns control to the caller (review-request) after all feedback items are processed.
