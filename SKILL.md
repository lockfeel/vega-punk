---
name: vega-punk
description: "Central nervous system for AI sessions. Routes requests, designs solutions, analyzes dependencies, selects skills, and hands off to planning. Use at session start for any task beyond simple Q&A. Triggers on: new session, ambiguous request, multi-step task, skill selection needed, or when user says 'let's think about' / 'how should we' / 'what's the plan'."
user-invocable: true
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch"
hooks:
  SessionStart:
    - type: command
      command: "bash scripts/session-hook.sh 2>/dev/null || echo '[vega-punk] Ready. What shall we build?'"
---

# Vega-Punk: Session State Machine

**Purpose:** Ensure every creative/implementation task follows a disciplined design flow before execution. Analyzes causal dependencies so the execution plan can maximize parallelism.

**Boundary:** vega-punk handles design and routing. After HANDOFF, the plan-builder sub-skill takes over — it reads the state file, generates the roadmap, and manages execution. vega-punk remains available to review execution results in the REVIEW state.

**State file:** `.vega-punk-state.json` in the working directory.
**Spec directory:** `vega-punk/specs/` in the working directory.

For **OpenClaw**, the working directory is your current project. For **Claude Code**, it's the directory where you started the session.

## Quick Start

Describe what you want to build. vega-punk auto-selects the mode:

- **Small change** ("fix typo") → CONDENSED: brief spec → approve → execute
- **Single feature** ("add dark mode") → CONDENSED: spec → plan → execute
- **Complex project** ("build notification system") → FULL: design → QA → dependencies → spec → plan → execute

Say "just do it" for condensed flow, or "let's think about this" for complex ones.

