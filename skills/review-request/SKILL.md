---
name: review-request
description: "Dispatch code-reviewer subagent to catch issues before they cascade. 做什么：代码审查调度 + 两阶段review（spec合规→代码质量）。何时用：完成任务后、合并前。触发词: code review, review my code, before merge, 代码审查, 检查一下代码, check code quality"
categories: ["code-quality"]
triggers: ["code review", "review my code", "request review", "before merge", "check code quality", "代码审查", "检查一下代码"]
user-invocable: true
---

# Requesting Code Review

Dispatch `code-reviewer` subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often. Dispatch clearly, hand off completely.

**Responsibility boundary:**
- review-request OWNS: dispatching the reviewer, crafting the review prompt, managing subagent lifecycle
- review-request DOES NOT OWN: evaluating feedback, implementing fixes, pushback — that is review-intake's job

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Unified Review Pipeline

All logic flows through a single pipeline. No SHA computation or lifecycle steps are duplicated.

```
BEGIN REVIEW_PIPELINE
    /* ═══════════════════════════════════════════
       Phase 1: PRE-FLIGHT — Validate prerequisites
       ═══════════════════════════════════════════ */

    IF not inside a git repository:
        FAIL: "[review-request] Not in a git repository. Cannot request review."

    /* Compute git range (computed once, used throughout) */
    BASE_SHA = git merge-base HEAD main 2>/dev/null
               || git merge-base HEAD master 2>/dev/null
               || git rev-list --max-parents=0 HEAD
    HEAD_SHA = git rev-parse HEAD

    IF BASE_SHA not found AND HEAD_SHA not found:
        FAIL: "[review-request] No commits to review. Nothing changed."

    IF BASE_SHA == HEAD_SHA:
        FAIL: "[review-request] No changes between base and HEAD. Nothing to review."

    /* Compute diff stats (used for scope decision + reviewer prompt) */
    changed_files = git diff --stat BASE_SHA..HEAD_SHA
    changed_lines = git diff --shortstat BASE_SHA..HEAD_SHA

    IF changed_files is empty:
        FAIL: "[review-request] No file changes detected. Nothing to review."

    /* ═══════════════════════════════════════════
       Phase 2: SCOPE — Determine review depth and focus
       ═══════════════════════════════════════════ */

    file_count = count of changed files
    line_count = total insertions + deletions from changed_lines

    /* Scope classification (dual axis: files AND lines) */
    IF file_count <= 3 AND line_count <= 100:
        review_scope = "focused"
    ELIF file_count <= 10 AND line_count <= 500:
        review_scope = "feature"
    ELIF file_count <= 20 AND line_count <= 2000:
        review_scope = "comprehensive"
    ELSE:
        review_scope = "split_recommended"
        WARN: "[review-request] Large diff ({file_count} files, {line_count} lines). Consider splitting into focused reviews."

    /* Focus area selection */
    /* Default: review all areas. Override based on situation. */
    focus_areas = ["correctness", "security", "architecture", "readability", "testing"]

    IF situation is "bug fix":
        focus_areas = ["correctness", "testing", "security"]
    IF situation is "security-sensitive":
        focus_areas = ["security", "correctness", "testing"]
    IF situation is "refactoring":
        focus_areas = ["architecture", "correctness", "readability"]
    IF situation is "pre-merge":
        focus_areas = ["correctness", "security", "architecture", "testing", "readability"]

    /* ═══════════════════════════════════════════
       Phase 3: CONTEXT — Gather what the reviewer needs
       ═══════════════════════════════════════════ */

    IF ~/.vega-punk/vega-punk-state.json exists:
        LOAD spec_path, requirements.success, design from state
    ELSE:
        /* Standalone mode — use git commit messages as context */
        context = git log BASE_SHA..HEAD_SHA --oneline

    /* Validate reviewer template */
    IF review-request/code-reviewer.md does NOT exist:
        WARN: "[review-request] Reviewer template missing. Using inline review criteria from this skill."

    /* ═══════════════════════════════════════════
       Phase 4: DISPATCH — Launch code-reviewer subagent
       ═══════════════════════════════════════════ */

    /* Construct reviewer prompt from template */
    reviewer_prompt = BUILD_PROMPT(
        what_was_implemented: <what was built>,
        plan_or_requirements: <spec/requirements reference>,
        base_sha: BASE_SHA,
        head_sha: HEAD_SHA,
        scope: review_scope,
        focus_areas: focus_areas,
        changed_files: changed_files,
        description: <summary with design decisions>
    )

    /* Dispatch with full specification */
    DISPATCH code-reviewer subagent with:
        prompt: reviewer_prompt
        isolation: "worktree"
        /* Rationale: reviewer needs read-only access to code. Worktree prevents
           any accidental modification to working directory. */
        timeout: {
            focused: "5m",
            feature: "10m",
            comprehensive: "15m",
            split_recommended: "10m per review"
        }[review_scope]

    RECORD subagent reference in dispatch table:
        {
            "task": "code-review",
            "scope": review_scope,
            "focus": focus_areas,
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "agent_ref": "<platform-native identifier>",
            "dispatched_at": "<timestamp>"
        }

    /* ═══════════════════════════════════════════
       Phase 5: RECEIVE — Handle reviewer results
       ═══════════════════════════════════════════ */

    /* Handle reviewer failure */
    IF subagent status is TIMEOUT:
        ASK: "Reviewer timed out. Re-dispatch with narrower scope ({review_scope} → focused on {focus_areas[0]})? Or proceed without review?"
    IF subagent status is FAILED:
        ASK: "Reviewer failed with error: {error}. Re-dispatch? Or proceed without review?"
    IF subagent returned incomplete results:
        ASK: "Review incomplete — only covered {returned_scope}. Accept partial review or re-dispatch?"

    /* Classify results for handoff to review-intake */
    IF subagent status is COMPLETE:
        review_result = {
            "status": classify_overall_status(subagent_findings),
            "findings": subagent_findings,
            "strengths": subagent_strengths,
            "scope_reviewed": review_scope,
            "focus_areas_reviewed": focus_areas
        }

        /* Overall status classification */
        IF any finding is security_vulnerability OR data_loss_risk:
            review_result.status = "critical"
        ELIF any finding is architectural_problem OR missing_error_handling OR test_gap:
            review_result.status = "important"
        ELIF any finding is style_or_naming_or_minor_optimization:
            review_result.status = "minor"
        ELSE:
            review_result.status = "passed"

    /* ═══════════════════════════════════════════
       Phase 6: HANDOFF — Transfer to review-intake
       ═══════════════════════════════════════════ */

    /* review-intake owns all feedback evaluation, pushback, and implementation */
    INVOKE review-intake via Skill tool
    PASS:
        review_result (from Phase 5)
        git diff context (BASE_SHA, HEAD_SHA, changed_files)
        spec/requirements (from Phase 3)
    WAIT for review-intake to complete

    /* ═══════════════════════════════════════════
       Phase 7: RE-REVIEW PROTOCOL — After fixes
       ═══════════════════════════════════════════ */

    IF review-intake fixed any Critical/BLOCKING items:
        /* Determine re-review scope */
        IF fix only touched files from original Critical findings:
            re_review_scope = "focused"
            re_review_base = HEAD_SHA_before_fixes
            re_review_head = git rev-parse HEAD
            /* Only review the fix + its immediate test files */
        ELIF fix touched additional files:
            re_review_scope = "feature"
            re_review_base = original BASE_SHA
            re_review_head = git rev-parse HEAD
            /* Re-review the full feature including the fix */

        RE-DISPATCH code-reviewer with:
            scope: re_review_scope
            base_sha: re_review_base
            head_sha: re_review_head
            focus_areas: ["correctness", "regression"]
            /* Narrower focus: only check the fix didn't introduce new issues */

        LOOP BACK to Phase 5 with re-review results
        /* Maximum 2 re-review cycles. After that, escalate to human. */

    /* ═══════════════════════════════════════════
       Phase 8: RECYCLE — Clean up subagent
       ═══════════════════════════════════════════ */

    LOOKUP agent_ref from dispatch table
    DEREGISTER/TERMINATE subagent
    CLEAR cached context/session data
    REMOVE entry from dispatch table
    LOG: "[review-request] code-reviewer subagent recycled."
END
```

