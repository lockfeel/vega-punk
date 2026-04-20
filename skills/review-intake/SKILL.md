---
name: review-intake
description: "Evaluate and act on code review feedback with technical rigor. 做什么：解析→去重→分类→冲突检测→技术验证→有序实现。何时用：收到代码审查反馈后、实现建议之前。触发词: code review feedback, reviewer suggestion, fix review comments, implement feedback, reviewer said, 审查反馈, 修复review意见"
categories: ["code-quality"]
triggers: ["code review feedback", "reviewer suggestion", "fix review comments", "implement feedback", "reviewer said", "审查反馈", "修复review意见"]
user-invocable: true
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Key Terms

| Term | Definition |
|------|-----------|
| **Decision Maker** | The person with final authority on scope/architecture decisions. Defaults to the human operating the session. Configurable per-project. |
| **Feedback Item** | A single actionable point from a review comment. May be parsed from a multi-point comment. |
| **Nit** | A cosmetic/surface-level fix (typo, import order, naming) that cannot break functionality. |
| **Blocking Issue** | A defect that causes incorrect behavior, security vulnerability, or data loss in production. |
| **Signal Phrase** | "Need a second opinion" — indicates discomfort pushing back, requests Decision Maker intervention without explicit escalation. |

## Unified Review Pipeline

All validation, classification, and implementation logic flow through a single pipeline. No logic is duplicated across stages.