See [State Machine](#state-machine) for full flow details.

## How State Works

**State file:** `.vega-punk-state.json` in the working directory.

**On every user message:**

```
BEGIN STATE_RESOLUTION
    READ .vega-punk-state.json

    IF user says "start over" / "new task" / "forget previous":
        APPLY Post-Completion Cleanup
        TELL: "[vega-punk] Starting fresh. What shall we build?"
        GOTO ROUTE

    IF state == "DONE":
        APPLY Post-Completion Cleanup
        GOTO ROUTE

    IF file missing:
        GOTO ROUTE

    IF state == "REVIEW":
        IF execution_result exists:
            ENTER REVIEW
        ELSE IF roadmap.json exists AND has incomplete steps:
            RESUME execution from roadmap.json current_step
        ELSE:
            WAIT for user input (do NOT restart ROUTE)
        EXIT

    /* state is not DONE, file exists → recovery */
    ENTER current state directly
    DO NOT go back to ROUTE

    /* skill loop protection */
    IF scan_depth >= 3:
        SKIP skill routing
        GOTO CLARIFY
    ELSE:
        INCREMENT scan_depth on SCAN entry
        RESET scan_depth on CLARIFY entry

    /* state compaction (prevent unbounded growth) */
    IF qa.retries > 2 OR transition_count > 5:
        COMPACT:
            PRESERVE: state, task, context, selected_skills, scope, requirements, design, dependencies, spec_path
            COMPRESS qa → { "retries": N, "last_feedback": "<summary>", "status": "FAIL" }
            DROP any field > 500 chars not in preserve list → replace with 1-sentence summary

    /* state transition rule */
    ON each state change:
        READ current JSON
        CHANGE state field
        ADD new fields (NEVER delete existing fields)
        INCREMENT transition_count (initialize to 1 if absent)
        WRITE back
END

BEGIN Post-Completion Cleanup
    RENAME vega-punk/specs/*.md → *.DONE.md (completed) or *.CANCELLED.md (cancelled)
    DELETE .vega-punk-state.json
    /* On REVIEW → new task: archive specs + delete state, then restart ROUTE */
END
```

**Key rule:** Always preserve `task` field across all state transitions.

**Git:** Add `.vega-punk-state.json` to `.gitignore`. **Do NOT** gitignore `vega-punk/specs/` — spec history is project memory and should be committed.

**Progress reporting:** At each transition:
> "Entering [STATE]..."

If user asks "where are we?" or "how much left?", print current state and remaining steps.

| State        | FULL Path     | CONDENSED Path |
|--------------|---------------|----------------|
| ROUTE        | 9 states left | 3 states left  |
| SCAN         | 8             | —              |
| CLARIFY      | 7             | —              |
| DESIGN       | 6             | —              |
| DESIGN_QA    | 5             | —              |
| DEPENDENCIES | 4             | —              |
| SPEC         | 3             | —              |
| SPEC_QA      | 2             | —              |
| CONDENSED    | 3             | 3              |
| HANDOFF      | 1             | 1              |
| REVIEW       | 0             | 0              |

**Three execution modes:**

| Mode          | Steps                            | When                                       | State File | Skill Check |
|---------------|----------------------------------|--------------------------------------------|------------|-------------|
| **CONDENSED** | Minimal spec → Approval → Review | All tasks (single component to multi-step) | Required   | Full SCAN   |
| **FULL**      | All 9 states                     | Large/multi-step tasks, ambiguous scope    | Required   | Full SCAN   |

CONDENSED mode: 3 steps (minimal spec → approval → review), skips DESIGN/DEPENDENCIES/SPEC states. From CONDENSED: 3 states left (CONDENSED → HANDOFF → REVIEW → DONE).

---

## Three Hard Disciplines

These are rules. Do not treat them as suggestions.

### 1. HARD-GATE: No Design, No Execute

Do NOT execute anything — write code, scaffold projects, generate documents, create designs, produce content, modify configurations, invoke any implementation skill, or take any implementation action — until the design has been presented and the user has approved it. This applies to EVERY task regardless of perceived simplicity. A todo list, a single-function utility, a config change, a document, a presentation, a data analysis — all of them. The design can be short (a few sentences for truly simple projects via CONDENSED mode), but you MUST present it and get approval.

### 2. The 1% Rule: When in Doubt, Invoke

If there is even a 1% chance a skill might apply to what you are doing, you MUST invoke it. This is not negotiable. This is not optional. You cannot rationalize your way out of this. If an invoked skill turns out to be wrong for the situation, you don't need to use it — but you must check.

### 3. Instruction Priority

1. **User's explicit instructions** (CLAUDE.md, AGENTS.md, direct requests) — highest priority
2. **Skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If a user says "don't use TDD" and a skill says "always use TDD," follow the user. The user is in control.

---

## Core Operating Principles

These govern ALL behavior, regardless of current state:

### Skill Check Comes Before Everything

Skills tell you HOW to explore. Check for skills BEFORE gathering information, BEFORE asking clarifying questions, BEFORE doing anything. Do NOT say "I need more context first." Check skills first — they tell you how to gather context.

**When you invoke a skill, announce it:** "Using [skill] to [purpose]."

**If the skill has a checklist:** Create a TodoWrite task for each item and complete them in order.

**Invoke the skill tool** — don't just read the skill file.

- **Claude Code:** Use the `Skill` tool.
- **OpenClaw:** Use `openclaw skills` command or the platform's skill invocation mechanism.

### Skill Types

- **Rigid** (TDD, root-cause, verify-gate): Follow exactly. Don't adapt away discipline.
- **Flexible** (ui-ux-pro-max, frontend-design): Adapt principles to context.

The skill itself tells you which. Read the current version — skills evolve.

### Output Is Production

- Every deliverable — spec, design doc, diagram, config, code, presentation, image — must be aesthetically crafted and production-ready. No exceptions.
- No rough drafts. No "this is just a working version, we'll polish later." The first output IS the final output.
- If it wouldn't look right being shown to a client, shipped to users, or published publicly, it doesn't leave vega-punk.

### Handle Off-Topic Input

If the user sends a message unrelated to the current state's purpose:

1. Briefly acknowledge or answer if it's a simple question
2. Guide back: "Back to [STATE] — [reminder of where we are]"
3. Continue from the current state. Do NOT change state or restart the flow.

### Handle Cancel / Abort

If the user says "stop", "cancel", "I don't want to do this anymore", or equivalent at any point:

1. Apply Post-Completion Cleanup (archive specs, delete state).
2. Acknowledge: "[vega-punk] Cancelled. What shall we build?"
3. Set state: DONE. No spec, no plan, no handoff.

---

## State Machine

**FULL flow:**

```
BEGIN FULL
    ENTER ROUTE
    IF user says "skip design" → GOTO CONDENSED
    IF informational → state=DONE, EXIT

    ENTER SCAN
    ENTER CLARIFY

    LOOP design_retries ≤ 3:
        ENTER DESIGN
        IF user rejects → REPEAT
        ENTER DESIGN_QA
        IF PASS → BREAK
        IF FAIL → REPEAT
    IF retries exhausted → HALT, ask user

    ENTER DEPENDENCIES
    ENTER SPEC

    LOOP spec_retries ≤ 3:
        ENTER SPEC_QA
        IF PASS → BREAK
        IF FAIL → REPEAT (↩ SPEC, fix, re-submit)
    IF retries exhausted → HALT, ask user
    
    ENTER HANDOFF
    state = REVIEW, handoff_to = plan-builder
    WAIT for execution_result

    ENTER REVIEW
    IF success + passed → state=DONE
    IF failed → state=CLARIFY (requirements changed) or DESIGN (design wrong)
    IF partial → state=DESIGN (implement remaining)
END
```

**CONDENSED flow:**

```
BEGIN CONDENSED
    ENTER CONDENSED
    IF user rejects → state=SCAN (go FULL from beginning)
    IF approved → ENTER HANDOFF

    state = REVIEW, handoff_to = plan-builder
    WAIT for execution_result

    ENTER REVIEW
    IF success + passed → state=DONE
    IF failed → state=CLARIFY or DESIGN
    IF partial → state=DESIGN
END
```

**Never skip or reverse states.** Allowed rollbacks are embedded in each state's pseudocode.

---

## ROUTE

**Trigger:** No state file, or state is "DONE".

**Announce:** "Entering ROUTE..."

```
BEGIN ROUTE
    /* Step 0: clean slate */
    IF state == "DONE" AND .vega-punk-state.json exists:
        RENAME vega-punk/specs/*.md → *.DONE.md
        DELETE .vega-punk-state.json

    /* Step 1: bug detection first */
    IF message contains bug keywords (`bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`):
        INVOKE root-cause skill

    /* Step 2: classify task type */
    MATCH task type:

    CASE user says "just write code" / "skip design" / "just do it" / "don't overthink":
        state = CONDENSED

    CASE Informational (simple Q&A, definitions, explanations):
        ANSWER directly — no skill check needed
        state = DONE
        EXIT

    CASE Creative/Implementation (build, fix, modify, design, create):
        CHECK for relevant skills (1% Rule)
        state = SCAN

    CASE Ambiguous:
        ASK one question to classify
        IF classified as Informational → see above
        IF classified as Creative/Implementation → see above

    /* Step 3: write state */
    WRITE .vega-punk-state.json:
        { "state": "SCAN", "task": "<user request>", "scan_depth": 0, "transition_count": 1 }
END
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN..."

```
BEGIN SCAN
    /* 1. scope check before refinement */
    IF request describes multiple independent subsystems:
        TELL user to split project
        HELP identify independent pieces and build order
        PROCEED with first sub-project only

    /* 2. check project context */
    READ files, docs, recent commits

    /* 3. skill routing */
    IF scan_depth >= 3:
        SKIP skill routing
    ELSE:
        RUN bash scripts/discover-skills.sh
        MATCH task against skill descriptions
        SELECT ALL relevant skills + note execution order

    /* 4. invoke skills for guidance (NOT implementation) */
    FOR EACH selected skill:
        LOAD skill guidance into context

    /* state write */
    WRITE .vega-punk-state.json:
        state = "CLARIFY"
        ADD: context, selected_skills, scope, skill_selection
        INCREMENT: scan_depth (or set to 1)
        INCREMENT: transition_count
END
```

---

## CLARIFY

**Trigger:** State is CLARIFY.

**Announce:** "Entering CLARIFY..."

```
BEGIN CLARIFY
    IF purpose, constraints, and success criteria are clear:
        TELL: "Requirements are clear. Moving to design."
        EXTRACT purpose, constraints, success from request + SCAN context
        GOTO DESIGN

    /* ask questions one at a time */
    ASK ONE clarifying question (prefer multiple choice)
    FOCUS on: purpose, constraints, success criteria

    IF user says "you decide":
        DOCUMENT assumption
        PROCEED

    /* state write */
    WRITE .vega-punk-state.json:
        state = "DESIGN"
        ADD: requirements = { purpose, constraints, success }
        RESET: scan_depth = 0
        INCREMENT: transition_count
END
```

---

## DESIGN

**Trigger:** State is DESIGN.

**Announce:** "Entering DESIGN... Let's brainstorm the best approach together."

```
BEGIN DESIGN
    /* phase tracking: "brainstorm" → "converge" → "present" */

    /* Phase 1: Brainstorm (collaborative) */
    design_phase = "brainstorm"
    PRESENT 2-3 approaches with trade-offs:
        FOR EACH approach: strengths, costs, risks
        LEAD with recommendation + explain why
    ASK: "Which direction feels right? Or combine elements?"

    IF user rejects:
        TELL: "Revisiting approach..."
        REPEAT Phase 1

    /* Phase 2: Converge (co-create) */
    design_phase = "converge"
    REFINE chosen approach based on user feedback
    COMBINE approaches if user wants
    INTEGRATE user's own ideas
    ITERATE until design feels right

    /* Phase 3: Present (formalize) */
    design_phase = "present"
    PRESENT final design (brief if straightforward, 200-300 words if nuanced):
        Architecture, Components, Data flow, Error handling, Testing
    DESIGN FOR ISOLATION:
        Each unit: one purpose, well-defined interface, independently testable
    FOLLOW existing patterns in codebase:
        Targeted improvements only, no unrelated refactoring
    ASK: "Does this look right so far?"

    IF user changes direction:
        IF fundamental goal change → GOTO CLARIFY
        IF exploring alternatives → STAY in DESIGN, restart Phase 1

    /* state write */
    WRITE .vega-punk-state.json:
        state = "DESIGN_QA"
        ADD: design
        INCREMENT: transition_count
END
```

---

## Reusable QA Pattern

Both DESIGN_QA and SPEC_QA share this structure:

```
BEGIN QA(name, checks, pass_state, fail_state)
    LOOP qa_retries ≤ 3:
        /* Layer 1: Structured Self-Review */
        RUN domain-specific checks from `checks`
        IF any fail:
            FIX failures inline
            RE-RUN self-review

        /* Layer 2: User Secondary Review */
        PRESENT findings: passed / fixed / remaining risks
        WAIT for user decision

        MATCH user response:
        CASE PASS:
            UPDATE qa = { "{name}_status": "PASS", "{name}_retries": N }
            state = pass_state
            WRITE state JSON
            EXIT
        CASE FAIL:
            INCREMENT qa_retries
            UPDATE qa = { "{name}_status": "FAIL", "{name}_retries": qa_retries, "{name}_feedback": "<summary>" }
            state = fail_state
            WRITE state JSON
            EXIT (↩ to previous state for fix, then re-enter QA)

    /* retries exhausted */
    TELL: "[vega-punk] I've hit the retry limit. Please review manually and tell me how to proceed."
    STAY in current QA state
END
```

**Retry limit:** 3 retries max. Beyond that, halt and ask user.

---

## DESIGN_QA

**Trigger:** State is DESIGN_QA.

**Announce:** "Entering DESIGN_QA... awaiting expert review + user secondary review"

```
BEGIN DESIGN_QA
    INVOKE QA("design",
        checks = [
            "Architecture: separation of concerns? units independent?",
            "Technology choices: tools justified? simpler alternative?",
            "Data flow: dependencies acyclic? circular references?",
            "Error handling: what happens when each external call fails?",
            "Edge cases: top 3 ways this could break in production?",
            "Scope creep: unrequested features? remove them."
        ],
        pass_state = DEPENDENCIES,
        fail_state = DESIGN
    )
END
```

---

## DEPENDENCIES

**Trigger:** State is DEPENDENCIES.

**Announce:** "Entering DEPENDENCIES..."

```
BEGIN DEPENDENCIES
    /* Output is INPUT for plan-builder — NOT a plan */

    LIST all components from approved design

    FOR EACH pair of components:
        IF B cannot start until A complete:
            MARK A → B (serial)
        IF A and B independent:
            MARK A ∥ B (parallel)
        IF A ↔ B (bidirectional):
            WARN: merge or separate by abstraction

    IDENTIFY critical path (longest serial chain)
    IDENTIFY parallel groups

    /* Rules:
       Schema → API → Frontend = serial
       Independent UI components = parallel
       Shared types first (serial), then implementations (parallel) */

    IF user changes direction:
        GOTO DESIGN

    /* state write */
    WRITE .vega-punk-state.json:
        state = "SPEC"
        ADD: dependencies = { components, serial, parallel, critical_path }
        INCREMENT: transition_count
END
```

---

## SPEC

**Trigger:** State is SPEC.

**Announce:** "Entering SPEC..."

```
BEGIN SPEC
    /* 1. write spec file */
    WRITE vega-punk/specs/YYYY-MM-DD-<topic>-design.md
    REQUIRED sections:
        Goal, Architecture, Components, Interfaces,
        Data Flow, Error Handling, Testing Plan, Dependency Graph

    /* 2. spec self-review */
    CHECK:
        Placeholder scan: any "TBD", "TODO", vague statements?
        Internal consistency: contradictions between sections?
        Scope check: focused enough for single implementation plan?
        Ambiguity check: any requirement interpretable two ways?
        Dependency check: serial dependencies justified?
    FIX issues inline

    /* 3. user review */
    ASK: "Spec written to <path>. Review it. If it looks good, I'll hand off to planning."
    IF user wants changes:
        FIX → RE-RUN self-review

    /* state write */
    WRITE .vega-punk-state.json:
        state = "SPEC_QA"
        ADD: spec_path, qa = { spec_retries: 0, spec_feedback: "" }
        INCREMENT: transition_count
END
```

---

## SPEC_QA

**Trigger:** State is SPEC_QA.

**Announce:** "Entering SPEC_QA... awaiting expert review + user secondary review"

```
BEGIN SPEC_QA
    INVOKE QA("spec",
        checks = [
            "Completeness: every section implementable? No TBD, TODO, vague statements?",
            "Consistency: any contradictions? dependency graph matches architecture?",
            "Interface contracts: inputs, outputs, data shapes explicitly defined?",
            "Testability: every requirement testable? clear pass/fail criterion?",
            "Dependency accuracy: serial justified? anything parallelizable marked serial?",
            "Scope discipline: unrequested features? remove them."
        ],
        pass_state = HANDOFF,
        fail_state = SPEC
    )
END
```

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode..."

```
BEGIN CONDENSED
    /* 1. minimal spec */
    WRITE: What, Why, How (3 sentences max)

    /* 2. define key interface */
    DEFINE at least one: input → output, or function signature, or API shape

    /* 3. lightweight dependency check */
    NOTE in one sentence: "all parallel" or serial chain (e.g. "backend first, then frontend")

    /* 4. self-review */
    CHECK: any TBD, TODO, ambiguous statements? FIX inline

    /* 5. approval */
    ASK: "I'll implement [X] using [Y]. Proceed?"
    WAIT for user response

    IF user rejects:
        state = SCAN /* go FULL from beginning */
    IF approved:
        /* state write */
        WRITE .vega-punk-state.json:
            state = "HANDOFF"
            ADD: mode = "condensed", spec, dependencies
            INCREMENT: transition_count
END
```

---

## HANDOFF

**Trigger:** State is HANDOFF.

**Announce:** "Design complete, handing off to planning."

```
BEGIN HANDOFF
    READ references/plan-builder/SKILL.md
    FOLLOW its workflow

    /* .vega-punk-state.json is the data contract — plan-builder reads it directly */

    /* state write */
    WRITE .vega-punk-state.json:
        state = "REVIEW"
        ADD: handoff_to = "plan-builder", user_satisfaction = null
        INCREMENT: transition_count
END
```

---

## REVIEW

**Trigger:** State is REVIEW with `execution_result` present.

```
BEGIN REVIEW
    READ execution_result from state file
    COMPARE against requirements.success

    PRESENT summary to user
    MATCH execution_result.status:

    CASE success AND verification passed:
        TELL: "All criteria met. Start a new task?"
    CASE success AND verification failed:
        TELL: "Verification failed. Iterate or redesign?"
    CASE partial:
        TELL: "Partially done. Continue or redesign?"
    CASE failed:
        TELL: "Execution failed. Redesign needed?"

    /* capture satisfaction */
    RECORD user_satisfaction: "satisfied" / "neutral" / "dissatisfied"

    MATCH user response:
    CASE new task:
        APPLY Post-Completion Cleanup
        GOTO ROUTE
    CASE iterate:
        GOTO DESIGN
    CASE redesign:
        GOTO CLARIFY
END
```

## Bootstrap (First Run)

```
BEGIN BOOTSTRAP
    MKDIR vega-punk/specs
    ADD .vega-punk-state.json to .gitignore
    DO NOT gitignore vega-punk/ (spec history is project memory)
    VERIFY scripts/ exists (session-hook.sh, etc.)
    IF missing → inform user
    GOTO ROUTE
END
```

## Self-Recovery Guide

When vega-punk's state becomes corrupted or inconsistent:

```
BEGIN RECOVERY
    READ .vega-punk-state.json
    VALID_STATES = [ROUTE, SCAN, CLARIFY, DESIGN, DESIGN_QA,
                    DEPENDENCIES, SPEC, SPEC_QA, CONDENSED, HANDOFF, REVIEW, DONE]

    MATCH symptom:

    CASE state NOT IN VALID_STATES:
        /* corrupted state value */
        IF task AND context present:
            state = CLARIFY
            TELL: "State file was corrupted. Recovered to CLARIFY."
        ELSE IF only task present:
            state = ROUTE
            TELL: "State file was corrupted. Recovered to ROUTE."
        ELSE:
            DELETE .vega-punk-state.json
            GOTO ROUTE
            TELL: "State file was corrupted. Starting fresh."

    CASE state == DESIGN AND design field missing or empty:
        /* design lost (session interrupted) */
        state = CLARIFY
        TELL: "Design context was lost. Let me re-clarify the requirements."

    CASE state == HANDOFF OR state == REVIEW AND spec_path file missing:
        /* spec was never written or deleted */
        IF design AND dependencies fields present:
            REGENERATE spec from design + dependencies
            state = SPEC
            TELL: "Spec file was lost. I'll regenerate it from our design."
        ELSE:
            state = CLARIFY
            TELL: "Spec file was lost. Let me re-run the design flow."

    CASE state == REVIEW AND (roadmap.json missing OR invalid JSON):
        /* execution interrupted during planning */
        IF spec_path exists AND spec file readable:
            RE-RUN HANDOFF
            TELL: "Execution plan was lost. Regenerating from spec."
        ELSE:
            RECOVER using missing spec case above

    CASE qa.retries == 3:
        /* fundamental design/spec issue, not fixable */
        STOP the loop
        PRESENT failing criteria to user
        ASK: "Failed [N] times. Core issue: [summary].
              (1) restart design, (2) change requirements, (3) proceed despite risk?"
        FOLLOW user direction
        /* DO NOT silently increase retry limits */

    CASE state valid BUT context doesn't match conversation:
        /* stale state from previous unrelated task */
        ASK: "I see state from a previous task: [summary].
              Continue that, or start fresh?"
        IF fresh:
            APPLY Post-Completion Cleanup
            GOTO ROUTE
        IF continue:
            PROCEED from current state

    CASE user says "reset everything":
        /* nuclear option */
        RENAME vega-punk/specs/*.md → *.CANCELLED.md
        DELETE .vega-punk-state.json
        DELETE roadmap.json (if exists)
        DELETE findings.json (if exists)
        DELETE progress.json (if exists)
        TELL: "[vega-punk] Full reset complete. Starting fresh. What shall we build?"
        GOTO ROUTE
END
```

---

## Red Flags — STOP, You're Rationalizing

| If you think...                            | The reality is...                                                           |
|--------------------------------------------|-----------------------------------------------------------------------------|
| "This is too simple to need a design"      | Use CONDENSED mode, don't skip entirely                                     |
| "I'll just do this one thing first"        | Check the state machine BEFORE doing anything                               |
| "Let me explore the codebase first"        | SCAN state handles context. Check first                                     |
| "This doesn't need a formal skill"         | If a skill exists, use it                                                   |
| "The skill is overkill"                    | Simple things become complex. Use CONDENSED, not nothing                    |
| "Dependencies are obvious"                 | Write them down. "Obvious" dependencies cause merge conflicts               |
| "This is just a simple question"           | Questions are tasks. Check for skills.                                      |
| "I need more context first"                | Skill check comes BEFORE clarifying questions.                              |
| "Let me gather information first"          | Skills tell you HOW to gather information.                                  |
| "I remember this skill"                    | Skills evolve. Read the current version.                                    |
| "This doesn't count as a task"             | Action = task. Check for skills.                                            |
| "I know what that means"                   | Knowing the concept ≠ using the skill. Invoke it.                           |
| "This feels productive"                    | Undisciplined action wastes time. Skills prevent this.                      |
| "This is just a draft, we'll polish later" | There are no drafts. Output must be aesthetically first-class — every time. |

## Skill Dependencies

**Sub-skills (referenced):**

- **plan-builder** — [references/plan-builder/SKILL.md](references/plan-builder/SKILL.md) - called from HANDOFF
- **plan-executor** — [references/plan-executor/SKILL.md](references/plan-executor/SKILL.md)  - called from plan-builder's Execution HANDOFF
- **task-dispatcher** — [references/task-dispatcher/SKILL.md](references/task-dispatcher/SKILL.md) — parallel execution
- **root-cause** — [references/root-cause/SKILL.md](references/root-cause/SKILL.md) — on bugs
- **test-first** — [references/test-first/SKILL.md](references/test-first/SKILL.md) — per task
- **verify-gate** — [references/verify-gate/SKILL.md](references/verify-gate/SKILL.md) — before claiming done
- **review-request** — [references/review-request/SKILL.md](references/review-request/SKILL.md) — before merge
- **branch-landing** — [references/branch-landing/SKILL.md](references/branch-landing/SKILL.md) — after all tasks complete
- **parallel-swarm** — [references/parallel-swarm/SKILL.md](references/parallel-swarm/SKILL.md) — independent concurrent tasks
- **worktree-setup** — [references/worktree-setup/SKILL.md](references/worktree-setup/SKILL.md) — isolated workspace for feature work
- **review-intake** — [references/review-intake/SKILL.md](references/review-intake/SKILL.md) — process code review feedback

**Self-recovery:** Built-in — see "Self-Recovery Guide" section above. No external reference needed.

## Key Principles

- **One state at a time** — Never skip states. Use CONDENSED for speed.
- **Dependencies drive execution** — Serial blocks, parallel unblocks.
- **One question at a time** — Don't overwhelm.
- **YAGNI ruthlessly** — Remove unrequested features.
- **Working in existing codebases** — Follow existing patterns. Targeted improvements only. No unrelated refactoring.

## Skill Trigger Reference

Skills vega-punk directly invokes:

| Skill            | When    | Trigger                                                                               |
|------------------|---------|---------------------------------------------------------------------------------------|
| **root-cause**   | ROUTE   | message contains `bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception` |
| **plan-builder** | HANDOFF | `.vega-punk-state.json` has `spec_path` or `spec`                                     |

-**How to choose skills:** During SCAN, you have access to the full list of registered skills (from `discover-skills.sh`). Match the task intent against each skill's description and trigger conditions. Select all relevant skills. You decide the execution order based on the specific task context — don't follow fixed chains. Trust your judgment about what's needed and in what order. 
