---
name: worktree-setup
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
categories: [ "workflow" ]
triggers: [ "worktree", "isolated workspace", "feature branch", "set up workspace" ]
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the worktree-setup skill to set up an isolated workspace."

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

## Pre-Execution Gate

```
BEGIN STATE_VALIDATION_GATE
    /* Required: git repository */
    IF not inside a git repository (git rev-parse --git-dir fails):
        FAIL: "[worktree-setup] Not in a git repository. Cannot create worktree."
        EXIT

    /* Check for pending uncommitted changes on current branch */
    IF git status --porcelain has output:
        TELL: "[worktree-setup] Uncommitted changes on current branch. Stashing before worktree creation."
        git stash push -m "vega-punk: auto-stash before worktree"
        stash_created = true

    /* Check if a worktree for target branch already exists */
    IF ~/.vega-punk/vega-punk-state.json exists AND worktree_path field exists:
        IF worktree_path directory exists:
            TELL: "[worktree-setup] Worktree already exists at {worktree_path}. Reusing."
            SKIP creation, proceed to setup
        /* else: stale path — recreate below */

    /* Validate branch name availability */
    IF target branch already checked out in another worktree:
        TELL: "[worktree-setup] Branch {branch_name} is already in use at another worktree."
        ASK: "Reuse existing or create a new branch?"
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

    /* Priority 2: Check CLAUDE.md / AGENTS.md for preference */
    IF worktree_dir NOT SET:
        grep -i "worktree.*director" CLAUDE.md AGENTS.md 2>/dev/null
        IF match found:
            worktree_dir = <configured path from CLAUDE.md/AGENTS.md>

    /* Priority 3: Default (no interaction) */
    IF worktree_dir NOT SET:
        worktree_dir = ".worktrees"

    /* Safety: verify project-local directory is gitignored */
    IF worktree_dir is project-local (not absolute path outside repo):
        IF git check-ignore -q "$worktree_dir" FAILS:
            ADD "$worktree_dir/" to .gitignore
            COMMIT the .gitignore change
END
```

## Safety Verification

### For Project-Local Directories

```bash
git check-ignore -q "$worktree_dir" 2>/dev/null
```

**If NOT ignored:**

1. Add `"$worktree_dir/"` to `.gitignore`
2. Commit the change
3. Proceed with worktree creation

**Why critical:** Prevents accidentally committing worktree contents to repository.

## Creation Process

```
BEGIN WORKTREE_CREATION
    /* Step 1: Determine branch name */
    IF ~/.vega-punk/roadmap.json exists:
        branch_name = "feature/{roadmap.project}-{roadmap.goal_slug}"
    ELSE IF ~/.vega-punk/vega-punk-state.json has task field:
        branch_name = "feature/{task_slug}"
    ELSE:
        branch_name = "feature/working"

    /* Slug rules: lowercase, hyphens, max 40 chars, no trailing hyphens */

    /* Step 2: Check for existing worktree */
    existing_path = git worktree list --porcelain | awk for branch_name
    IF existing_path is non-empty:
        worktree_path = existing_path
        TELL: "Worktree already exists at <path>. Reusing it."
        GOTO STEP 4 (Verify Clean Baseline)

    /* Step 3: Create worktree */
    worktree_path = "$(pwd)/$worktree_dir/$branch_name"
    git worktree add "$worktree_path" -b "$branch_name"

    /* Step 4: Run project setup — auto-detect and install */
    IF pnpm-workspace.yaml OR lerna.json exists in worktree_path:
        (cd "$worktree_path" && pnpm install)
    ELSE IF package.json exists in worktree_path:
        (cd "$worktree_path" && npm install)

    IF Cargo.toml exists in worktree_path:
        (cd "$worktree_path" && cargo build)

    IF requirements.txt exists in worktree_path:
        (cd "$worktree_path" && pip install -r requirements.txt)
    IF pyproject.toml exists in worktree_path:
        (cd "$worktree_path" && poetry install)

    IF go.mod exists in worktree_path:
        (cd "$worktree_path" && go mod download)

    /* Step 5: Verify clean baseline */
    RUN project test command (npm test / cargo test / pytest / go test ./...)
    IF tests pass:
        test_status = "all passing"
    ELSE:
        test_status = "<N> pre-existing failures"
        FLAG: "These are pre-existing — flag so executor can distinguish new vs existing"

    /* Step 6: Record worktree path */
    IF ~/.vega-punk/vega-punk-state.json exists:
        ADD worktree_path = "<absolute path>" to state
        ADD worktree_branch = "<branch_name>" to state

    /* Step 7: Report */
    TELL: "Worktree ready at <full-path>\nBranch: <branch_name>\nTests: <test_status>\nReady to implement <feature-name>"
END
```