```
BEGIN REVIEW_PIPELINE
    /* ═══════════════════════════════════════════
       Phase 1: INTAKE — Read, Parse, Validate
       ═══════════════════════════════════════════ */

    IF no review feedback items provided:
        FAIL: "[review-intake] No review feedback to process. Request a review first."

    /* Parse multi-point comments into individual items */
    FOR EACH review comment:
        IF comment contains multiple distinct points:
            SPLIT into separate feedback items
            MARK with source comment ID for traceability

    /* Validate references */
    FOR EACH feedback item:
        IF item references file:line:
            IF file does NOT exist:
                MARK item as UNACTIONABLE, reason: "file not found"
            ELSE IF line out of range:
                MARK item as UNACTIONABLE, reason: "stale location (line {line}, file has {actual_lines})"
        IF item has NO specific target (no file, no function, no test):
            MARK item as AMBIGUOUS, reason: "no actionable target identified"

    /* ═══════════════════════════════════════════
       Phase 2: DEDUPLICATE — Merge redundant items
       ═══════════════════════════════════════════ */

    FOR EACH pair of feedback items (A, B):
        IF A and B describe the same concern in different words:
            MERGE into single item
            RETAIN more specific/specific version
            RECORD: "Merged items from [A.source] and [B.source] — same concern"

    /* ═══════════════════════════════════════════
       Phase 3: CLASSIFY — Type determines strategy
       ═══════════════════════════════════════════ */

    FOR EACH actionable feedback item:
        /* Intent analysis: literal suggestion vs underlying concern */
        item.literal = what reviewer explicitly asked for
        item.intent = why reviewer raised this (the underlying problem)

        /* Classification */
        IF item identifies incorrect behavior, security flaw, or data loss:
            item.type = BLOCKING
            item.strategy = "fix root cause immediately"
        IF item identifies stylistic, naming, import order, or formatting issue:
            item.type = NIT
            item.strategy = "batch fix, minimal verification"
        IF item suggests structural change (refactor, rename module, change patterns):
            item.type = ARCHITECTURE
            item.strategy = "evaluate scope impact before implementing"
        IF item requests new functionality not in original scope:
            item.type = SCOPE_CREEP
            item.strategy = "YAGNI check → defer to Decision Maker if used"
        IF item is a question, not a directive:
            item.type = QUESTION
            item.strategy = "answer directly, no code change needed"

        /* Verify: does the literal suggestion address the intent? */
        IF item.literal does NOT address item.intent:
            ANNOTATE: "Reviewer asked for {literal}, but underlying concern is {intent}. Consider addressing intent instead."
            /* Example: reviewer says "add a comment" but intent is "this code is unreadable".
               Fix: rename variables + simplify logic (addresses intent).
               Not: add a comment (addresses literal only). */

    /* ═══════════════════════════════════════════
       Phase 4: CONFLICT DETECTION — Contradictory feedback
       ═══════════════════════════════════════════ */

    FOR EACH pair of actionable items (A, B):
        IF A suggests X and B suggests NOT-X (same concern, opposite direction):
            MARK both as CONFLICT
            DO NOT implement either
            PRESENT to Decision Maker: "Items {A.id} and {B.id} conflict: {A.literal} vs {B.literal}. Which direction?"

        IF A and B target same code region with incompatible approaches:
            MARK both as CONFLICT
            PRESENT to Decision Maker: "Items {A.id} and {B.id} compete for same code region. Recommend {preferred} because {reason}. Approve?"

    /* ═══════════════════════════════════════════
       Phase 5: EVALUATE — Technical soundness check
       ═══════════════════════════════════════════ */

    FOR EACH actionable, non-conflicting item:
        /* Source-aware evaluation */
        IF item source is Decision Maker:
            trust_level = TRUSTED
            /* Still verify scope clarity, but assume technical intent is correct */
        IF item source is external reviewer:
            trust_level = SKEPTICAL
            /* Full technical verification required */

        /* Technical verification (all sources) */
        verify_results = {
            technically_correct: CHECK "Is this suggestion correct for this codebase/stack?",
            breaks_existing:     CHECK "Does implementing this break existing functionality?",
            reason_current:      CHECK "Why is the current implementation this way? (check git blame, comments, tests)",
            cross_platform:      CHECK "Does this work on all target platforms/versions?",
            reviewer_context:    CHECK "Does the reviewer have full context? (e.g., only saw diff, not full file)"
        }

        /* Decision branching */
        IF verify_results.technically_correct AND NOT verify_results.breaks_existing:
            item.verdict = ACCEPT
        IF verify_results.breaks_existing:
            item.verdict = PUSH_BACK, reason: "Breaks {specific functionality}"
            item.evidence = reference to breaking test/behavior
        IF NOT verify_results.technically_correct:
            item.verdict = PUSH_BACK, reason: "Incorrect for {stack/version/constraint}"
            item.evidence = technical explanation
        IF NOT verify_results.reviewer_context:
            item.verdict = PUSH_BACK, reason: "Reviewer lacks context: {missing context}"
            item.evidence = what reviewer didn't see
        IF verify_results.reason_current reveals deliberate choice:
            item.verdict = PUSH_BACK, reason: "Current impl is intentional: {reason} (see {commit/file})"
            item.evidence = git blame or code comment
        IF item.type == SCOPE_CREEP:
            GREP codebase for actual usage of suggested feature
            IF unused:
                item.verdict = PUSH_BACK, reason: "YAGNI — this feature has zero usage in codebase"
            IF used:
                item.verdict = DEFER, reason: "Valid usage found, but outside current scope. Defer to Decision Maker."
        IF cannot fully verify:
            item.verdict = NEEDS_INVESTIGATION
            STATE: "Cannot verify without {X}. Investigate before implementing?"

        /* Conflict with Decision Maker's prior decisions */
        IF item contradicts Decision Maker's established direction:
            item.verdict = ESCALATE
            PRESENT to Decision Maker: "Item {id} conflicts with prior decision: {decision}. Resolve?"

    /* ═══════════════════════════════════════════
       Phase 6: CLARIFY — Resolve ambiguity before ANY implementation
       ═══════════════════════════════════════════ */

    ambiguous_items = items with verdict AMBIGUOUS or NEEDS_INVESTIGATION
    conflict_items = items with verdict CONFLICT or ESCALATE

    IF ambiguous_items OR conflict_items:
        STOP — do NOT implement ANY item
        /* WHY: Items may be related. Partial understanding = wrong implementation. */
        PRESENT all ambiguous/conflict items with specific questions
        WAIT for resolution

    /* ═══════════════════════════════════════════
       Phase 7: IMPLEMENT — Ordered, tested, verified
       ═══════════════════════════════════════════ */

    /* Build implementation queue */
    queue = []
    APPEND to queue: all BLOCKING items (sorted by severity: security > data_loss > incorrect_behavior)
    APPEND to queue: all NIT items (batched together)
    APPEND to queue: all ARCHITECTURE items (sorted by dependency: foundation changes first)
    /* QUESTION items: already answered in Phase 3, no implementation needed */
    /* SCOPE_CREEP items: already handled in Phase 5, no implementation unless Decision Maker approved */

    FOR EACH item IN queue:
        /* Implementation */
        IF item.type == NIT AND multiple NITs in queue:
            IMPLEMENT all NITs as a single batch
            RUN: linter/formatter on modified files
            VERIFY: no functional regressions (smoke test)
        ELSE:
            IMPLEMENT fix targeting item.intent (not just item.literal, when they differ)
            TEST individually (targeted test for the specific fix)
            VERIFY no regressions (relevant test suite section)

    /* ═══════════════════════════════════════════
       Phase 8: VERIFY — Post-implementation gate
       ═══════════════════════════════════════════ */

    RUN: full test suite on all modified files
    IF any test fails:
        IDENTIFY: which implementation caused the regression
        IF regression from a PUSH_BACK item that was overridden:
            RE-PUSH_BACK with new evidence: "Implementing this suggestion caused regression: {test}"
        IF regression from own implementation:
            FIX the implementation (not the test, unless test was wrong)
    ELSE:
        MARK: "All feedback items processed, verification passed"
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

## Feedback Classification Reference

| Type | Indicators | Strategy | Verification Level |
|------|-----------|----------|--------------------|
| **BLOCKING** | "crashes", "security", "data loss", "wrong result", failing test | Fix root cause immediately | Full: targeted test + regression suite |
| **NIT** | "typo", "import order", "naming", "formatting", trailing whitespace | Batch fix, minimal verification | Linter only + smoke test |
| **ARCHITECTURE** | "refactor", "restructure", "move to", "change pattern", "extract" | Evaluate scope impact first | Design review + full test suite |
| **SCOPE_CREEP** | "also add", "while you're at it", "it would be nice", "properly implement" | YAGNI check → defer if used | Depends on Decision Maker outcome |
| **QUESTION** | "why does", "how come", "what if", genuine "?" | Answer directly, no code change | N/A |

## YAGNI Check (Broadened)

Trigger on ANY suggestion that adds new functionality, not just "implementing properly":

```
BEGIN YAGNI_CHECK
    IF item.type == SCOPE_CREEP OR
       item adds new function/class/module not replacing existing one OR
       item says "while you're at it" / "also" / "it would be nice" / "properly" OR
       item scope exceeds original task boundaries:

        GREP codebase for actual usage/callers of the suggested feature
        IF zero usage found:
            PUSH_BACK: "YAGNI — no code in the codebase calls or references this. Remove it?"
        IF usage found:
            DEFER to Decision Maker: "Usage exists ({callers}), but this is beyond current scope. Add to backlog?"
