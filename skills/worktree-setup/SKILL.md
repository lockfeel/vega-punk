---
name: worktree-setup
description: "Create isolated git worktrees for feature work. 做什么：智能目录选择 + 安全检查 + 自动依赖安装。何时用：需要隔离工作区或执行实现计划前。触发词: worktree, isolated workspace, feature branch, set up workspace, 创建工作树, 隔离环境"
categories: [ "workflow" ]
triggers: [ "worktree", "isolated workspace", "feature branch", "set up workspace", "创建工作树", "隔离环境" ]
user-invocable: true
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification + rollback guarantees = reliable isolation.

**Announce at start:** "I'm using the worktree-setup skill to set up an isolated workspace."

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: git repository */
    IF not inside a git repository (git rev-parse --git-dir fails):
        FAIL: "[worktree-setup] Not in a git repository. Cannot create worktree."
        EXIT

    /* P0-fix: REMOVED stash logic — git worktree add does NOT switch branches
       or modify the working tree. Dirty worktree is perfectly fine.
       The only constraint: the target branch must not be checked out elsewhere.
       Stashing was causing silent data loss (stash with no pop path). */

    /* Check if already inside a worktree — nested worktrees are usually unintended */
    common_dir = git rev-parse --git-common-dir
    IF common_dir is NOT ".git" AND NOT ending with "/.git":
        /* We are inside a worktree, not the main working tree */
        WARN: "[worktree-setup] Already inside a worktree at {current_path}. Nested worktrees are usually unintended."
        ASK: "Continue anyway?"
        IF user says no:
            EXIT

    /* Check for existing worktree for target branch */
    existing_path = git worktree list --porcelain
        | grep -A2 "branch refs/heads/{branch_name}$"
        | head -1
        | sed 's/^worktree //'
    IF existing_path is non-empty AND directory {existing_path} exists:
        TELL: "[worktree-setup] Worktree already exists at {existing_path}. Reusing."
        SET worktree_path = existing_path
        SKIP creation, GOTO POST_CREATION_SETUP

    /* Validate branch name availability */
    IF target branch already checked out in another worktree (but path missing/stale):
        TELL: "[worktree-setup] Branch {branch_name} is already checked out at a stale worktree path."
        ASK: "Remove stale worktree and recreate? (git worktree prune + re-add)"
        IF user says yes:
            git worktree prune
        ELSE:
            EXIT

    /* Handle detached HEAD — generate branch name differently */
    current_branch = git rev-parse --abbrev-ref HEAD
    IF current_branch == "HEAD":
        /* Detached HEAD state — e.g., during rebase or bisect */
        short_hash = git rev-parse --short HEAD
        WARN: "[worktree-setup] Currently in detached HEAD state ({short_hash})."
        ASK: "Create worktree anyway? Branch name will include commit hash."
END
```

## Branch Name Generation

```
BEGIN BRANCH_NAME_GENERATION
    /* Explicit slug algorithm — produces deterministic, safe branch names */

    IF ~/.vega-punk/roadmap.json exists:
        raw_name = "{roadmap.project}-{roadmap.goal_slug}"
    ELSE IF ~/.vega-punk/vega-punk-state.json has task field:
        raw_name = "{task_slug}"
    ELSE:
        short_hash = git rev-parse --short HEAD
        raw_name = "working-{short_hash}"

    /* Slug transformation (applied to raw_name): */
    /* 1. Lowercase all characters */
    /* 2. Replace any character NOT in [a-z0-9-] with hyphen */
    /* 3. Collapse multiple consecutive hyphens into one */
    /* 4. Strip leading and trailing hyphens */
    /* 5. Truncate to max 40 characters, breaking at last hyphen if possible */
    /* 6. If result is empty after slugification, use "work-{short_hash}" */

    branch_name = "feature/{slugified(raw_name)}"

    /* Ensure branch doesn't already exist as a non-worktree branch */
    IF git show-ref --verify --quiet "refs/heads/{branch_name}":
        /* Branch exists but is NOT checked out in a worktree (would have been caught above) */
        branch_name = "feature/{slugified(raw_name)}-{short_hash}"