## Quick Reference

| Situation                          | Action                                                   |
|------------------------------------|----------------------------------------------------------|
| `.worktrees/` exists               | Use it, set `worktree_dir=".worktrees"` (verify ignored) |
| `worktrees/` exists                | Use it, set `worktree_dir="worktrees"` (verify ignored)  |
| Both exist                         | Use `.worktrees/`                                        |
| Neither exists, no config          | Default `.worktrees/`                                    |
| CLAUDE.md specifies preference     | Use it without asking                                    |
| Directory not ignored              | Add to `.gitignore` + commit                             |
| Tests fail during baseline         | Report + proceed (pre-existing flag)                     |
| No package.json/Cargo.toml         | Skip dependency install                                  |
| Worktree already exists for branch | Reuse it, skip creation                                  |

## Common Mistakes

### Skipping ignore verification

- **Problem:** Worktree contents get tracked, pollute git status
- **Fix:** Always use `git check-ignore` before creating project-local worktree

### Assuming directory location

- **Problem:** Creates inconsistency, violates project conventions
- **Fix:** Follow priority: existing > CLAUDE.md > default `.worktrees/`

### Proceeding with failing tests without flagging

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report pre-existing failure count so downstream can compare

### Hardcoding setup commands

- **Problem:** Breaks on projects using different tools
- **Fix:** Auto-detect from project files (package.json, etc.)

### Not checking for existing worktree

- **Problem:** `git worktree add` fails if path already exists
- **Fix:** Check `git worktree list` first, reuse if found

### Not recording worktree path

- **Problem:** branch-landing can't find the worktree to clean up
- **Fix:** Always write `worktree_path` to `~/.vega-punk/vega-punk-state.json`

### Relying on `cd` across steps

- **Problem:** Shell state does not persist between code blocks
- **Fix:** Use absolute `$worktree_path` in every command, wrap in subshells `(cd "$worktree_path" && ...)`

## Example Workflow

```
You: I'm using the worktree-setup skill to set up an isolated workspace.

[Check .worktrees/ - exists → worktree_dir=".worktrees"]
[Verify ignored - git check-ignore confirms]
[Determine branch name from ~/.vega-punk/roadmap.json: feature/myapp-add-auth]
[Check existing worktree - not found]
[Create: git worktree add /Users/jesse/myproject/.worktrees/feature-myapp-add-auth -b feature/myapp-add-auth]
[Run: (cd "$worktree_path" && npm install)]
[Run: (cd "$worktree_path" && npm test) - 47 passing]
[Write worktree_path to ~/.vega-punk/vega-punk-state.json]

Worktree ready at /Users/jesse/myproject/.worktrees/feature-myapp-add-auth
Branch: feature/myapp-add-auth
Tests: 47 passing, 0 pre-existing failures
Ready to implement auth feature
```

## Red Flags

**Never:**

- Create worktree without verifying it's ignored (project-local)
- Skip baseline test verification
- Assume directory location when ambiguous
- Skip CLAUDE.md check
- Fail to record worktree path in state file
- Fail to check for existing worktree before creating
- Rely on `cd` to persist between code blocks

**Always:**

- Follow directory priority: existing > CLAUDE.md > default `.worktrees/`
- Verify directory is ignored for project-local
- Auto-detect and run project setup
- Verify clean test baseline
- Record `worktree_path` for downstream cleanup
- Reuse existing worktree if already created
- Use absolute paths in every command

## Integration

**Called by:**

- **vega-punk** (DESIGN → HANDOFF) — REQUIRED when design is approved and implementation follows
- **plan-executor** — REQUIRED at Step 1.6 (fresh start only)
- **task-dispatcher** — REQUIRED before executing any tasks
- Any skill needing isolated workspace

**Pairs with:**

- **branch-landing** — reads `worktree_path` from `~/.vega-punk/vega-punk-state.json` for cleanup