END
```

**Decision Maker's rule:** "If we don't need this feature right now, don't add it."

## When To Push Back

Push back when:
- Suggestion breaks existing functionality (with test evidence)
- Reviewer lacks full context (only saw diff, not full file/module)
- Violates YAGNI (unused feature with no callers)
- Technically incorrect for this stack/version/constraint
- Legacy/compatibility reasons exist (check git blame for why current impl exists)
- Conflicts with Decision Maker's architectural decisions

**How to push back:**
- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Cite the constraint or version requirement
- Involve Decision Maker if architectural

**Signal phrase:** "Need a second opinion on this" — indicates discomfort pushing back, requests Decision Maker intervention without explicit escalation.

## Acknowledging Correct Feedback

```
BEGIN ACKNOWLEDGE_CORRECT
    WHEN feedback IS correct:
        OUTPUT ONE OF:
            "Fixed. [Brief description of what changed]"
            "Good catch — [specific issue]. Fixed in [location]."
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
BEGIN CORRECT_PUSHPACK
    IF you pushed back and were wrong:
        OUTPUT ONE OF:
            "Checked [X] and it does [Y]. Implementing now."
            "Verified — my initial understanding was wrong because [reason]. Fixing."
    NEVER:
        Long apology
        Defending why you pushed back
        Over-explaining
    /* State the correction factually and move on. */
