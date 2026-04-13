---
name: branch-landing
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
categories: ["workflow"]
triggers: ["implementation complete", "merge", "create PR", "finish development", "complete branch", "integrate work"]
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the branch-landing skill to complete this work."

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations. 

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Validate current branch state */
    current_branch = git branch --show-current

    IF current_branch is "main" OR "master":
        TELL: "[branch-landing] You're on {current_branch}. This is unusual."
        ASK: "Are you sure you want to complete from {current_branch}? This could affect the main branch."

    /* Try to find worktree_path */
    IF ~/.vega-punk/vega-punk-state.json exists:
        IF worktree_path field missing:
            /* Try to find worktree from git */
            worktree_path = git worktree list | grep current_branch | parse path
            IF worktree_path found:
                ADD worktree_path to ~/.vega-punk/vega-punk-state.json
                TELL: "[branch-landing] Found worktree at {worktree_path} via git."
            ELSE:
                /* Not in a worktree — might be inline execution */
                worktree_path = null
                TELL: "[branch-landing] No worktree found. Proceeding without cleanup."
        ELSE IF worktree_path directory does NOT exist:
            /* Worktree was removed — find from git */
            worktree_path = git worktree list | grep current_branch | parse path
            IF worktree_path found:
                UPDATE worktree_path in ~/.vega-punk/vega-punk-state.json
            ELSE:
                worktree_path = null
                TELL: "[branch-landing] Worktree was removed. Skipping cleanup."
    /* else: standalone mode — no state file */