END
```

## Directory Selection Process

Follow this priority order — **no user interaction required unless explicitly requested**:

```
BEGIN DIRECTORY_SELECTION
    /* Priority 1: Check existing directories */
    IF .worktrees/ exists:
        worktree_dir = ".worktrees"
    ELSE IF worktrees/ exists:
        worktree_dir = "worktrees"

    /* Priority 2: Check CLAUDE.md for structured config comment */
    IF worktree_dir NOT SET:
        match = grep -E '<!--\s*worktree-dir:\s*(\S+)\s*-->' CLAUDE.md AGENTS.md 2>/dev/null
        IF match found:
            worktree_dir = <captured path from config comment>

    /* Priority 3: Default (no interaction) */
    IF worktree_dir NOT SET:
        worktree_dir = ".worktrees"

    /* Safety: verify project-local directory is gitignored */
    IF worktree_dir is project-local (not absolute path outside repo):
        IF git check-ignore -q "$worktree_dir" FAILS:
            ADD "$worktree_dir/" to .gitignore
            TELL: "[worktree-setup] Added '{worktree_dir}/' to .gitignore (not auto-committed)."
            /* P1-fix: Do NOT auto-commit — let user or downstream skill decide when to commit */
END
```

## Worktree Count Guard

```
BEGIN WORKTREE_COUNT_GUARD
    current_count = git worktree list --porcelain | grep -c "^worktree "
    /* Subtract 1 for the main working tree */
    IF (current_count - 1) >= 5:
        WARN: "[worktree-setup] {current_count - 1} worktrees already exist. Consider cleaning up before creating more."
        LIST: git worktree list (show paths and branches)
        ASK: "Proceed with new worktree anyway?"
        IF user says no:
            EXIT
END
```

## Creation Process

```
BEGIN WORKTREE_CREATION
    /* Step 1: Run Pre-Execution Gate → get branch_name, worktree_dir */

    /* Step 2: Run Directory Selection → get worktree_dir */

    /* Step 3: Run Worktree Count Guard */

    /* Step 4: Determine if branch already exists as a git ref */
    branch_exists = git show-ref --verify --quiet "refs/heads/{branch_name}"

    /* Step 5: Create worktree (handle existing branch correctly) */
    worktree_path = "$(pwd)/$worktree_dir/$branch_name"

    IF branch_exists:
        /* P0-fix: Branch ref exists — use it without -b flag */
        git worktree add "$worktree_path" "$branch_name"
    ELSE:
        /* New branch — use -b to create */
        git worktree add "$worktree_path" -b "$branch_name"

    IF worktree creation FAILS:
        FAIL: "[worktree-setup] git worktree add failed: {error}"
        EXIT  /* No cleanup needed — nothing was created */

    /* From here on, if any step fails, roll back the worktree */
    SET creation_succeeded = true

    /* Step 6: Run project setup — auto-detect and install */
    IF pnpm-workspace.yaml OR lerna.json exists in worktree_path:
        RUN (cd "$worktree_path" && pnpm install)
        IF FAILS: GOTO ROLLBACK
    ELSE IF package.json exists in worktree_path:
        IF yarn.lock exists:
            RUN (cd "$worktree_path" && yarn install)
            IF FAILS: GOTO ROLLBACK
        ELSE IF pnpm-lock.yaml exists:
            RUN (cd "$worktree_path" && pnpm install)
            IF FAILS: GOTO ROLLBACK
        ELSE:
            RUN (cd "$worktree_path" && npm install)
            IF FAILS: GOTO ROLLBACK

    IF Cargo.toml exists in worktree_path:
        RUN (cd "$worktree_path" && cargo build)
        IF FAILS: GOTO ROLLBACK

    IF pyproject.toml exists in worktree_path:
        IF poetry.lock exists:
            RUN (cd "$worktree_path" && poetry install)
            IF FAILS: GOTO ROLLBACK
        ELSE:
            RUN (cd "$worktree_path" && pip install -e .)
            IF FAILS: GOTO ROLLBACK
    ELSE IF requirements.txt exists in worktree_path:
        RUN (cd "$worktree_path" && pip install -r requirements.txt)
        IF FAILS: GOTO ROLLBACK

    IF go.mod exists in worktree_path:
        RUN (cd "$worktree_path" && go mod download)
        IF FAILS: GOTO ROLLBACK

    /* Check for Makefile-based projects */
    IF Makefile exists in worktree_path AND make -n test succeeds (dry-run):
        RUN (cd "$worktree_path" && make test)
        /* Make test failure does NOT trigger rollback — just record status */

    /* Step 7: Verify clean baseline */
    test_status = detect_and_run_tests(worktree_path)
    /* test_status is one of: "all passing", "{N} pre-existing failures", "no tests found" */
    IF test_status contains "failures":
        FLAG: "These are pre-existing — flag so executor can distinguish new vs existing"

    /* Step 8: Record worktree path */
    ENSURE ~/.vega-punk/ directory exists:
        mkdir -p ~/.vega-punk/

    IF ~/.vega-punk/vega-punk-state.json exists:
        READ state, ADD worktree_path = "<absolute path>", ADD worktree_branch = "<branch_name>"
        WRITE back to file
    ELSE:
        /* P0-fix: Create state file if it doesn't exist */
        WRITE ~/.vega-punk/vega-punk-state.json with:
            { "worktree_path": "<absolute path>", "worktree_branch": "<branch_name>" }

    /* Step 9: Report */
    TELL: "Worktree ready at <full-path>
    Branch: <branch_name>
    Tests: <test_status>
    Ready to implement <feature-name>"

    DONE