END
```

## GitHub Thread Protocol

When replying to inline review comments on GitHub:

**Reply mechanics:**
- Reply in the comment thread (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), not as a top-level PR comment
- One reply per feedback item, even if multiple items came from one comment

**Conversation lifecycle:**
```
BEGIN GITHUB_CONVERSATION
    IF item.verdict == ACCEPT and implemented:
        Reply: "Fixed in {commit_sha}. {brief description}"
        Resolve conversation: ✅

    IF item.verdict == PUSH_BACK:
        Reply: "Pushing back because {technical reason}. {evidence/reference}"
        Do NOT resolve conversation — leave for reviewer response

    IF item.verdict == DEFER:
        Reply: "Valid point, but outside current scope. Tracking in {issue/link}."
        Resolve conversation: ✅ (with acknowledgement)

    IF item.verdict == NEEDS_INVESTIGATION:
        Reply: "Need to verify {X} before proceeding. Investigating."
        Do NOT resolve conversation

    IF item.type == QUESTION:
        Reply: direct answer
        Resolve if satisfied, otherwise leave open
END
```

**PR review action after processing all items:**
- All ACCEPT → Approve PR (if you have review permissions)
- Any PUSH_BACK remaining → Comment with summary, do NOT approve
- Any DEFER → Approve with comment listing deferred items

## Implementation Order (Precise)

```
BEGIN IMPLEMENTATION_ORDER
    /* Priority tiers — process top-to-bottom, never reorder */

    TIER 1 — BLOCKING (security vulnerabilities, data loss, crashes)
        Sort: security > data_loss > incorrect_behavior
        Strategy: implement individually, test each, verify before moving to next

    TIER 2 — NIT (cosmetic, non-functional)
        Strategy: batch ALL nits together, single commit
        Verify: linter + smoke test only

    TIER 3 — ARCHITECTURE (structural changes)
        Sort: foundation changes before dependent changes
        /* If item A renames a module and item B updates callers, A before B */
        Strategy: implement individually, full test suite after each

    /* Dependency-aware ordering within tiers */
    IF item A is a prerequisite for item B:
        A must be implemented before B, even if B is higher tier
        /* Exception: security fixes are always Tier 1 regardless of deps */

    /* After all items: */
    RUN full test suite
    COMMIT with structured message referencing feedback items
END
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State requirement or just act |
| Blind implementation | Verify against codebase first |
| Batch without testing | One at a time (except NITS), test each |
| Assuming reviewer is right | Check if breaks things — trust level matters |
| Avoiding pushback | Technical correctness > comfort |
| Partial implementation on unclear items | STOP everything, clarify ALL items first |
| Can't verify, proceed anyway | State limitation, ask for direction |
| Fixing literal suggestion, missing intent | Ask: "Why did they raise this?" before implementing |
| Ignoring contradictory feedback | Detect conflicts, escalate both, implement neither |
| Treating scope creep as blocking | YAGNI check first, defer if valid but out of scope |
| Implementing nits individually | Batch nits — they're cheap but waste commits individually |
| Answering questions with code changes | Questions need answers, not implementations |

## Real Examples

### Performative Agreement (Bad)
```
Reviewer: "Remove legacy code"
❌ "You're absolutely right! Let me remove that..."
```