## Boundary with verify-gate

| Skill | Checks | When to Run |
|-------|--------|-------------|
| **verify-gate** | *That* it works — tests pass/fail, build success, lint clean | BEFORE review-request |
| **review-request** | *How well* it's built — architecture, patterns, readability, correctness | AFTER verify-gate passes |

**Execution order:**
```
verify-gate (pass) → review-request → review-intake → verify-gate (re-verify if fixes made)
```

Do NOT run review-request before verify-gate. Reviewing code that doesn't compile or fails tests wastes the reviewer's time on noise.

## Checkpoint Protocol

| Checkpoint | Trigger | Action |
|------------|---------|--------|
| `LARGE_DIFF_WARN` | > 20 files or > 2000 lines changed | ASK: "Large diff — split into focused reviews or proceed with comprehensive?" |
| `SUBAGENT_TIMEOUT` | Reviewer exceeds timeout | ASK: re-dispatch narrower scope / proceed without review |
| `CRITICAL_FINDING` | Review finds security/data-loss issue | BLOCK progression, REQUIRE fix before continuing |
| `REVIEW_CYCLE_EXHAUSTED` | 2 re-review cycles without resolution | STOP, escalate disagreement summary to user |

## When to Request Review

**Mandatory:**
- After completing major feature
- Before merge to main
- AFTER verify-gate passes (not before)

