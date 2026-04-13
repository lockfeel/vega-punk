---
name: review-request
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
categories: ["code-quality"]
triggers: ["code review", "review my code", "request review", "before merge", "check code quality"]
---

# Requesting Code Review

Dispatch `code-reviewer` subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations. 

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: git repository with commits to review */
    IF not inside a git repository:
        FAIL: "[review-request] Not in a git repository. Cannot request review."
        EXIT

    /* Determine git range */
    BASE_SHA = git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
    HEAD_SHA = git rev-parse HEAD

    IF BASE_SHA not found AND HEAD_SHA not found:
        FAIL: "[review-request] No commits to review. Nothing changed."
        EXIT

    IF BASE_SHA not found:
        /* Root commit — review all commits from beginning */
        BASE_SHA = git rev-list --max-parents=0 HEAD
        TELL: "[review-request] No base branch found. Reviewing all commits from root."

    /* Determine review scope */
    changed_files = git diff --stat BASE_SHA..HEAD_SHA
    IF changed_files is empty:
        FAIL: "[review-request] No file changes between BASE_SHA and HEAD_SHA. Nothing to review."
        EXIT

    /* Check for existing review artifacts */
    IF ~/.vega-punk/vega-punk-state.json exists:
        /* Load context for reviewer — spec, requirements, design */
        LOAD spec_path, requirements.success, design from state
    ELSE:
        /* Standalone mode — use git commit messages as context */
        context = git log BASE_SHA..HEAD_SHA --oneline

    /* Validate reviewer template exists */
    IF review-request/code-reviewer.md does NOT exist:
        TELL: "[review-request] Reviewer template missing. Using default review criteria."
END
```

**Boundary with verify-gate:**
- review-request: Qualitative code quality assessment — architecture, patterns, readability, best practices
- verify-gate: Command-level verification — tests pass/fail, build success, lint clean
- review-request checks *how well* it's built; verify-gate checks *that* it works
- Both are needed — neither replaces the other

## When to Request Review

**Mandatory:**
- After completing major feature
- Before merge to main

**In task-dispatcher / plan-executor workflows:**
- Per-task spec compliance and code quality reviews are handled by the executor's two-stage review loop — **do NOT call review-request for individual tasks**
- Only invoke review-request at the **final pre-merge checkpoint** (after all tasks/steps complete, before branch-landing)

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

```
BEGIN REQUEST_REVIEW
    /* Step 1: Get git SHAs */
    BASE_SHA = git merge-base HEAD main || git merge-base HEAD master || git rev-list --max-parents=0 HEAD || git rev-parse HEAD~1
    HEAD_SHA = git rev-parse HEAD

    /* Step 2: Dispatch code-reviewer subagent */
    DISPATCH code-reviewer subagent with:
        WHAT_WAS_IMPLEMENTED: <what you just built>
        PLAN_OR_REQUIREMENTS: <what it should do>
        BASE_SHA: <starting commit>
        HEAD_SHA: <ending commit>
        DESCRIPTION: <brief summary>
    RECORD subagent sessionKey in dispatch table

    /* Step 3: Act on feedback via review-intake */
    INVOKE review-intake via Skill tool
    /* review-intake handles: verify suggestions, push back on incorrect, implement valid fixes */
    WAIT for review-intake to complete

    /* Step 4: Recycle code-reviewer subagent */
    LOOKUP sessionKey from dispatch table
    DEREGISTER/TERMINATE subagent
    CLEAR cached context/session data
    REMOVE entry from dispatch table
    LOG: "[review-request] code-reviewer subagent recycled."
END
```

## Review Scope Decision

Different situations call for different review depth:

| Situation | Review Scope | What to Include |
|-----------|-------------|-----------------|
| Single small task | Focused | Only the files changed in this task |
| Multi-step feature | Full feature | All changes since feature branch start |
| Bug fix | Symptom + fix | The failing test + the fix code |
| Refactoring | Before + after | What changed and why, risk areas |
| Pre-merge | Complete | Everything on the branch vs. base |

**How to determine scope:**
1. `git diff --stat {BASE_SHA}..{HEAD_SHA}` — see what changed
2. If < 5 files → focused review
3. If 5-15 files → feature review
4. If > 15 files → consider splitting into multiple reviews

## Crafting the Review Request

A good review request gives the reviewer everything they need without overwhelming them:

**Essential context:**
- What was implemented (1-2 sentences)
- What requirements/spec it maps to
- Key design decisions made and why
- Known trade-offs or limitations

**What NOT to include:**
- Your internal thought process
- Dead-end approaches you tried
- Implementation history (that's what git log is for)
- Unrelated context from other tasks

**Example:**
```
WHAT_WAS_IMPLEMENTED: UserService with email validation and retry logic
PLAN_OR_REQUIREMENTS: Task 2 from ~/.vega-punk/roadmap.json — user registration with email verification
BASE_SHA: a7981ec
HEAD_SHA: 3df7661
DESCRIPTION: Created UserService class with validateEmail(), retryOperation(), and constructor.
             4 tests covering email validation, retry logic, and error handling.
             Design decision: Used exponential backoff instead of linear retry
             because email services have variable response times.
