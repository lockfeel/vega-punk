---
name: test-first
description: "Test-Driven Development: write test first, watch it fail, write minimal code to pass. 做什么：TDD 红绿重构循环。何时用：任何新功能、bug修复、重构之前。触发词: TDD, test-driven, write test first, red-green-refactor, implement feature, bug fix, refactoring, 先写测试, 测试驱动"
categories: ["code-quality"]
triggers: ["TDD", "test-driven", "write test first", "red-green-refactor", "implement feature", "bug fix", "refactoring", "先写测试", "测试驱动"]
user-invocable: true
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't verify the test fails before implementing, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: a feature, behavior, or bug to address */
    IF no target behavior described:
        FAIL: "[test-first] No behavior specified. Cannot write tests without a target."
        EXIT

    /* Check if test framework is available */
    CHECK project for test framework:
        Node.js: jest/vitest/mocha in package.json devDependencies
        Python: pytest/unittest in pyproject.toml or requirements
        Rust: cargo test (built-in)
        Go: go test (built-in)
    IF no test framework found:
        TELL: "[test-first] No test framework detected in project."
        ASK: "Install test framework or skip TDD for this task?"

    /* Determine starting state — 3 scenarios */
    CASE new feature (target files empty or don't exist):
        PROCEED to TDD cycle (RED first)

    CASE existing untested code:
        /* Don't blindly delete — preserve work with characterization tests first */
        WRITE characterization tests for existing behavior (run them, they should pass)
        THEN refactor using TDD cycle (change one behavior at a time)
        LOG: "[test-first] Existing code found. Wrote characterization tests before modifying."

    CASE existing code with passing tests:
        /* Tests already cover this area — extend or refactor safely */
        CHECK: do existing tests cover the NEW behavior?
        IF yes AND tests pass:
            TELL: "[test-first] Tests for this behavior already exist and pass."
            ASK: "Is this a new behavior (add more tests) or refactoring (existing tests should still pass)?"
        IF no:
            PROCEED to TDD cycle for the uncovered new behavior
END
```

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask your human partner):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Don't keep it as "reference." Don't "adapt" it while writing tests. Implement fresh from tests. Period.

**Safety before deletion:** If you encounter pre-existing implementation code without tests:
1. **Commit or stash current state first** (never delete without a recovery point)
2. Write characterization tests for what exists
3. Then refactor/modify using TDD
Never delete uncommitted work without preserving it somewhere first.

**Structured alternatives when pure TDD isn't feasible:**
- **Legacy code without tests:** Write characterization tests first (record what it does, not what it should do), then refactor with TDD
- **Emergency hotfix:** Fix first, but write the regression test immediately after — flag as TECHNICAL DEBT in commit message
- **Exploratory spike:** Fine to explore. Throw away the spike code. Start implementation with TDD.

All alternatives require asking your human partner first.

## Test File Location

Before writing tests, determine where they go:

```
BEGIN LOCATE_TEST_FILE
    /* Follow existing project conventions — check what's already there */
    IF project uses co-located tests (Component.test.ts next to Component.ts):
        USE same pattern
    IF project uses dedicated test directories (__tests__/, tests/, test/):
        USE same directory structure
    IF no existing pattern:
        ASK human partner for preference
        DEFAULT: co-located test files (*.test.<ext> or *_test.<ext> next to source)

    /* Test file naming by language */
    TypeScript/JavaScript: *.test.ts / *.test.js or *.spec.ts / *.spec.js
    Python: test_*.py or *_test.py
    Rust: tests stay in same file (#[cfg(test)]) or tests/ directory
    Go: *_test.go in same package
END
```

## Red-Green-Refactor

```
BEGIN TDD_CYCLE
    /* RED — Write Failing Test */
    WRITE one minimal test showing what should happen
    REQUIREMENTS:
        - One cohesive behavior (test name should describe a single observable outcome;
          "and" is a smell — split unless steps are an inseparable sequence, e.g.
          "creates user and sends welcome email" is OK as an integration test,
          but "validates email and handles whitespace" should be two tests)
        - Clear name describing behavior
        - Real code (follow mock hierarchy below)

    /* Mock hierarchy (prefer real → fake → mock) */
    1. Real implementation (always preferred)
    2. Fake implementation (in-memory database, test double with real logic)
    3. Mock/stub (ONLY for: external APIs, time-dependent code, network I/O,
       nondeterministic systems — things you cannot control in a test environment)
    IF you mock something controllable:
        REFACTOR to make it testable with real code instead

    /* Verify RED — Confirm Test Fails (MANDATORY, never skip) */
    RUN project test command for the new test only
    CONFIRM:
        IF test passes:
            FAIL: "Test passes without implementation. Either testing existing behavior or test is wrong."
            FIX test to fail for the right reason
        IF test errors (not fails — e.g., import error, syntax error):
            FIX error, re-run until test fails correctly (fails at assertion, not at setup)
        IF test fails with unexpected reason:
            FIX test to fail for expected reason (feature missing, not setup problem)
        IF test fails as expected:
            LOG: "[test-first] RED confirmed — test fails because: {failure message}"
            PROCEED to GREEN

    /* GREEN — Minimal Code */
    WRITE simplest code to make the test pass
    CONSTRAINTS:
        - Don't add features no test requires
        - Don't refactor other code
        - Don't "improve" beyond the test
        - Hardcoded values are OK if that's what makes the test pass

    EXAMPLE — Good vs Bad GREEN:
    ```typescript
    // ✅ Good: Just enough to pass
    async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
      for (let i = 0; i < 3; i++) {
        try { return await fn(); } catch (e) {
          if (i === 2) throw e;
        }
      }
      throw new Error('unreachable');
    }

    // ❌ Bad: Over-engineered (YAGNI — options, backoff, callbacks no test requires)
    async function retryOperation<T>(fn: () => Promise<T>, options?: {
      maxRetries?: number; backoff?: 'linear' | 'exponential';
      onRetry?: (attempt: number) => void;
    }): Promise<T> { /* ... */ }
    ```

    /* Verify GREEN — Confirm Test Passes (MANDATORY) */
    RUN full test suite
    CONFIRM:
        IF new test fails:
            FIX implementation code (NOT test), re-run
        IF other tests fail:
            FIX immediately — regression means your change broke something
        IF output has errors/warnings:
            FIX before proceeding
        IF all pass, output pristine:
            LOG: "[test-first] GREEN confirmed — all tests pass"
            PROCEED to REFACTOR

    /* REFACTOR — Clean Up (only after green) */
    IF duplication exists:
        Remove duplication
    IF naming is unclear:
        Improve names
    IF helpers can be extracted:
        Extract helpers
    CONSTRAINT: Keep tests green. Don't add behavior.

    /* Verify REFACTOR — Confirm Still Green (MANDATORY) */
    RUN full test suite
    CONFIRM:
        IF any test fails:
            REVERT refactor, try simpler approach
        IF all pass:
            LOG: "[test-first] REFACTOR verified — still green"
            EVALUATE completion (see Completion Criteria below)
END
```

## Completion Criteria

```
BEGIN COMPLETION_CRITERIA
    /* After each REFACTOR verification, check if TDD cycle should continue */
    ALL of the following must be true to exit the cycle:

    1. Every requirement from the task spec has a corresponding test
       (walk through spec line by line, check each has coverage)
    2. All edge cases identified during implementation are tested:
       - Empty input / null / undefined
       - Boundary values (0, MAX, MIN)
       - Error conditions (network failure, invalid input)
    3. All tests pass with pristine output (no errors, no warnings)
    4. No TODO/FIXME comments remaining in new code
    5. No test marked as skip or pending

    IF any criterion fails:
        GOTO RED (write next failing test for uncovered requirement)
    IF all criteria pass:
        EXIT cycle — implementation complete
END
```

## Good Tests

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One cohesive behavior. "and" between unrelated things? Split it. | `test('validates email and domain and whitespace')` |
| **Clear** | Name describes behavior | `test('test1')` |
| **Shows intent** | Demonstrates desired API | Obscures what code should do |
| **Real** | Tests actual code paths | Tests mock setup instead |

## Why Order Matters

**"I'll write tests after to verify"** — Tests written after code pass immediately, proving nothing. You never verified the test could catch the bug.

**"I already manually tested all edge cases"** — Manual testing is ad-hoc: no record, can't re-run, easy to forget. Automated tests are systematic.

**"Deleting X hours of work is wasteful"** — Sunk cost fallacy. The time is already gone. Choice: rewrite with TDD (high confidence) or keep untrusted code (technical debt).

**"TDD is dogmatic, being pragmatic means adapting"** — TDD IS pragmatic: finds bugs before commit, prevents regressions, documents behavior, enables refactoring.

**"Tests after achieve the same goals"** — No. Tests-after = "what does this do?" Tests-first = "what should this do?" Tests-after verify remembered edge cases. Tests-first force edge case discovery.

## Common Rationalizations

All of these reduce to: "just do TDD." If you catch yourself thinking any of these, stop and follow the cycle.

| Excuse → Reality |
|------------------|
| "Too simple to test" → Simple code breaks. Test takes 30 seconds. |
| "I'll test after" → Tests passing immediately prove nothing. |
| "Already manually tested" → Ad-hoc ≠ systematic. No record, can't re-run. |
| "Keep as reference" → You'll adapt it. That's testing after. |
| "Need to explore first" → Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" → Listen to test. Hard to test = hard to use. |
| "This is different because..." → It isn't. |

## Red Flags — STOP and Reassess

- Code before test
- Test passes immediately on RED
- Can't explain why test failed
- Rationalizing "just this once"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"

**Response:** If code exists without a test, write characterization tests first, then refactor with TDD. Never delete without preserving a recovery point.

## Example: Bug Fix

**Bug:** Empty email accepted

**RED**
```typescript
test('rejects empty email', async () => {
  const result = await submitForm({ email: '' });
  expect(result.error).toBe('Email required');
});
```

**Verify RED**
```bash
$ npm test
FAIL: expected 'Email required', got undefined
```

**GREEN**
```typescript
function submitForm(data: FormData) {
  if (!data.email?.trim()) {
    return { error: 'Email required' };
  }
}
```

**Verify GREEN**
```bash
$ npm test
PASS
```

**REFACTOR**
Extract validation for multiple fields if needed.

**Verify REFACTOR**
```bash
$ npm test
PASS (all tests still green)
```

## Example: Characterization Test (for existing code)

**Scenario:** You need to modify `parseConfig()` which has no tests.

```typescript
// Step 1: Write characterization test — records WHAT the code does (not what it should do)
test('parseConfig returns default port when not specified', () => {
  const result = parseConfig('host=localhost');
  expect(result.port).toBe(3000); // observed behavior, might not be "correct"
});

// Step 2: Run it — should PASS (we're recording existing behavior)
// Step 3: Now safely refactor or add new behavior via TDD
```

## Verification Checklist

```
BEGIN VERIFICATION_CHECKLIST
    FOR EACH new function/method:
        CHECK: has a test that covers it
        CHECK: test was run and confirmed to FAIL before implementation was written
        CHECK: test failed for the right reason (feature missing, not setup/import error)
        CHECK: wrote minimal code to pass (no extra features)
    CHECK: all tests pass (full suite)
    CHECK: output pristine (no errors, warnings)
    CHECK: mocks only used for uncontrollable dependencies (external APIs, time, network)
    CHECK: edge cases and error conditions covered
    CHECK: no skipped or pending tests
    CHECK: no TODO/FIXME in new code

    IF any check fails:
        FIX the issue — do not proceed until checklist is fully green
END
```

## When Stuck

```
BEGIN WHEN_STUCK
    CASE don't know how to test:
        WRITE wished-for API first → write assertion against it → ask human partner if stuck

    CASE test too complicated:
        DESIGN is too complicated → simplify the interface → then test the simpler interface

    CASE must mock everything:
        CODE is too coupled → use dependency injection → then test with real/fake dependencies

    CASE test setup huge:
        EXTRACT test helpers → still complex? → simplify design (code tells you it's wrong)

    CASE can't make test fail correctly:
        Test may be testing wrong thing → re-read requirement → rewrite test for observable behavior
END
```

## Debugging Integration

Bug found? Write failing test reproducing it. Follow TDD cycle. Test proves fix and prevents regression.

Never fix bugs without a test.

## Testing Anti-Patterns

Avoid these common pitfalls:
- Testing mock behavior instead of real behavior (if your assertion checks mock.callCount instead of actual output, the test proves nothing about real code)
- Adding test-only methods to production classes (if you need `setInternalState()` only for tests, the class is too coupled — refactor instead)
- Mocking without understanding dependencies (if you mock a dependency you don't understand, your mock may not match real behavior — read the dependency first)
- Testing implementation details (private methods, internal state) instead of public behavior

## Language Note

All examples use TypeScript for readability, but TDD patterns are language-agnostic:

| Pattern | TypeScript | Python | Go | Rust |
|---------|-----------|--------|-----|------|
| Test file | `*.test.ts` | `test_*.py` | `*_test.go` | `#[cfg(test)]` inline or `tests/` |
| Run command | `npm test` | `pytest` | `go test ./...` | `cargo test` |
| Assert style | `expect(x).toBe(y)` | `assert x == y` | `if got != want { t.Error(...) }` | `assert_eq!(got, want)` |
| Mock library | jest/vitest mocks | unittest.mock | interfaces + fakes | trait objects + fakes |

Follow your project's existing conventions when they exist.

## Integration

**Used by other skills:**
- `task-dispatcher` — injects test-first discipline into implementer prompts for feature/refactor tasks
- `root-cause` — uses test-first for bug fix verification (write failing test that reproduces bug)
- `verify-gate` — runs the test suite this skill creates to confirm mechanical soundness

**When used as injected discipline (e.g., by task-dispatcher):**
- The parent skill provides task context, target files, and spec requirements
- You apply TDD cycle within those constraints
- Report status back via the parent skill's mechanism (e.g., `.task-status-*.json`)

**When working in a worktree:**
- All test and implementation files are written to the worktree path, not the main repo
- Run test commands from the worktree root directory
- The worktree shares the git history, so existing tests are available

## Final Rule

```
Production code → test exists and was confirmed to fail first
Otherwise → not TDD
```

No exceptions without your human partner's permission.