**In task-dispatcher / plan-executor workflows:**
- Per-task spec compliance and code quality reviews are handled by the executor's two-stage review loop — **do NOT call review-request for individual tasks**
- Only invoke review-request at the **final pre-merge checkpoint** (after all tasks/steps complete, before branch-landing)

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug
- After security-sensitive changes

## Review Focus Areas

Configure what the reviewer should prioritize. Default is all areas; override per situation.

| Focus Area | What the Reviewer Checks | When to Prioritize |
|-----------|-------------------------|-------------------|
| **correctness** | Logic errors, off-by-one, null handling, edge cases | Always (default) |
| **security** | Input validation, auth checks, injection risks, data exposure | Security-sensitive features, API endpoints, auth flows |
| **architecture** | Separation of concerns, dependency direction, abstraction level | Refactoring, new modules, cross-cutting changes |
| **readability** | Naming, function length, comment quality, cognitive complexity | All reviews (lower priority for bug fixes) |
| **testing** | Test coverage, test quality, edge case coverage, test isolation | All reviews (higher priority for bug fixes) |

## Review Scope Decision

Dual-axis classification (files AND lines matter):

| Scope | File Count | Line Count | Reviewer Strategy |
|-------|-----------|------------|-------------------|
| **focused** | ≤ 3 | ≤ 100 | Deep line-by-line review of all changes |
| **feature** | ≤ 10 | ≤ 500 | Thematic review by module/concern |
| **comprehensive** | ≤ 20 | ≤ 2000 | Structured walkthrough with risk-prioritized areas |
| **split_recommended** | > 20 | > 2000 | Split into 2-3 focused reviews by subsystem |

**When splitting a large review:**
1. Group changed files by subsystem/module
2. Dispatch one reviewer per group
3. Each reviewer gets `scope: "focused"` for their group
4. Combine findings before passing to review-intake

## Reviewer Prompt Template

The prompt dispatched to the code-reviewer subagent follows this structure:

```markdown
## Review Request

### What Was Implemented
<1-2 sentences describing the feature/fix>

### Requirements
<Reference to spec, task, or requirements document>
<If standalone: bullet list of what the code should do>

### Git Range
- Base: {BASE_SHA}
- Head: {HEAD_SHA}
- Changed files: {file list with line counts}

### Scope
{focused|feature|comprehensive}

### Focus Areas
<prioritized list from Focus Areas table>

### Design Decisions
<Key decisions made and why>
<Known trade-offs or limitations>

### Review Criteria
Check for:
- [Focus area 1]: <specific things to verify>
- [Focus area 2]: <specific things to verify>
- ...

### What NOT to Review
<Areas explicitly out of scope>
<Files/patterns that are intentionally legacy>

### Expected Output
Return a structured review:
1. Summary: overall assessment (1-2 sentences)
2. Strengths: what's done well
3. Issues: list of {severity, file:line, description, suggested_fix}
4. Assessment: ready to proceed / needs fixes before proceeding
```

### Example: Focused Review (Bug Fix)

```markdown
## Review Request

### What Was Implemented
Fix for null pointer exception in UserService.verifyEmail() when email provider is unreachable.

### Requirements
Bug fix from Issue #142 — verifyEmail must handle network errors gracefully, returning false instead of crashing.

### Git Range
- Base: a7981ec
- Head: 3df7661
- Changed files: src/services/UserService.ts (+12 -3), src/services/UserService.test.ts (+28 -0)

### Scope
focused

### Focus Areas
1. correctness — verify null/network handling is complete
2. testing — verify edge cases are covered (timeout, DNS failure, 5xx response)
3. security — verify no credential leakage in error paths

### Design Decisions
Used exponential backoff (3 retries) instead of single retry, because email verification often fails transiently.

### Expected Output
Return a structured review:
1. Summary: overall assessment
2. Strengths: what's done well
3. Issues: list of {severity, file:line, description, suggested_fix}
4. Assessment: ready / needs fixes
```

### Example: Feature Review (New Module)

```markdown
## Review Request

### What Was Implemented
UserService with email validation, retry logic, and profile management.

### Requirements
Task 2 from ~/.vega-punk/roadmap.json — user registration with email verification and profile CRUD.

### Git Range
- Base: a7981ec
- Head: f7b3210
- Changed files: src/services/UserService.ts (+145 -0), src/services/UserService.test.ts (+210 -0), src/types/User.ts (+18 -0), src/api/routes/users.ts (+62 -0)

### Scope
feature

### Focus Areas
1. architecture — module boundaries, dependency direction
2. correctness — business logic, error handling, edge cases
3. testing — coverage completeness, test isolation
4. security — input validation, auth checks on routes
5. readability — naming, function length

### Design Decisions
- Used exponential backoff instead of linear retry (email services have variable response times)
- Repair returns a report rather than auto-fixing (some corruptions need human judgment)
- Profile updates use optimistic locking to prevent stale overwrites

### What NOT to Review
- src/api/routes/auth.ts (not part of this task, touched only for import reorganization)

### Expected Output
Return a structured review:
1. Summary: overall assessment
2. Strengths: what's done well
3. Issues: list of {severity, file:line, description, suggested_fix}
4. Assessment: ready / needs fixes
```

## Re-Review Protocol

After review-intake fixes Critical/BLOCKING items, a re-review may be needed:

| Fix Scope | Re-Review Range | Re-Review Focus | Max Cycles |
|-----------|----------------|-----------------|------------|
| Fix only touches files from original Critical findings | Fix commit only (HEAD~1..HEAD) | correctness, regression | 2 |
| Fix touches additional files beyond original findings | Full feature branch (original BASE_SHA..HEAD) | correctness, architecture, regression | 2 |
| Fix introduces new architectural changes | Full feature branch | Full review (all focus areas) | 2 |

**After 2 re-review cycles without resolution:**
- STOP re-dispatching
- SUMMARIZE: remaining disagreement in 1 paragraph each side
- ESCALATE to human for decision
- DO NOT loop indefinitely