ROLLBACK:
    /* P1-fix: Clean up half-created worktree on any post-creation failure */
    IF creation_succeeded AND worktree_path exists:
        git worktree remove "$worktree_path" --force
        TELL: "[worktree-setup] Setup failed, worktree at {worktree_path} has been cleaned up."
    FAIL: "[worktree-setup] Setup failed during post-creation step. See error above."
    EXIT
END
```

## Helper: detect_and_run_tests

```
BEGIN DETECT_AND_RUN_TESTS(worktree_path)
    /* Ordered detection — first match wins */

    IF package.json exists AND "test" in scripts:
        RUN (cd "$worktree_path" && npm test)
        RETURN "all passing" OR "{N} pre-existing failures"

    IF Cargo.toml exists:
        RUN (cd "$worktree_path" && cargo test)
        RETURN "all passing" OR "{N} pre-existing failures"

    IF pytest.ini OR pyproject.toml with [tool.pytest] OR tests/ with conftest.py:
        RUN (cd "$worktree_path" && pytest)
        RETURN "all passing" OR "{N} pre-existing failures"

    IF go.mod exists:
        RUN (cd "$worktree_path" && go test ./...)
        RETURN "all passing" OR "{N} pre-existing failures"

    IF Makefile exists AND make -n test succeeds:
        RUN (cd "$worktree_path" && make test)
        RETURN "all passing" OR "{N} pre-existing failures"

    RETURN "no tests found"
END
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Prefer `.worktrees/` |
| Neither exists, no config | Default `.worktrees/` |
| `<!-- worktree-dir: path -->` in CLAUDE.md | Use configured path |
| Directory not ignored | Add to `.gitignore`, tell user (no auto-commit) |
| Branch already exists as ref | `git worktree add` without `-b` |
| Branch checked out in stale worktree | Prune + re-add |
| Already inside a worktree | Warn + ask before proceeding |
| Detached HEAD | Warn + include commit hash in branch name |
| 5+ worktrees exist | Warn + list + ask before proceeding |
| Setup step fails after creation | Rollback: `git worktree remove --force` |
| Tests fail during baseline | Report + proceed (pre-existing flag) |
| No test framework detected | Skip, report "no tests found" |

## Red Flags

**Never:**
- Auto-stash working tree changes (worktree add doesn't need it)
- Auto-commit .gitindex modifications
- Use `git worktree add -b` when branch ref already exists
- Skip rollback on post-creation failure
- Create worktree without verifying it's ignored (project-local)
- Assume branch doesn't exist — always check with `git show-ref`
- Rely on `cd` to persist between code blocks
- Create state file without ensuring directory exists first
- Proceed silently when nested inside an existing worktree

**Always:**
- Follow directory priority: existing > CLAUDE.md config > default `.worktrees/`
- Verify directory is ignored for project-local paths
- Check `git show-ref` before using `-b` flag
- Auto-detect package manager from lock files (yarn.lock → yarn, pnpm-lock.yaml → pnpm, etc.)
- Roll back worktree on any post-creation failure
- Verify clean test baseline (or flag pre-existing failures)
- Record `worktree_path` in state file (create file if needed)
- Reuse existing worktree if already created
- Use absolute paths in every command
- Detect and warn on nested worktree usage
- Guard against excessive worktree count (≥5)

## Integration

**Called by:**
- **vega-punk** (DESIGN → HANDOFF) — REQUIRED when design is approved and implementation follows
- **plan-executor** — REQUIRED at Step 1.6 (fresh start only)
- **task-dispatcher** — REQUIRED before executing any tasks
- Any skill needing isolated workspace

**Pairs with:**
- **branch-landing** — reads `worktree_path` from `~/.vega-punk/vega-punk-state.json` for cleanup