END
```

## The Process

```
BEGIN BRANCH_LANDING_PROCESS
    /* Step 1: Verify Tests */
    AUTO-DETECT project test command (package.json, pyproject.toml, Cargo.toml, go.mod)
    RUN test command

    IF tests fail:
        REPORT: "Tests failing (<N> failures). Must fix before completing."
        STOP — do NOT proceed

    /* Step 1b: Summarize Changes */
    git diff --stat <base>..HEAD
    COUNT: files changed, lines added/removed
    IDENTIFY: new files, deleted files, modified files
    FLAG: any migration files, config changes, dependency updates

    /* Step 2: Determine Base Branch */
    base = git merge-base HEAD main || git merge-base HEAD master
    IF base NOT found:
        ASK: "This branch splits from main - is that correct?"

    /* Step 3: Present Options */
    OUTPUT exactly:
        "Implementation complete.
         Summary: <N> files changed, +<added>/-<removed> lines.
         Tests: all passing.

         What would you like to do?

         1. Merge back to <base-branch> locally
            — auto-verifies tests on merged result, rolls back if broken
         2. Push and create a Pull Request
            — preserves branch + worktree for iterative review
         3. Keep the branch as-is (I'll handle it later)
            — no changes, worktree stays available
         4. Discard this work
            — requires typed confirmation, irreversible

         Which option?"
    WAIT for user choice

    /* Step 4: Execute Choice */
    CASE 1 (Merge Locally):
        git checkout <base-branch>
        git pull
        git merge <feature-branch>

        /* Post-merge test verification + auto-fix */
        RUN test command on merged result

        IF tests fail:
            REPORT: "Merge succeeded but tests failed (<N> failures). Diagnosing..."
            COMPARE: are these new failures or pre-existing baseline failures?
                Check baseline failure count from worktree-setup / verify-gate records

            IF new failures (introduced by merge):
                DIAGNOSE root cause:
                    - Git merge conflict left markers? → check `git grep "<<<<<<\\|======\\|>>>>>>"`
                    - Missing file from merge? → check `git diff --name-status HEAD~1..HEAD`
                    - Dependency conflict? → check `package-lock.json` / `Gemfile.lock` changes
                    - Integration gap between feature and main? → check test error messages
                IF fixable automatically (conflict markers, missing import):
                    FIX the issue
                    RE-RUN test command
                    IF still failing:
                        REPORT: "Auto-fix didn't resolve all issues. Rolling back merge."
                        git merge --abort
                        TELL: "Merge rolled back. Options: (1) create PR for manual review, (2) keep branch as-is"
                        STOP
                ELSE:
                    REPORT: "Merge introduced test failures that require manual investigation."
                    git merge --abort
                    TELL: "Merge rolled back. Recommend creating PR for review instead."
                    STOP

            IF pre-existing failures (same count as baseline):
                TELL: "Tests fail but these are pre-existing issues, not caused by merge."
                RECORD: merge is clean, pre-existing failures unchanged

        IF tests pass:
            git branch -d <feature-branch>
        GOTO STEP 6

    CASE 2 (Push and Create PR):
        git push -u origin <feature-branch>
        gh pr create --title "<title>" --body "<summary + test plan>"
        REPORT branch/PR location
        DO NOT cleanup worktree
        STOP

    CASE 3 (Keep As-Is):
        REPORT: "Keeping branch <name>. Worktree preserved at <path>."
        DO NOT cleanup worktree
        STOP

    CASE 4 (Discard):
        CONFIRM: "This will permanently delete: Branch <name>, All commits: <list>, Worktree at <path>. Type 'discard' to confirm."
        WAIT for exact "discard"
        IF confirmed:
            git checkout <base-branch>
            git branch -D <feature-branch>
            GOTO STEP 6

    /* Step 5: Notify Vega-Punk (if applicable) */
    IF ~/.vega-punk/vega-punk-state.json exists:
        CASE Option 1 succeeded:
            UPDATE state = "DONE", completion_method = "merged"
        CASE Option 4 confirmed:
            UPDATE state = "DONE", completion_method = "discarded"
        /* Options 2 and 3: do NOT update state */

    /* Step 6: Cleanup Worktree (Options 1 and 4 only) */
    IF user_choice IN [1, 4]:
        IF state has worktree_path:
            worktree_path = read from state
        ELSE:
            worktree_path = git worktree list | grep current_branch | parse path
        IF worktree_path found:
            ATTEMPT git worktree remove "$worktree_path"
            IF fails: ASK "Stash/commit first, or force remove?"
    /* Options 2 and 3: Keep worktree */
END
```

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge locally | ✓ | - | - | ✓ |
| 2. Create PR | - | ✓ | ✓ | - |
| 3. Keep as-is | - | - | ✓ | - |
| 4. Discard | - | - | - | ✓ (force) |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**No diff summary before options**
- **Problem:** User can't judge scope of changes
- **Fix:** Always show files changed, lines added/removed, notable files (migrations, configs, dependencies)

**Open-ended questions**
- **Problem:** "What should I do next?" → ambiguous
- **Fix:** Present exactly 4 structured options with one-line descriptions

**Automatic worktree cleanup**
- **Problem:** Remove worktree when might need it (Option 2, 3)
- **Fix:** Only cleanup for Options 1 and 4 (Step 6)

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

**Ignoring merge test failures**
- **Problem:** Merged code passes on branch but fails on main (integration gap, dependency conflict)
- **Fix:** Always re-run tests AFTER merge, diagnose new vs pre-existing failures, auto-abort if broken

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Ignore merge-introduced test failures (always diagnose and roll back if broken)
- Skip the diff summary — user needs to judge scope

**Always:**
- Verify tests before offering options
- Show change summary (files, lines, notable files)
- Present exactly 4 options with one-line descriptions
- Re-run tests AFTER merge, not just before
- Diagnose new vs pre-existing failures post-merge
- Roll back merge if new failures detected
- Get typed confirmation for Option 4
- Clean up worktree for Options 1 & 4 only

## Integration

**Called by:**
- **task-dispatcher** (Step 7) - After all tasks complete
- **plan-executor** (Step 5) - After all batches complete

**Pairs with:**
- **worktree-setup** - Cleans up worktree created by that skill