## Subagent Dispatch Specification

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **isolation** | `worktree` | Reviewer needs read-only access; worktree prevents accidental modification |
| **timeout** | 5-15 min based on scope | See Phase 4 timeout table |
| **agent type** | `Code Reviewer` | Specialized for code review, not general-purpose |
| **prompt format** | Reviewer Prompt Template | Ensures consistent, complete context |
| **max concurrent** | 1 (normal) / 3 (split reviews) | Avoid reviewer contention on shared resources |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skip review because "it's simple" | Every merge gets reviewed — simplicity makes it fast, not skippable |
| Review before tests pass | Run verify-gate FIRST — reviewing broken code wastes time |
| Handling feedback in review-request | Hand off to review-intake — review-request dispatches, review-intake evaluates |
| Large diff without splitting | Use split_recommended scope — 3 focused reviews > 1 overwhelming review |
| No focus areas specified | Default covers all, but narrowing focus produces deeper review |
| Include thought process in reviewer prompt | Only include decisions and outcomes — reviewer evaluates the code, not your journey |
| Re-review full scope after small fix | Match re-review scope to fix scope — focused fix → focused re-review |
| Infinite review loops | 2 cycle max, then escalate — perfect is the enemy of merged |

## Red Flags (With Remediation)

| Red Flag | Why It's Bad | What To Do |
|----------|-------------|------------|
| Skip review for "simple" changes | Simple bugs cause production incidents | Even 1-file changes get focused review |
| Ignore Critical findings | Security/data loss risk | review-intake blocks until Critical is fixed |
| Proceed with unfixed Important findings | Architecture debt compounds | Fix before next task, or explicitly defer with tracking |
| Argue with valid technical feedback | Ego-driven, not engineering-driven | If pushback is warranted, review-intake handles it with evidence |
| Review code that doesn't compile | Reviewer wastes time on noise | verify-gate FIRST, then review-request |
| Dispatch reviewer without focus areas | Shallow review across all areas | Specify 2-3 focus areas for depth |
| No re-review after Critical fix | Fix may introduce new issues | Always re-review Critical fixes (focused scope) |

## Completion Contract

After the entire pipeline completes (including review-intake processing and any re-reviews):

```
BEGIN COMPLETION_CONTRACT
    review_intake_result = result from review-intake (Phase 6)
    re_review_count = number of re-review cycles performed

    WRITE structured result for caller:
        {
            "status": review_intake_result.status,
            /* "complete" = all feedback processed, "blocked" = escalated items pending */
            "initial_review": {
                "scope": review_scope,
                "focus_areas": focus_areas,
                "findings_count": <number of issues found>,
                "severity_distribution": { "critical": N, "important": N, "minor": N }
            },
            "re_reviews": re_review_count,
            "changes": review_intake_result.changes,
            "regression_check": review_intake_result.regression_check,
            "pushed_back": review_intake_result.pushed_back,
            "deferred": review_intake_result.deferred
        }

    /* Recycle subagent (final cleanup) */
    DEREGISTER the code-reviewer subagent
    CLEAR any cached context or session data
    LOG: "[review-request] Pipeline complete. Subagent recycled."
END
```

**How callers use the result:**
- `status: "complete"` → proceed to branch-landing
- `status: "blocked"` → resolve escalated items, then re-invoke review-request
- `pushed_back` or `deferred` items → tracked in backlog, not blocking current merge

## Integration

**Called by:**
- **task-dispatcher** (Step 4) — final pre-merge review after all task batches pass their per-task two-stage reviews
- **plan-executor** — final pre-merge review before branch-landing
- Any skill before making success claims about completed work

**Calls next:**
- **verify-gate** — should run BEFORE review-request (reviewing broken code wastes time)
- **review-intake** — invoked at Phase 6 to evaluate and act on review feedback. review-intake owns all feedback evaluation, pushback, and implementation. review-request only dispatches and hands off.
- **branch-landing** — after review completes successfully, use branch-landing to decide integration strategy

**Does NOT duplicate from review-intake:**
- Feedback evaluation, classification, and pushback → review-intake
- Implementation of fixes → review-intake
- Review loop negotiation → review-intake

See reviewer template at: review-request/code-reviewer.md
