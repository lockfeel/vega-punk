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

**File locations:** When this document says "state file", it means `~/.vega-punk/vega-punk-state.json`. All vega-punk runtime files reside in `~/.vega-punk/`.

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations. 

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Validate current branch state */
    current_branch = git branch --show-current

    IF current_branch is empty (detached HEAD):
        TELL: "[branch-landing] You're in detached HEAD state. Cannot complete from here."
        ASK: "Check out a branch first? (git checkout <branch>)"
        STOP

    IF current_branch is "main" OR "master":
        TELL: "[branch-landing] You're on {current_branch}. This is unusual."
        ASK: "Are you sure you want to complete from {current_branch}? This could affect the main branch."

    /* Try to find worktree_path */
    IF state file exists:
        IF worktree_path field missing:
            /* Try to find worktree from git */
            worktree_path = git worktree list | grep current_branch | parse path
            IF worktree_path found:
                ADD worktree_path to state file
                TELL: "[branch-landing] Found worktree at {worktree_path} via git."
            ELSE:
                /* Not in a worktree — might be inline execution */
                worktree_path = null
                TELL: "[branch-landing] No worktree found. Proceeding without cleanup."
        ELSE IF worktree_path directory does NOT exist:
            /* Worktree was removed — find from git */
            worktree_path = git worktree list | grep current_branch | parse path
            IF worktree_path found:
                UPDATE worktree_path in state file
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

    /* Step 2: Summarize Changes */
    git diff --stat <base>..HEAD
    COUNT: files changed, lines added/removed
    IDENTIFY: new files, deleted files, modified files
    FLAG: any migration files, config changes, dependency updates

    /* Step 3: Determine Base Branch */
    base_commit = git merge-base HEAD main || git merge-base HEAD master
    IF base_commit NOT found:
        ASK: "This branch splits from main - is that correct?"
    /* Determine the actual base branch name (not commit hash) */
    base_branch = "main"  /* default */
    IF "master" branch exists AND "main" does NOT:
        base_branch = "master"

    /* Step 4: Present Options */
    OUTPUT exactly:
        "Implementation complete.
         Summary: <N> files changed, +<added>/-<removed> lines.
         Tests: all passing.

         What would you like to do?

         1. Merge back to <base_branch> locally
            — auto-verifies tests on merged result, rolls back if broken
         2. Push and create a Pull Request
            — preserves branch + worktree for iterative review
         3. Keep the branch as-is (I'll handle it later)
            — no changes, worktree stays available
         4. Discard this work
            — requires typed confirmation, irreversible

         Which option?"
    WAIT for user choice

    /* Step 5: Execute Choice */
    CASE 1 (Merge Locally):
        git checkout base_branch
        git pull
        git merge feature_branch

        /* Handle merge conflicts */
        IF merge has conflicts:
            REPORT: "Merge has conflicts in: <conflicted files>"
            PRESENT options:
                a. "Abort merge and keep branch as-is" — git merge --abort, GOTO CASE 3
                b. "I'll resolve conflicts manually" — PAUSE, wait for user to resolve, then continue below
            IF user chose a: STOP
            IF user chose b:
                WAIT until `git diff --check` passes (no conflict markers)
                git add -A && git commit (no --no-verify)

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
                    PRESENT diff to user for review before committing  /* never auto-commit fixes silently */
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
            /* Safe branch deletion with fallback */
            ATTEMPT git branch -d feature_branch
            IF fails (branch not fully merged per git's heuristics):
                WARN: "git branch -d refused — branch may have diverged. Use -D to force delete?"
                ASK user before using -D
        GOTO STEP 6

    CASE 2 (Push and Create PR):
        /* Check gh CLI availability */
        IF `gh` command NOT available OR `gh auth status` fails:
            WARN: "[branch-landing] gh CLI not available or not authenticated."
            PRESENT fallback options:
                a. "Push branch only (I'll create PR manually)" — git push -u origin feature_branch
                b. "Keep branch as-is (I'll handle everything)" — GOTO CASE 3 behavior
            IF user chose a:
                REPORT: "Branch pushed to origin. Create PR manually at the remote."
                STOP
            IF user chose b:
                STOP

        /* Check if remote branch already exists and has diverged */
        IF remote branch feature_branch already exists:
            LOCAL_AHEAD = git rev-list origin/feature_branch..HEAD --count
            REMOTE_AHEAD = git rev-list HEAD..origin/feature_branch --count
            IF REMOTE_AHEAD > 0:
                WARN: "[branch-landing] Remote branch has diverged (remote +{REMOTE_AHEAD}, local +{LOCAL_AHEAD})."
                ASK: "Force push, rebase first, or abort?"
                IF user says "force push": git push --force-with-lease -u origin feature_branch
                IF user says "rebase": git rebase origin/feature_branch → then push
                ELSE: STOP
            ELSE:
                /* Remote behind or same — safe push */
                git push -u origin feature_branch
        ELSE:
            git push -u origin feature_branch

        /* Create PR with structured description */
        PR_TITLE = "<concise summary from Step 2>"
        PR_BODY = build from template (see PR Description Template section)
        gh pr create --title PR_TITLE --body PR_BODY
        REPORT branch/PR location
        DO NOT cleanup worktree
        STOP

    CASE 3 (Keep As-Is):
        REPORT: "Keeping branch <name>. Worktree preserved at <path>."
        DO NOT cleanup worktree
        STOP

    CASE 4 (Discard):
        /* Check for uncommitted changes first */
        IF git status has uncommitted changes:
            REPORT: "Working directory has uncommitted changes: <list>"
            ASK: "Commit, stash, or proceed with discard (changes will be lost)?"
            IF user says "commit": git add -A && git commit
            IF user says "stash": git stash
            IF user says "proceed": CONTINUE (changes lost)
            ELSE: STOP — abort discard

        CONFIRM: "This will permanently delete: Branch <name>, All commits unique to this branch: <list>. Type 'discard' to confirm."
        WAIT for exact "discard"
        IF confirmed:
            git checkout base_branch
            git branch -D feature_branch
            GOTO STEP 6

    /* Step 6: Notify Vega-Punk (if applicable) */
    IF state file exists:
        CASE Option 1 succeeded:
            UPDATE state = "DONE", completion_method = "merged"
        CASE Option 2 (PR created):
            UPDATE state = "REVIEW", completion_method = "pr", pr_url = "<url>"
        CASE Option 3 (Keep as-is):
            UPDATE state = "PAUSED", completion_method = "kept", notes = "Branch preserved at user request"
        CASE Option 4 confirmed:
            UPDATE state = "DONE", completion_method = "discarded"

    /* Step 7: Cleanup Worktree (Options 1 and 4 only) */
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

| Option | Merge | Push | Keep Worktree | Cleanup Branch | State Update | Rollback on Failure |
|--------|-------|------|---------------|----------------|--------------|---------------------|
| 1. Merge locally | ✓ | - | - | ✓ | DONE/merged | Abort merge → keep branch |
| 2. Create PR | - | ✓ | ✓ | - | REVIEW/pr | N/A (push failure → report) |
| 3. Keep as-is | - | - | ✓ | - | PAUSED/kept | N/A |
| 4. Discard | - | - | - | ✓ (force) | DONE/discarded | Uncommitted changes check first |

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
