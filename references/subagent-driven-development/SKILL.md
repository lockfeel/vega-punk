---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each: spec compliance review first, then code quality review.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Two-stage review order:** Spec compliance review first, then code quality review. Rationale: verify we built the right thing before verifying we built it well. A beautifully coded wrong feature is still wrong.

## When to Use

**Use this skill when:**
- You have an implementation plan (`roadmap.json` from planning-with-json)
- Tasks are mostly independent (can be dispatched separately)
- You want to stay in the same session (no context switch)

**vs. Executing Plans:**
- Same session (no context switch)
- Fresh subagent per task (no context pollution)
- Two-stage review after each task: spec compliance first, then code quality
- Faster iteration (no human-in-loop between tasks)

## The Process

1. **Read `roadmap.json`** — extract all phases and steps with full context
2. **Create TodoWrite** — one entry per phase/task from the plan
3. **For each task:**
   - Dispatch implementer subagent with full task text + context (`implementer-prompt.md`)
   - If implementer asks questions → answer, provide context, re-dispatch
   - Implementer implements, tests, commits, self-reviews
   - Dispatch spec reviewer subagent (`spec-reviewer-prompt.md`)
   - If spec reviewer finds issues → implementer fixes → re-review until ✅
   - Dispatch code quality reviewer subagent (`code-quality-reviewer-prompt.md`)
   - If code reviewer finds issues → implementer fixes → re-review until ✅
   - Mark task complete
4. **Final code review** — dispatch reviewer for entire implementation (use `requesting-code-review/code-reviewer.md` template with the full git range from first to last commit)
5. **finishing-a-development-branch** — complete development

## Model Selection

Use the least powerful model that can handle each role to conserve cost and increase speed.

**Mechanical implementation tasks** (isolated functions, clear specs, 1-2 files): use a fast, cheap model. Most implementation tasks are mechanical when the plan is well-specified.

**Integration and judgment tasks** (multi-file coordination, pattern matching, debugging): use a standard model.

**Architecture, design, and review tasks**: use the most capable available model.

**Task complexity signals:**
- Touches 1-2 files with a complete spec → fast model
- Touches multiple files with integration concerns → standard model
- Requires design judgment or broad codebase understanding → most capable model

**Dispatch example (Claude Code):**
```
Task tool (general-purpose, model: "haiku"):
  description: "Implement Task 1.1: Create UserService skeleton"
  prompt: |
    [implementer-prompt.md content]
```

**Dispatch example (OpenClaw):** Use `openclaw agent dispatch --model fast` or the platform's equivalent model selection mechanism.

## Handling Implementer Status

Implementer subagents report one of four statuses. Handle each appropriately:

**DONE:** Proceed to spec compliance review.

**DONE_WITH_CONCERNS:** The implementer completed the work but flagged doubts. Read the concerns before proceeding. If the concerns are about correctness or scope, address them before review. If they're observations (e.g., "this file is getting large"), note them and proceed to review.

**NEEDS_CONTEXT:** The implementer needs information that wasn't provided. Provide the missing context and re-dispatch.

**BLOCKED:** The implementer cannot complete the task. Assess the blocker:
1. If it's a context problem, provide more context and re-dispatch with the same model
2. If the task requires more reasoning, re-dispatch with a more capable model
3. If the task is too large, break it into smaller pieces
4. If the plan itself is wrong, escalate to the human

**Never** ignore an escalation or force the same model to retry without changes. If the implementer said it's stuck, something needs to change.

## Review Error Recovery

If a reviewer finds issues, the implementer fixes and the reviewer re-reviews. If this cycle repeats, apply these limits:

**Spec compliance review — max 3 cycles:**
- Cycle 1-2: Implementer fixes, reviewer re-reviews
- Cycle 3: If still failing, the spec itself may be ambiguous. Escalate to human with specific discrepancy (spec says X, implementer built Y, who's right?)

**Code quality review — max 2 cycles:**
- Cycle 1: Implementer fixes, reviewer re-reviews
- Cycle 2: If reviewer still finds Important/Critical issues, the implementer may be fundamentally misunderstanding the pattern. Escalate to human with the conflicting perspectives.

**If reviewer is wrong:** Implementer should push back with technical reasoning (file:line evidence, test results, spec quotes). The controller (you) makes the final call — don't let the review loop indefinitely.

## Prompt Templates

- `implementer-prompt.md` — Dispatch implementer subagent. Copy the full template, fill in task-specific details (task name, full text, context, file structure) before dispatching.
- `spec-reviewer-prompt.md` — Dispatch spec compliance reviewer. Copy the full template, fill in the requested spec text and git SHAs.
- `code-quality-reviewer-prompt.md` — Dispatch code quality reviewer. Copy the full template, fill in git SHAs and task description.

## Example Workflow

```
You: I'm using Subagent-Driven Development to execute this plan.
[Extract all tasks from roadmap.json → Create TodoWrite entries]

For each task:
  1. Dispatch implementer (implementer-prompt.md + full task text + context)
  2. If implementer asks questions → answer → re-dispatch
  3. Dispatch spec reviewer (spec-reviewer-prompt.md) → fix issues → re-review until ✅
  4. Dispatch code quality reviewer (code-quality-reviewer-prompt.md) → fix issues → re-review until ✅
  5. Mark task complete

After all tasks:
  Final code review (requesting-code-review/code-reviewer.md, full git range)
  → finishing-a-development-branch
```

## Advantages

**vs. Manual execution:**
- Subagents follow TDD naturally
- Fresh context per task (no confusion)
- Parallel-safe (subagents don't interfere)
- Subagent can ask questions (before AND during work)

**vs. Executing Plans:**
- Same session (no handoff)
- Continuous progress (no waiting)
- Review checkpoints automatic

**Efficiency gains:**
- No file reading overhead (controller provides full text)
- Controller curates exactly what context is needed
- Subagent gets complete information upfront
- Questions surfaced before work begins (not after)

**Quality gates:**
- Self-review catches issues before handoff
- Two-stage review: spec compliance, then code quality
- Review loops ensure fixes actually work
- Spec compliance prevents over/under-building
- Code quality ensures implementation is well-built

**Cost:**
- More subagent invocations (implementer + 2 reviewers per task)
- Controller does more prep work (extracting all tasks upfront)
- Review loops add iterations
- But catches issues early (cheaper than debugging later)

## Red Flags

**Never:**
- Start implementation on main/master branch without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel **within the same task** (conflicts on shared files)
- Dispatch independent tasks in parallel **across different subagent-driven-development sessions** (use `dispatching-parallel-agents` for this pattern)
- Make subagent read plan file (provide full text instead)
- Skip scene-setting context (subagent needs to understand where task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance (spec reviewer found issues = not done)
- Skip review loops (reviewer found issues = implementer fixes = review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is ✅** (wrong order)
- Move to next task while either review has open issues

**If subagent asks questions:**
- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

**If reviewer finds issues:**
- Implementer (same subagent) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

**If subagent fails task:**
- Dispatch fix subagent with specific instructions
- Don't try to fix manually (context pollution)

## Integration

**Required workflow skills:**
- **using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **vega-punk** - Creates the design that leads to planning-with-json
- **planning-with-json** - Creates the `roadmap.json` this skill executes
- **requesting-code-review** - Code review template for reviewer subagents
- **verification-before-completion** - REQUIRED: Subagents verify each task before reporting done
- **finishing-a-development-branch** - Complete development after all tasks

**Subagents should use:**
- **test-driven-development** - Subagents follow TDD for each task

**Alternative workflow:**
- **executing-plans** - Use for parallel session instead of same-session execution