### Technical Verification (Good)
```
Reviewer: "Remove legacy code"
✅ "Checking... build target is 10.15+, this API needs 13+. Need legacy for backward compat. Current impl has wrong bundle ID — fix it or drop pre-13 support?"
```

### YAGNI (Good)
```
Reviewer: "Implement proper metrics tracking with database, date filters, CSV export"
✅ "Grepped codebase — nothing calls this endpoint. Remove it (YAGNI)? Or is there usage I'm missing?"
```

### Unclear Item (Good)
```
Decision Maker: "Fix items 1-6"
You understand 1,2,3,6. Unclear on 4,5.
✅ "Understand 1,2,3,6. Need clarification on 4 and 5 before implementing."
```

### Intent vs Literal (Good)
```
Reviewer: "Add a comment explaining this regex"
Literal: add comment
Intent: regex is hard to understand

❌ Add comment: // This regex matches email addresses
✅ Replace regex with named capture groups + helper function, making comment unnecessary
   "The regex was the problem, not the lack of comments. Extracted to isVerifiedEmail() with readable groups."
```

### Wrong Pushback (Bad)
```
Reviewer: "This function should handle null input"
You push back: "It can't be null, the caller always passes a value"
❌ Defend your pushback, argue, write a long justification
✅ "Checked — null can reach here via the API boundary handler. Implementing null check now."
```

### Conflicting Feedback (Good)
```
Reviewer A: "Make this async with promises"
Reviewer B: "Keep it synchronous, simpler is better"
✅ "Items 3 and 7 conflict (async vs sync). The sync version is used by 12 callers that expect return values. Async would require changing all callers. Recommend keeping sync. Thoughts?"
```

## Completion Contract

After processing all review feedback items:

```
BEGIN COMPLETION_CONTRACT
    COUNT total_items     = number of feedback items received (after parsing/splitting)
    COUNT implemented     = items with code changes made
    COUNT pushed_back     = items rejected with technical reasoning
    COUNT deferred        = items valid but outside current scope, deferred to later
    COUNT unactionable    = items with stale locations or no actionable target
    COUNT escalated       = items needing Decision Maker resolution

    IF pushed_back > 0:
        PRESENT: list of pushed-back items with reasoning and evidence

    IF deferred > 0:
        PRESENT: list of deferred items with tracking reference (issue link or backlog note)

    IF escalated > 0:
        PRESENT: list of escalated items requiring Decision Maker decision

    IF unactionable > 0:
        PRESENT: list of unactionable items with reason

    WRITE structured result for caller:
        {
            "status": "complete|blocked",
            "blocked_reason": "escalated items require Decision Maker input",
            "total_items": total_items,
            "implemented": implemented,
            "pushed_back": pushed_back,
            "deferred": deferred,
            "escalated": escalated,
            "unactionable": unactionable,
            "changes": ["<list of modified files>"],
            "regression_check": {
                "command": "<exact test command run>",
                "result": "pass|fail",
                "failures": ["<failing tests if any>"]
            }
        }
END
```

Callers use this result to decide whether to proceed to the next task/batch or re-review. Status "blocked" means escalated items must be resolved before the work is considered complete.

## Review Pacing

Don't rush through feedback items. Quality over speed:

- **Read all items first** — don't start implementing after the first item
- **Process in order** — but be willing to reorder if dependencies emerge
- **One context switch per tier** — don't alternate between blocking fixes and nits
- **Pause after pushback** — give the reviewer/Decision Maker time to respond before proceeding to other items that depend on the same code

## Integration

**Called by:**
- **review-request** (Step 3) — after reviewer subagent returns feedback. review-request dispatches the reviewer; review-intake evaluates and acts on the feedback.
- Any workflow receiving code review comments from external reviewers

**Should integrate with:**
- **verify-gate** — after implementation, run verification gate before marking complete
- **branch-landing** — after all feedback is processed and verified, use branch-landing to decide integration strategy

**Does NOT call other skills directly** — review-intake is a terminal processing step. It returns control to the caller (review-request) after all feedback items are processed.
