---
name: worktree-setup
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
categories: ["workflow"]
triggers: ["worktree", "isolated workspace", "feature branch", "set up workspace"]
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the worktree-setup skill to set up an isolated workspace."

## Directory Selection Process

Follow this priority order — **no user interaction required unless explicitly requested**:

### 1. Check Existing Directories

```bash
ls -d .worktrees 2>/dev/null     # Preferred (hidden)
ls -d worktrees 2>/dev/null      # Alternative
```

**If found:** Use that directory. If both exist, `.worktrees` wins. Set `worktree_dir` to the found path.

### 2. Check CLAUDE.md / AGENTS.md

```bash
grep -i "worktree.*director" CLAUDE.md AGENTS.md 2>/dev/null
```

**If preference found:** Use it. Set `worktree_dir` to the configured path.

### 3. Default (no interaction)

If no directory exists and no config found: **default to `.worktrees/`** (project-local, hidden). Set `worktree_dir=".worktrees"`.

**`worktree_dir` is now the single variable for all subsequent steps.**

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

### Step 1: Determine Branch Name

```
IF roadmap.json exists:
    branch_name = "feature/{roadmap.project}-{roadmap.goal_slug}"
ELSE IF .vega-punk-state.json has task field:
    branch_name = "feature/{task_slug}"
ELSE:
    branch_name = "feature/working"
```

Slug rules: lowercase, hyphens, max 40 chars, no trailing hyphens.

### Step 2: Check for Existing Worktree

```bash
existing_path=$(git worktree list --porcelain | awk '/^worktree /{p=$2} /^branch .+\/'"$branch_name"'$/{print p; exit}')
```

**If `existing_path` is non-empty (worktree already exists):**
- Set `worktree_path="$existing_path"`
- Report: "Worktree already exists at `<path>`. Reusing it."
- Skip to Step 4 (Verify Clean Baseline)

### Step 3: Create Worktree

```bash
worktree_path="$(pwd)/$worktree_dir/$branch_name"
git worktree add "$worktree_path" -b "$branch_name"
```

### Step 4: Run Project Setup

Auto-detect and run appropriate setup (use absolute paths, do NOT rely on `cd`):

```bash
# Node.js — check for monorepo first
if [ -f "$worktree_path/pnpm-workspace.yaml" ] || [ -f "$worktree_path/lerna.json" ]; then
  (cd "$worktree_path" && pnpm install)
elif [ -f "$worktree_path/package.json" ]; then
  (cd "$worktree_path" && npm install)
fi

# Rust
if [ -f "$worktree_path/Cargo.toml" ]; then
  (cd "$worktree_path" && cargo build)
fi

# Python
if [ -f "$worktree_path/requirements.txt" ]; then
  (cd "$worktree_path" && pip install -r requirements.txt)
fi
if [ -f "$worktree_path/pyproject.toml" ]; then
  (cd "$worktree_path" && poetry install)
fi

# Go
if [ -f "$worktree_path/go.mod" ]; then
  (cd "$worktree_path" && go mod download)
fi
```

**Monorepo note:** Run install at the workspace root. Individual package builds handled by task-specific steps.

### Step 5: Verify Clean Baseline

Run tests to ensure worktree starts clean:

```bash
# Use project-appropriate command: npm test / cargo test / pytest / go test ./...
# Always run in a subshell: (cd "$worktree_path" && npm test)
```

**If tests fail:** Report failures with count. Proceed anyway (these are pre-existing issues) but flag them so the executor knows which failures are pre-existing vs new.

### Step 6: Record Worktree Path

Write worktree path to `.vega-punk-state.json` so downstream skills (branch-landing) can find it:

```
IF .vega-punk-state.json exists:
    ADD worktree_path = "<absolute path to worktree>"
    ADD worktree_branch = "<branch_name>"
```

### Step 7: Report

```
Worktree ready at <full-path>
Branch: <branch_name>
Tests: <N> passing, <M> pre-existing failures
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it, set `worktree_dir=".worktrees"` (verify ignored) |
| `worktrees/` exists | Use it, set `worktree_dir="worktrees"` (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists, no config | Default `.worktrees/` |
| CLAUDE.md specifies preference | Use it without asking |
| Directory not ignored | Add to `.gitignore` + commit |
| Tests fail during baseline | Report + proceed (pre-existing flag) |
| No package.json/Cargo.toml | Skip dependency install |
| Worktree already exists for branch | Reuse it, skip creation |

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
- **Fix:** Always write `worktree_path` to `.vega-punk-state.json`

### Relying on `cd` across steps

- **Problem:** Shell state does not persist between code blocks
- **Fix:** Use absolute `$worktree_path` in every command, wrap in subshells `(cd "$worktree_path" && ...)`

## Example Workflow

```
You: I'm using the worktree-setup skill to set up an isolated workspace.

[Check .worktrees/ - exists → worktree_dir=".worktrees"]
[Verify ignored - git check-ignore confirms]
[Determine branch name from roadmap.json: feature/myapp-add-auth]
[Check existing worktree - not found]
[Create: git worktree add /Users/jesse/myproject/.worktrees/feature-myapp-add-auth -b feature/myapp-add-auth]
[Run: (cd "$worktree_path" && npm install)]
[Run: (cd "$worktree_path" && npm test) - 47 passing]
[Write worktree_path to .vega-punk-state.json]

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
- **branch-landing** — reads `worktree_path` from `.vega-punk-state.json` for cleanup
