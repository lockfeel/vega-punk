---
name: test-first
description: Use when implementing any feature or bugfix, before writing implementation code
categories: ["code-quality"]
triggers: ["TDD", "test-driven", "write test first", "red-green-refactor", "implement feature", "bug fix", "refactoring"]
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

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

    /* Check for pre-existing implementation code (violates TDD) */
    IF target files already contain implementation for the feature:
        FAIL: "[test-first] Implementation code already exists for {target}. Delete it and start with TDD."
        EXIT

    /* Check for existing tests that already pass (means feature may exist) */
    IF existing tests cover the target behavior AND pass:
        TELL: "[test-first] Tests for this behavior already exist and pass."
        ASK: "Is this a new behavior (add more tests) or refactoring (existing tests should still pass)?"
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

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor

```
BEGIN TDD_CYCLE
    /* RED — Write Failing Test */
    WRITE one minimal test showing what should happen
    REQUIREMENTS:
        - One behavior (no "and" in test name — split if present)
        - Clear name describing behavior
        - Real code (no mocks unless unavoidable)

    EXAMPLE — Good vs Bad RED:
    ```typescript
    // ✅ Good: Clear name, tests real behavior, one thing
    test('retries failed operations 3 times', async () => {
      let attempts = 0;
      const operation = () => {
        attempts++;
        if (attempts < 3) throw new Error('fail');
        return 'success';
      };
      const result = await retryOperation(operation);
      expect(result).toBe('success');
      expect(attempts).toBe(3);
    });

    // ❌ Bad: Vague name, tests mock not code
    test('retry works', async () => {
      const mock = jest.fn()
        .mockRejectedValueOnce(new Error())
        .mockRejectedValueOnce(new Error())
        .mockResolvedValueOnce('success');
      await retryOperation(mock);
      expect(mock).toHaveBeenCalledTimes(3);
    });
    ```

    /* Verify RED — Watch It Fail (MANDATORY, never skip) */
    RUN project test command
    CONFIRM:
        IF test passes:
            FAIL: "You're testing existing behavior. Fix test or confirm this is a new behavior."
        IF test errors (not fails):
            FIX error, re-run until it fails correctly
        IF test fails with unexpected reason:
            FIX test to fail for expected reason
        IF test fails as expected:
            PROCEED to GREEN

    /* GREEN — Minimal Code */
    WRITE simplest code to make the test pass
    CONSTRAINTS:
        - Don't add features no test requires
        - Don't refactor other code
        - Don't "improve" beyond the test

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

    /* Verify GREEN — Watch It Pass (MANDATORY) */
    RUN same test command
    CONFIRM:
        IF test fails:
            FIX code (NOT test), re-run
        IF other tests fail:
            FIX immediately
        IF output has errors/warnings:
            FIX before proceeding
        IF all pass, output pristine:
            PROCEED to REFACTOR

    /* REFACTOR — Clean Up (only after green) */
    IF duplication exists:
        Remove duplication
    IF naming is unclear:
        Improve names
    IF helpers can be extracted:
        Extract helpers
    CONSTRAINT: Keep tests green. Don't add behavior.

    /* Repeat — Next failing test for next behavior */
    GOTO RED
END
```

## Good Tests

| Quality | Good | Bad |
|---------|------|-----|
| **Minimal** | One thing. "and" in name? Split it. | `test('validates email and domain and whitespace')` |
| **Clear** | Name describes behavior | `test('test1')` |
| **Shows intent** | Demonstrates desired API | Obscures what code should do |

## Why Order Matters

**"I'll write tests after to verify"** — Tests written after code pass immediately, proving nothing. You never saw the test catch the bug.

**"I already manually tested all edge cases"** — Manual testing is ad-hoc: no record, can't re-run, easy to forget. Automated tests are systematic.

**"Deleting X hours of work is wasteful"** — Sunk cost fallacy. The time is already gone. Choice: rewrite with TDD (high confidence) or keep untrusted code (technical debt).

**"TDD is dogmatic, being pragmatic means adapting"** — TDD IS pragmatic: finds bugs before commit, prevents regressions, documents behavior, enables refactoring.

**"Tests after achieve the same goals"** — No. Tests-after = "what does this do?" Tests-first = "what should this do?" Tests-after verify remembered edge cases. Tests-first force edge case discovery.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for existing code. |

## Red Flags - STOP and Start Over

- Code before test
- Test after implementation
- Test passes immediately
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

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

## Verification Checklist

```
BEGIN VERIFICATION_CHECKLIST
    FOR EACH new function/method:
        CHECK: has a test
        CHECK: watched test fail before implementing
        CHECK: test failed for expected reason (feature missing, not typo)
        CHECK: wrote minimal code to pass
    CHECK: all tests pass
    CHECK: output pristine (no errors, warnings)
    CHECK: tests use real code (mocks only if unavoidable)
    CHECK: edge cases and errors covered

    IF any check fails:
        FAIL: "You skipped TDD. Delete code. Start over."
END
```

## When Stuck

```
BEGIN WHEN_STUCK
    CASE don't know how to test:
        WRITE wished-for API → write assertion first → ask human partner

    CASE test too complicated:
        DESIGN too complicated → simplify interface

    CASE must mock everything:
        CODE too coupled → use dependency injection

    CASE test setup huge:
        EXTRACT helpers → still complex? → simplify design
END
```

## Debugging Integration

Bug found? Write failing test reproducing it. Follow TDD cycle. Test proves fix and prevents regression.

Never fix bugs without a test.

## Testing Anti-Patterns

When adding mocks or test utilities, read [testing-anti-patterns.md](testing-anti-patterns.md) to avoid common pitfalls:
- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without your human partner's permission.