```

## Handling Review Results

```
BEGIN HANDLE_REVIEW_RESULTS
    FOR EACH issue by severity:

    CASE Critical (Must Fix):
        /* Bugs, security vulnerabilities, data loss risks */
        FIX immediately
        DO NOT proceed until fixed
        RE-REQUEST review after fix

    CASE Important (Should Fix):
        /* Architecture problems, missing error handling, test gaps */
        FIX before moving to next task
        NO re-review needed unless fix is complex

    CASE Minor (Nice to Have):
        /* Code style, naming, small optimizations */
        NOTE for later — don't fix now (YAGNI on polish)
        BATCH minor fixes at end of phase if desired
END
```

### When Reviewer Is Wrong

```
BEGIN PUSHBACK
    IF pushing back:
        MUST include technical reasoning with file:line evidence
        MUST NOT use: "I disagree" (vague), "It works fine" (working ≠ correct), "We can fix it later"
        VALID reasons: reviewer lacks context, breaks existing behavior (cite tests), YAGNI, conflicts with architecture
END
```

### Review Loop Limits

```
BEGIN REVIEW_LOOP_LIMITS
    IF reviewer and implementer disagree after 2 rounds:
        SUMMARIZE disagreement clearly (1 paragraph each side)
        PRESENT to human for decision
        DO NOT loop indefinitely — escalate early
END
```

## Review Cadence

**Task-dispatcher workflow:**
- Per-task reviews handled by dispatcher's two-stage review loop (spec compliance + code quality) — **not review-request**
- review-request invoked once at the end for final pre-merge review (all changes since branch start)

**Plan-executor workflow:**
- review-request invoked once at the end for final pre-merge review

**Ad-hoc development:**
- Review before merge
- Review when stuck (fresh perspective helps)
- Review after major refactoring

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch `code-reviewer` subagent]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from ~/.vega-punk/specs/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types.
               Design decision: Repair returns a report rather than auto-fixing,
               because some corruptions need human judgment.

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators — Important issue, must fix before next task]
[Note magic number for later — Minor, don't fix now]
[Continue to Task 3]
```

## Completion Contract

After review completes, hand off to review-intake for processing:

```
BEGIN COMPLETION_CONTRACT
    /* Summarize review results for review-intake */
    IF Critical issues found:
        PRESENT: list of Critical issues with file:line locations
        BLOCK: do not allow caller to proceed until fixed
        RETURN: { status: "failed", severity: "critical", issues: [...] }

    IF Important issues found:
        PRESENT: list of Important issues
        RECOMMEND: fix before next task
        RETURN: { status: "passed_with_concerns", severity: "important", issues: [...] }

    IF Minor issues found:
        PRESENT: summary of Minor issues
        RETURN: { status: "passed", severity: "minor", issues: [...] }

    IF no issues found:
        PRESENT: strengths observed
        RETURN: { status: "passed", severity: "none", strengths: [...] }

    /* Step 3: invoke review-intake */
    INVOKE review-intake via Skill tool
    PASS: review result, git diff context, and spec requirements
    WAIT for review-intake to complete

    /* Step 4: recycle subagent */
    DEREGISTER the code-reviewer subagent
    CLEAR any cached context or session data
    LOG: "[review-request] code-reviewer subagent recycled."
END
```

**How callers use the result:**
The result is passed to `review-intake` via Skill tool invocation. review-intake evaluates each item against codebase reality, implements valid fixes, and pushes back on incorrect ones. Callers wait for review-intake to complete before proceeding.

## Integration

**Called by:**
- **task-dispatcher** (Step 4) — final pre-merge review after all task batches pass their per-task two-stage reviews
- **plan-executor** — final pre-merge review before branch-landing
- Any skill before making success claims about completed work

**Calls next:**
- **review-intake** — invoked at Step 3 to evaluate and act on review feedback. review-intake handles the technical rigor; review-request handles the dispatching of the reviewer subagent.
- **Subagent recycling** — invoked at Step 4 after review-intake completes.

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback
- Loop more than 2 rounds without escalating

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: review-request/code-reviewer.md
