---
name: vega-punk
description: "A disciplined AI brain: design before execution. State machine-driven — routes requests, orchestrates skills, designs solutions, delivers plans. 触发词: design first / 先设计再实现 / let's think / 我想做一个 / 帮我构建 / skip design / just do it / 直接写代码 / urgent / hotfix / 报错了 / bug / 重新开始 / new task"
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch"
hooks:
  SessionStart:
    - type: command
      command: "bash skills/vega-punk/scripts/session-hook.sh 2>/dev/null || echo '[vega-punk] Ready. What shall we build?'"
---

# Vega-Punk: Session State Machine

**Purpose:** Enforce design-before-execution for every implementation task. Map causal dependencies so the execution plan maximizes parallelism.

**Boundary:** vega-punk owns design and routing. After HANDOFF, plan-builder takes execution — reads the state file, generates the roadmap, manages implementation. vega-punk stays in REVIEW to validate results against requirements.

**Constants:**

- `STATE_FILE` = `~/.vega-punk/vega-punk-state.json`
- `SPEC_DIR` = `~/.vega-punk/specs/`
- `ROADMAP_FILE` = `~/.vega-punk/roadmap.json`
- `COUNTERS_FILE` = `~/.vega-punk/vega-punk-counters.json`
- `FINDINGS_FILE` = `~/.vega-punk/findings.json`
- `PROGRESS_FILE` = `~/.vega-punk/progress.json`

For **OpenClaw** and **Claude Code**, the workspace is always `~/.vega-punk/` — state, specs, roadmap, and all runtime files live there.

## Quick Start

Describe what you want to build. vega-punk auto-selects the mode:

- **Single feature or Small change** ("add dark mode", "添加XX") → Auto-detected → CONDENSED
- **Complex project** ("build notification system") → FULL: design → QA → dependencies → spec → plan → execute
- **Bug / Error** ("报错了", "not working") → Bug fast-path → CONDENSED with root-cause

Say "just do it" for explicit fast mode, or "let's think about this" to force FULL flow.

See [State Machine](#state-machine) for full flow details.

## How State Works

**Document format:** This document combines pseudocode (exact logic, branching, state transitions) with natural language prompts (intent, principles, constraints). Both carry equal authority. Pseudocode defines WHAT to do and WHEN; prompts define WHY and HOW. Execute pseudocode as mandatory workflow rules, not optional illustrations.

**GOTO semantics:** `GOTO <STATE>` = `MERGE INTO STATE_FILE { state: "<STATE>" }` then exit current block. The state file is always written before control transfers. `EXIT` = write current state to file then end processing for this message.

**On every user message:**

```
BEGIN STATE_RESOLUTION
    READ STATE_FILE

    /* Check these rules in order — stop at the first match */

    1. User says "start over" / "new task" / "forget previous":
       → APPLY Post-Completion Cleanup
       → TELL: "[vega-punk] Starting fresh. What shall we build?"
       → GOTO ROUTE

    2. State is "DONE":
       → ENTER DONE, then EXIT

    3. State file missing:
       → GOTO ROUTE

    4. State is "REVIEW" — check sub-conditions in order, stop at first match:

       | # | Condition | Action |
       |---|-----------|--------|
       | 4a | STATE_FILE.execution_result exists | ENTER REVIEW, then EXIT |
       | 4b | ROADMAP_FILE exists with incomplete steps | RESUME from ROADMAP_FILE current_step, EXIT |
       | 4c | User requests iterate or redesign | Archive ROADMAP_FILE if exists → GOTO DESIGN, EXIT |
       | 4d | None of the above | TELL: "In REVIEW with nothing to review. Start a new task, iterate, or tell me what to do." → WAIT for user input, EXIT |

    5. State file has invalid JSON or state NOT in valid states:
       → APPLY RECOVERY
       → GOTO current state (RECOVERY sets the target; if unclear → GOTO ROUTE)

    6. None of the above (file exists, state is valid):
       → ENTER current state directly
       → DO NOT go back to ROUTE

    /* After routing — always apply these */
    APPLY GlobalGuards
    APPLY StateTransition
END
```

### StateTransition

```
BEGIN StateTransition
    /* Applies to every state change — ALL skills must follow: */
    READ current JSON → merge in memory → CHANGE state → ADD new fields
    NEVER delete existing fields (cross-skill safety)
    INCREMENT transition_count (init to 1 if absent) → WRITE back

    /* State file write rules — ALL skills must follow: */
    1. NEVER overwrite STATE_FILE without reading first — always read, merge in memory, then write back
    2. NEVER delete existing fields — only ADD new fields or UPDATE existing values
    3. If a field was written by another skill (e.g. worktree_path by worktree-setup), preserve it
    4. When in doubt, read the current JSON, add your fields, and write back — never assume you own the entire file
END
```

### GlobalGuards

```
BEGIN GlobalGuards
    /* Loop protection — prevents skill routing loops during SCAN */
    IF state == "SCAN" AND scan_depth >= 3:
        SKIP skill routing → GOTO CLARIFY

    /* Depth lifecycle */
    ON entering SCAN:   INCREMENT scan_depth
    ON entering CLARIFY: RESET scan_depth = 0

    /* Per-phase intermediate data cleanup — prevent unbounded growth */
    /* After each phase completes, compress its intermediate data to 1-sentence summary */
    ON transitioning FROM SCAN:
        COMPRESS domain_considerations → keep only { skill_name: { key_blockers: [], assumptions: [] } }
        /* Remove raw output, keep only structured conclusions */

    ON transitioning FROM DESIGN_QA OR SPEC_QA:
        COMPRESS expert_findings → keep only { skill_name: { verdict: pass/fail, top_3_risks: [] } }
        /* Remove detailed commentary, keep verdict + top risks */

    ON transitioning FROM REVIEW:
        COMPRESS expert_validation → keep only { skill_name: { verdict: pass/fail, top_3_issues: [] } }

    /* Compaction — prevents unbounded state file growth */
    /* Apply when context is under pressure: long conversations, many retries, or large state */
    IF qa.retries > 2 OR transition_count > 8:
        PRESERVE: state, task, context, selected_skills, scope, requirements, design, dependencies, spec_path, phase_skill_mapping, expert_contexts
        COMPRESS qa → { retries: N, last_feedback: "<summary>", status: "FAIL|PASS|CONDITIONAL_PASS" }
        COMPRESS any oversized field not in preserve list → 1-sentence summary
END
```

### Post-Completion Cleanup

```
BEGIN Post-Completion Cleanup
    /* Step 1: save counters BEFORE deleting state file */
    IF STATE_FILE has consecutive_dissatisfied_count:
        WRITE COUNTERS_FILE:
            { "consecutive_dissatisfied_count": value }

    /* Step 2: archive + delete state */
    RENAME SPEC_DIR*.md → *.DONE.md (completed) or *.CANCELLED.md (cancelled)
    DELETE STATE_FILE

    /* On REVIEW → new task: archive specs + preserve counters, then restart ROUTE */
    /* On "start over" / "new task" / "forget previous": also clear counter */
    IF user says "forget previous":
        DELETE COUNTERS_FILE
END
```

**Progress reporting:** At each transition:
> "Entering [STATE]..."

If user asks "where are we?" or "how much left?", print current state and remaining steps.

| State        | FULL Path     | CONDENSED Path |
|--------------|---------------|----------------|
| ROUTE        | 10 states left| 3 states left  |
| SCAN         | 9             | —              |
| CLARIFY      | 8             | —              |
| DESIGN       | 7             | —              |
| DESIGN_QA    | 6             | —              |
| DEPENDENCIES | 5             | —              |
| SPEC         | 4             | —              |
| SPEC_QA      | 3             | —              |
| CONDENSED    | 3             | 3              |
| HANDOFF      | 2             | 2              |
| REVIEW       | 1             | 1              |

**Two execution modes:**

| Mode          | Steps                             | When                                      | State File | Skill Check | Context Strategy |
|---------------|-----------------------------------|-------------------------------------------|------------|-------------|-----------------|
| **CONDENSED** | Minimal spec → Approval → Handoff | Small changes, single features, fast-path | Required   | Full SCAN   | Blockers only   |
| **FULL**      | All 10 states                     | Large/multi-step tasks, ambiguous scope   | Required   | Full SCAN   | Cache + reuse   |

CONDENSED skips DESIGN, DESIGN_QA, DEPENDENCIES, SPEC, SPEC_QA. 4 states remain: CONDENSED → HANDOFF → REVIEW → DONE.

---

## Three Hard Disciplines

These are rules. Do not treat them as suggestions.

### 1. HARD-GATE: No Design, No Execute

Do NOT execute anything — write code, scaffold projects, generate documents, create designs, produce content, modify configurations, invoke any implementation skill, or take any implementation action — until the design has been presented and the user has approved it. This applies to EVERY task regardless of perceived simplicity. A todo list, a single-function utility, a config change, a document, a presentation, a data analysis — all of them. The design can be short (a few sentences for truly simple projects via CONDENSED mode), but you MUST present it and get approval.

### 2. Semantic Skill Matching

Skills are matched by **semantic relevance**, not fuzzy "1% chance". A skill is invoked only when the AI judges it applies based on `skill.name` + `skill.description`:

| Step | What happens |
|------|-------------|
| **Discover** | `discover-skills.sh` returns `{ name, description, source, path }` for all installed skills |
| **Match** | AI reads each skill's `name` + `description` and judges: "Does this skill apply to the user's task?" |
| **Auto-add** | Hard-coded rules add `test-first` (code tasks), `verify-gate` (fast mode), `root-cause` (bug tasks) |

If the skill's description does NOT mention the task domain, **do NOT invoke the skill**.

### 3. Instruction Priority

1. **User's explicit instructions** — highest priority
2. **Skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If a user says "don't use TDD" and a skill says "always use TDD," follow the user. The user is in control.

---

## Core Operating Principles

These govern ALL behavior, regardless of current state:

### Skill Check Comes Before Everything

Skills tell you HOW to explore. Check skills BEFORE gathering context, BEFORE asking questions, BEFORE acting. Never say "I need more context first" — skills tell you how to get it.

**When you invoke a skill, announce it:** "Using [skill] to [purpose]."

**If the skill has a checklist:** Create a TodoWrite task for each item and complete them in order.

**Invoke the skill tool** — don't just read the skill file.

- **Claude Code:** Use the `Skill` tool.
- **OpenClaw:** Use `openclaw skills` command or the platform's skill invocation mechanism.

### Output Is Production

- Every deliverable — spec, design, diagram, config, code, presentation, image — must be production-ready. No exceptions.
- No rough drafts. The first output IS the final output.
- If it wouldn't survive client review, user delivery, or public release, it doesn't leave vega-punk.

### Handle Off-Topic Input

If the user sends input unrelated to the current state's purpose:

1. Briefly answer if it's a simple question
2. Return: "Back to [STATE] — [reminder of where we are]"
3. Resume the current state. Do NOT change state or restart.

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
    IF approved → ENTER HANDOFF (state set by CONDENSED block)

    /* HANDOFF invokes plan-builder, which writes execution_result */
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

**Purpose:** Classify the task and route to the correct entry point.

```
BEGIN ROUTE
    /* Load preserved counters from previous task */
    IF COUNTERS_FILE exists:
        READ consecutive_dissatisfied_count into context
    ELSE:
        INITIALIZE consecutive_dissatisfied_count = 0

    /* Clean slate is handled by STATE_RESOLUTION Post-Completion Cleanup before reaching ROUTE */

    /* Bug detection — always check first (English + Chinese keywords) */
    IF message contains bug keywords (`bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`, `broken`, `报错`, `出错`, `崩溃`, `异常`, `不工作`, `坏了`):
        INVOKE root-cause skill
        /* Auto-fast-path for bugs: skip full design flow */
        GOTO rule 1a below

    /* Classify task — check these rules in order, stop at first match */

    1. **Fast mode** — user says "urgent" / "emergency" / "hotfix" / "prod down" / "critical" / "just do it" / "skip design" / "just write code" / "don't overthink":
       - ADD "verify-gate" TO skills_to_apply (executor will invoke before any success claim)
       - ADD "test-first" TO skills_to_apply (executor will invoke for code implementation)
       - MERGE INTO STATE_FILE: { "state": "CONDENSED", "task": "<user request>", "mode": "fast", "transition_count": 1 }
       - GOTO CONDENSED

    1a. **Bug fast-path** — triggered by bug detection above:
        - ADD "root-cause" TO skills_to_apply (already invoked above)
        - ADD "verify-gate" TO skills_to_apply
        - MERGE INTO STATE_FILE: { "state": "CONDENSED", "task": "<user request>", "mode": "fast", "transition_count": 1 }
        - GOTO CONDENSED

    1b. **Simple task auto-detect** — single feature or small change request:
        /* Heuristic: task involves ONE component change, no new subsystems */
        /* Signals: "add dark mode", "add button", "change color", "update text", "fix typo", "添加XX", "修改XX", "改成XX" */
        IF task scope is clearly single-component AND no architectural dependency:
            ADD "verify-gate" TO skills_to_apply
            ADD "test-first" TO skills_to_apply (if code involved)
            MERGE INTO STATE_FILE: { "state": "CONDENSED", "task": "<user request>", "mode": "condensed", "transition_count": 1 }
            GOTO CONDENSED

    2. **Informational** — simple Q&A, definitions, explanations:
       - ANSWER directly — no skill check needed
       - state = DONE, EXIT

    3. **Creative/Implementation** — build, fix, modify, design, create:
       - CHECK for relevant skills (signal-driven matching)
       - MERGE INTO STATE_FILE: { "state": "SCAN", "task": "<user request>", "scan_depth": 0, "transition_count": 1 }
       - Enter SCAN

    4. **Ambiguous** — can't classify:
       - ASK one question to classify
       - If Informational → see rule 2
       - If Creative/Implementation → see rule 3
END
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN..."

**Purpose:** Discover project context and select relevant skills.

```
BEGIN SCAN
    /* 1. scope check before refinement */
    IF request describes multiple independent subsystems:
        TELL user to split project
        HELP identify independent pieces and build order
        PROCEED with first sub-project only

    /* 2. check project context */
    READ files, docs, recent commits

    /* 3. skill discovery — semantic matching on name + description */
    IF scan_depth >= 3:
        SKIP skill routing
    ELSE:
        /* Step A: Discover available skills */
        RUN bash skills/vega-punk/scripts/discover-skills.sh
        IF exit code == 1 (hard failure — no JSON runtime):
            TELL: "[SCAN] Skill discovery failed — no JSON runtime available. Proceeding without skill guidance."
            PARSE system prompt skill list as fallback → available_skills
        IF exit code == 2 (partial success):
            PROCEED with discovered skills + note warnings in context
        IF exit code == 0 (success):
            PARSE JSON output → available_skills

        /* Step B: Semantic matching — AI decides which skills match */
        /* Available fields per skill: { name, description, source, path } */
        /* Match user task intent against skill.name + skill.description semantically */
        matched_skills = []
        FOR EACH skill IN available_skills:
            /* Check: does this skill's description say it applies to this task? */
            /* The AI reads skill.name + skill.description and judges relevance */
            IF skill APPLIES TO task_intent:
                ADD skill.name TO matched_skills

        /* Step C: Auto-add rules (hard-coded, always fire) */
        IF mode == "fast" AND "verify-gate" NOT IN matched_skills:
            ADD "verify-gate" TO matched_skills
        IF task involves code AND "test-first" NOT IN matched_skills:
            ADD "test-first" TO matched_skills
        IF message contains bug keywords AND "root-cause" NOT IN matched_skills:
            ADD "root-cause" TO matched_skills

        /* Step D: Deduplicate */
        DEDUP matched_skills by name

    /* 4. invoke skills for guidance (NOT implementation) — ONE-TIME cache */
    domain_considerations = {}
    expert_contexts = {}
    FOR EACH selected skill:
        INVOKE skill via Skill tool
        /* Guidance mode only — do NOT execute implementation steps from the skill */
        /* Use skill output to populate context, scope, and selected_skills fields */
        /* Also extract: what ambiguities in this skill's domain would block a good solution? */
        EXTRACT domain-specific considerations from skill output
        IF ambiguities identified:
            domain_considerations[skill.name] = { inputs_needed, ambiguities, considerations }
        /* CRITICAL: cache the skill's expertise summary, NOT the full SKILL.md */
        expert_contexts[skill.name] = {
            expertise_domains: <what this skill knows>,
            quality_standards: <what "good" looks like in this domain>,
            common_pitfalls: <typical mistakes to avoid>
        }

    /* state write */
    MERGE INTO STATE_FILE:
        state = "CLARIFY"
        ADD: context, scope
        ADD: domain_considerations (if populated by step 4)
        ADD: expert_contexts (if populated — used by QA/REVIEW instead of re-invoking skills)
        ADD: selected_skills = {
            "planner": "plan-builder",
            "executor": <inferred from skill types — execution-oriented skills → "task-dispatcher" or "plan-executor">,
            "reviewer": <if review-oriented skills found → "review-request", else null>,
            "alternatives": [<other plausible executors identified during skill matching>]
        }
        INCREMENT: scan_depth (or set to 1)
        INCREMENT: transition_count
END
```

---

## CLARIFY

**Trigger:** State is CLARIFY.

**Announce:** "Entering CLARIFY..."

**Purpose:** Extract requirements — purpose, constraints, success criteria — one question at a time. **Skill-driven:** selected skills are activated as domain experts to identify what needs clarification; vega-punk synthesizes their expertise into user-facing questions.

```
BEGIN CLARIFY
    /* 0. Skill-driven clarification — activate matched skills as domain experts */
    IF selected_skills NOT empty AND domain_considerations NOT IN STATE_FILE:
        FOR EACH skill_name IN selected_skills:
            INVOKE skill_name via Skill tool (if not already in context)
            ASK skill: "Based on the user's task, what domain-specific dimensions need clarification?"
            EXTRACT: required_inputs, key_ambiguities, expert_considerations
            COLLECT INTO: domain_considerations[skill_name] = { inputs, ambiguities, considerations }

    /* 1. Build question pool */
    IF domain_considerations NOT empty:
        BUILD question_pool FROM domain_considerations
        CLASSIFY questions:
            - BLOCKERS: "would block a quality solution" — must ask (platform, auth, data model, core API)
            - PREFERENCES: "affects implementation style" — can assume (colors, animation, naming)
        PRIORITIZE: BLOCKERS first, then PREFERENCES
        DEDUP overlapping questions across skills
    ELSE:
        question_pool = []
        /* Fallback: ask vega-punk's own clarifying questions */
        IF purpose unclear: APPEND "What is the primary goal?" to question_pool
        IF constraints unclear: APPEND "Any technical or time constraints?" to question_pool
        IF success unclear: APPEND "What does 'done' look like?" to question_pool

    /* 2. Ask questions one at a time — max 3 rounds */
    clarify_rounds = 0
    WHILE question_pool NOT empty AND clarify_rounds < 3:
        clarify_rounds += 1
        ASK single question from question_pool (BLOCKER first) → prefer multiple choice
        REMOVE asked question from pool
        WAIT for answer

        /* Match user's answer: */
        CASE "you decide" / "你决定":
            DOCUMENT assumption for THIS dimension
            /* Ask if user wants to skip remaining questions */
            ASK: "I'll assume [assumption]. Skip remaining questions and move to design?"
            WAIT for answer
            CASE "yes" / "好" / "skip":
                DOCUMENT remaining assumptions for all unanswered dimensions
                BREAK → PROCEED to step 3
            CASE else:
                CONTINUE to next question
        CASE user answers the question:
            RECORD answer → remove from unanswered pool
            IF user's answer reveals new ambiguity:
                APPEND clarifying follow-up to question_pool (max 1)
        CASE user rejects answering:
            DOCUMENT reasonable assumption
            BREAK

    /* 3. Finalize requirements and transition */
    TELL: "Requirements captured. Moving to design."
    EXTRACT purpose, constraints, success from:
        - User's original request
        - SCAN context
        - All answered questions + documented assumptions

    /* state write */
    MERGE INTO STATE_FILE:
        state = "DESIGN"
        ADD: requirements = { purpose, constraints, success }
        ADD: domain_considerations (if populated)
        RESET: scan_depth = 0
        INCREMENT: transition_count
END
```

---

## DESIGN

**Trigger:** State is DESIGN.

**Announce:** "Entering DESIGN... Let's brainstorm the best approach together."

**Purpose:** Co-create the solution architecture with the user — explore, converge, formalize.

```
BEGIN DESIGN
    /* re-entry from DESIGN_QA FAIL: reset retries if design substantively changed */
    IF qa.design_status == "FAIL":
        PREVIOUS_DESIGN = design from last iteration
        RE-DO design phases (brainstorm → converge → present)
        IF resulting design differs substantively from PREVIOUS_DESIGN:
            RESET qa.design_retries = 0
        CLEAR qa.design_status

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
    MERGE INTO STATE_FILE:
        state = "DESIGN_QA"
        ADD: design
        INCREMENT: transition_count
END
```

---

## Reusable QA Protocol

Both DESIGN_QA and SPEC_QA follow the same 3-layer review pattern. This protocol defines the shared logic.

```
/* QA_PROTOCOL — called by DESIGN_QA and SPEC_QA
   Parameters:
     qa_type:     "design" | "spec"
     review_items: domain-specific self-review checklist
     expert_q:     what to ask each expert (design vs spec)
     pass_state:   next state on PASS
     fail_state:   next state on FAIL
     retry_field:  "design_qa_retries" | "spec_qa_retries"
     qa_field:     "design_status" | "spec_status"
*/

BEGIN QA_PROTOCOL(qa_type, review_items, expert_q, pass_state, fail_state, retry_field, qa_field)
    LOOP retry_field ≤ 3:
        /* Layer 1: Expert Review — prefer cached contexts */
        IF expert_contexts NOT empty:
            FOR EACH skill_name IN expert_contexts:
                REVIEW {qa_type} against expert_contexts[skill_name]:
                    - expertise_domains, quality_standards, common_pitfalls
                COLLECT: expert_findings[skill_name] = { passed, risks, recommendations }
        ELSE IF selected_skills NOT empty:
            FOR EACH skill_name IN selected_skills:
                INVOKE skill_name via Skill tool
                ASK skill: expert_q
                COLLECT: expert_findings[skill_name] = { passed, risks, recommendations }

        /* Layer 2: Structured Self-Review */
        CHECK review_items
        MERGE self-review results with expert_findings
        IF any fail: FIX inline → RE-RUN self-review

        /* Layer 3: User Secondary Review */
        PRESENT summary: expert findings + self-review + bottom line
        WAIT for user decision

        MATCH user response:
        CASE PASS:
            UPDATE qa = { qa_field: "PASS", retry_field: N, expert_review: expert_findings }
            MERGE INTO STATE_FILE: state = pass_state, EXIT
        CASE CONDITIONAL_PASS:
            RECORD conditions: [must-fix items]
            IF conditions are specific and actionable:
                FIX inline
                IF all conditions resolved:
                    UPDATE qa = { qa_field: "PASS", retry_field: N, expert_review: expert_findings, conditional_fixes: conditions }
                    MERGE INTO STATE_FILE: state = pass_state, EXIT
                ELSE:
                    INCREMENT retry_field
                    UPDATE qa = { qa_field: "FAIL", retry_field: retry_field, qa_feedback: "Conditionals not resolved", expert_review: expert_findings }
                    MERGE INTO STATE_FILE: state = fail_state, EXIT
            ELSE:
                INCREMENT retry_field
                UPDATE qa = { qa_field: "FAIL", retry_field: retry_field, qa_feedback: "<summary>", expert_review: expert_findings }
                MERGE INTO STATE_FILE: state = fail_state, EXIT
        CASE FAIL:
            INCREMENT retry_field
            IF qa_type == "spec" AND qa_feedback contains "architecture" OR "wrong pattern" OR "fundamental":
                MERGE INTO STATE_FILE: state = "DESIGN"
            ELSE:
                UPDATE qa = { qa_field: "FAIL", retry_field: retry_field, qa_feedback: "<summary>", expert_review: expert_findings }
                MERGE INTO STATE_FILE: state = fail_state
            EXIT

    /* retries exhausted */
    TELL: "[vega-punk] Retry limit hit. Expert findings: [summary]. Review manually."
    STAY in current state
END
```

---

## DESIGN_QA

**Trigger:** State is DESIGN_QA.

**Announce:** "Entering DESIGN_QA... invoking expert review + user confirmation"

**Purpose:** Validate design quality through skill-driven expert review and user confirmation.

```
BEGIN DESIGN_QA
    /* Re-entry: reset retries if design substantively changed */
    IF qa.design_status == "FAIL":
        PREVIOUS_DESIGN = design from last iteration
        RE-DO design phases (brainstorm → converge → present)
        IF resulting design differs substantively from PREVIOUS_DESIGN:
            RESET qa.design_retries = 0
        CLEAR qa.design_status

    CALL QA_PROTOCOL(
        qa_type = "design",
        review_items = [
            - Architecture: separation of concerns? units independent?
            - Technology choices: tools justified? simpler alternative?
            - Data flow: dependencies acyclic? circular references?
            - Error handling: what happens when each external call fails?
            - Edge cases: top 3 ways this could break in production?
            - Scope creep: unrequested features? remove them.
        ],
        expert_q = "Review this design against your domain expertise. What risks, gaps, or anti-patterns do you see?",
        pass_state = "DEPENDENCIES",
        fail_state = "DESIGN",
        retry_field = "design_qa_retries",
        qa_field = "design_status"
    )
END
```

---

## DEPENDENCIES

**Trigger:** State is DEPENDENCIES.

**Announce:** "Entering DEPENDENCIES..."

**Purpose:** Map serial and parallel dependencies between design components for optimal execution ordering.

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
    MERGE INTO STATE_FILE:
        state = "SPEC"
        ADD: dependencies = { components, serial, parallel, critical_path }
        /* Note: phase_skill_mapping will be populated by SPEC phase from Skill Mapping section */
        INCREMENT: transition_count
END
```

---

## SPEC

**Trigger:** State is SPEC.

**Announce:** "Entering SPEC..."

**Purpose:** Write an unambiguous, testable, implementation-ready specification.

```
BEGIN SPEC
    /* re-entry from SPEC_QA FAIL: reset retries if spec substantively changed */
    IF qa.spec_status == "FAIL":
        PREVIOUS_SPEC = spec from last iteration
        RE-DO spec writing + self-review
        IF resulting spec differs substantively from PREVIOUS_SPEC:
            RESET qa.spec_retries = 0
        CLEAR qa.spec_status

    /* 0. Skill-driven spec enrichment — let experts dictate spec sections */
    IF expert_contexts NOT empty:
        FOR EACH skill_name IN expert_contexts:
            DERIVE required spec sections from expert_contexts[skill_name]:
                - expertise_domains → what sections must exist
                - quality_standards → what acceptance criteria to include
                - common_pitfalls → what constraints/edge cases to document
            COLLECT INTO: spec_sections[skill_name] = { required_sections, acceptance_criteria, constraints }

    /* 1. write spec file */
    WRITE SPEC_DIR/YYYY-MM-DD-<topic>-design.md
    REQUIRED sections:
        Goal, Architecture, Components, Interfaces,
        Data Flow, Error Handling, Testing Plan, Dependency Graph,
        Skill Mapping
    IF spec_sections NOT empty:
        MERGE spec_sections into spec — add skill-specific sections
        e.g. UI skills → add "Responsive Breakpoints", "Interaction States", "Animation Specs"
        e.g. test-first → add "Test Coverage Targets", "Boundary Cases"
        e.g. security skills → add "Auth Flow", "Data Protection"

    /* Skill Mapping — required section in spec document */
    /* For EACH implementation phase/component, specify: */
    /*   - Phase name → SKILL name(s) to invoke during execution */
    /*   - Example: "User auth module" → test-first, verify-gate */
    /*              "Dashboard UI" → frontend-design, ui-ux-pro-max, verify-gate */
    /*   - Bug fix phases → root-cause, test-first, verify-gate */
    /* This section is READ by plan-builder and injected into executor prompts */

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
        IF user identifies fundamental design issue (architecture wrong, wrong pattern, missing component):
            GOTO DESIGN
        FIX → RE-RUN self-review

    /* state write */
    MERGE INTO STATE_FILE:
        state = "SPEC_QA"
        ADD: spec_path, phase_skill_mapping
        ADD: qa = { spec_retries: 0, spec_feedback: "" }
        INCREMENT: transition_count
END
```

---

## SPEC_QA

**Trigger:** State is SPEC_QA.

**Announce:** "Entering SPEC_QA... invoking expert review + user confirmation"

**Purpose:** Validate spec completeness, consistency, and implementability through skill-driven expert review and user confirmation.

```
BEGIN SPEC_QA
    /* Re-entry: reset retries if spec substantively changed */
    IF qa.spec_status == "FAIL":
        PREVIOUS_SPEC = spec from last iteration
        RE-DO spec writing + self-review
        IF resulting spec differs substantively from PREVIOUS_SPEC:
            RESET qa.spec_retries = 0
        CLEAR qa.spec_status

    CALL QA_PROTOCOL(
        qa_type = "spec",
        review_items = [
            - Completeness: every section implementable? No TBD, TODO, vague statements?
            - Consistency: any contradictions? dependency graph matches architecture?
            - Interface contracts: inputs, outputs, data shapes explicitly defined?
            - Testability: every requirement testable? clear pass/fail criterion?
            - Dependency accuracy: serial justified? anything parallelizable marked serial?
            - Scope discipline: unrequested features? remove them.
            - Skill Mapping: every phase has at least one skill assigned? skills actually exist?
        ],
        expert_q = "Review this spec against your domain expertise. Is it complete, implementable, and unambiguous? What's missing or vague?",
        pass_state = "HANDOFF",
        fail_state = "SPEC",
        retry_field = "spec_qa_retries",
        qa_field = "spec_status"
    )
END
```

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode..."

**Purpose:** Fast-path design for simple tasks — minimal spec, single approval, handoff.

```
BEGIN CONDENSED
    /* 0. extract requirements — skill-driven (CONDENSED bypasses CLARIFY) */
    IF selected_skills NOT empty AND domain_considerations NOT IN STATE_FILE:
        FOR EACH skill_name IN selected_skills:
            INVOKE skill_name via Skill tool (if not already in context)
            EXTRACT domain-specific ambiguities → domain_considerations[skill_name]

    EXTRACT purpose, constraints, success criteria from user request + SCAN context (if available)
    IF domain_considerations NOT empty:
        BUILD question_pool FROM domain_considerations
        CLASSIFY questions:
            - BLOCKERS: "would block a quality solution" (e.g., platform, auth method, data model)
            - PREFERENCES: "affects implementation style" (e.g., color scheme, animation, tech preference)
        ASK only BLOCKER questions (max 2) → prefer multiple choice
        FOR PREFERENCES → make reasonable assumptions and document them
        IF any BLOCKER dimension still unclear after 2 questions → ASK one more
    ELSE:
        IF any dimension unclear → ASK one question, prefer multiple choice

    /* 1. minimal spec */
    WRITE: What, Why, How (3 sentences max)

    /* 2. define key interface */
    DEFINE at least one: input → output, or function signature, or API shape

    /* 3. lightweight dependency check */
    NOTE in one sentence: "all parallel" or serial chain (e.g. "backend first, then frontend")

    /* 4. skill mapping — which skills executor should invoke per step */
    /* Add skills relevant to this task to phase_skill_mapping */
    /* e.g. code → test-first, verify-gate; bug fix → root-cause; UI → ui-ux-pro-max */

    /* 5. self-review */
    CHECK: any TBD, TODO, ambiguous statements? FIX inline

    /* 6. approval checkpoint — must get explicit user agreement before handoff */
    PRESENT: summary of what will be built, how, and which skills will be invoked
    ASK: "I'll implement [X] using [Y]. Proceed?"
    WAIT for user response

    IF user rejects:
        RESET scan_depth = 0
        state = SCAN /* go FULL from beginning */
    IF user says "modify" / "change" / "调整":
        /* Treat as reject — incorporate feedback and re-present */
        REFINE based on user feedback → REPEAT step 6 (max 2 refine cycles)
    IF approved:
        /* state write */
        MERGE INTO STATE_FILE:
            state = "HANDOFF"
            ADD: mode = "condensed", spec, dependencies
            ADD: requirements = { purpose, constraints, success } /* extracted in step 0 — preserve for plan-builder verification */
            ADD: phase_skill_mapping = <skills mapped in step 4>
            INCREMENT: transition_count
END
```

---

## HANDOFF

**Trigger:** State is HANDOFF.

**Announce:** "Design complete, handing off to planning."

**Purpose:** Transfer approved design to plan-builder for execution planning.

```
BEGIN HANDOFF
    /* 0. validate data contract before handoff */
    REQUIRED_FIELDS = ["task", "requirements", "mode"]
    IF mode == "full":
        REQUIRED_FIELDS += ["design", "dependencies", "spec_path"]
    IF mode == "condensed":
        REQUIRED_FIELDS += ["spec"]
    FOR EACH field IN REQUIRED_FIELDS:
        IF field NOT IN STATE_FILE OR STATE_FILE[field] is empty:
            TELL: "[vega-punk] Missing required field: [field]. Cannot hand off."
            STAY in current state (DESIGN or SPEC_QA)
            EXIT

    /* 0.5. check if worktree isolation is needed */
    IF task benefits from isolation (multi-file changes, feature branch work):
        INVOKE worktree-setup via Skill tool
        IF worktree-setup succeeds:
            MERGE worktree_path into STATE_FILE

    /* 0.6. attach skills to apply during execution */
    /* Preserve existing skills_to_apply (e.g. from Fast mode in ROUTE) */
    IF skills_to_apply NOT IN STATE_FILE:
        MERGE INTO STATE_FILE: skills_to_apply = []
    IF mode == "fast" AND "verify-gate" NOT IN skills_to_apply:
        ADD "verify-gate" TO skills_to_apply
    IF implementation involves code AND "test-first" NOT IN skills_to_apply:
        ADD "test-first" TO skills_to_apply

    /* Use Skill tool directly — do NOT rely on trigger phrase matching */
    INVOKE plan-builder via Skill tool
    IF invocation fails:
        TELL: "[vega-punk] Failed to invoke plan-builder. Check that the skill is available."
        STAY in HANDOFF
        EXIT
    FOLLOW its workflow

    /* STATE_FILE is the data contract — plan-builder reads it directly */
    /* NOTE to plan-builder: phase_skill_mapping maps each implementation phase/component to the SKILL(s) that executor MUST invoke.
       Write this into roadmap.json step instructions so the executor knows exactly which skills to use per step. */
    /* Data contract schema (plan-builder MUST read these fields):
       {
         "task": string,                    // user's original request
         "mode": "full"|"condensed"|"fast",
         "requirements": {                   // extracted during CLARIFY or CONDENSED step 0
           "purpose": string,
           "constraints": string[],
           "success": string[]
         },
         "design": object|null,             // FULL mode: architecture from DESIGN phase
         "dependencies": object|null,       // FULL mode: { components, serial, parallel, critical_path }
         "spec_path": string|null,          // FULL mode: path to spec file
         "spec": object|null,               // CONDENSED mode: inline spec (what/why/how)
         "phase_skill_mapping": object,     // { "phase_name": ["skill-1", "skill-2"] } — executor MUST invoke these per phase/step
         "skills_to_apply": string[],        // global skills applied to ALL steps (e.g. ["verify-gate", "test-first"]) — executor invokes throughout
         "selected_skills": {              // skills identified during SCAN
           "planner": "plan-builder",       // always plan-builder when coming from vega-punk
           "executor": string|null,         // "plan-executor" | "task-dispatcher" | null
           "reviewer": string|null,         // "review-request" | null
           "alternatives": string[]         // alternative executors identified during SCAN
         },
         "worktree_path": string|null,      // set by worktree-setup if isolation needed
         "context": object|null,             // project context from SCAN
         "domain_considerations": object,    // { skill_name: { inputs, ambiguities, considerations } } — extracted by skills during CLARIFY
         "expert_contexts": object           // { skill_name: { expertise_domains, quality_standards, common_pitfalls } } — cached in SCAN, used by QA/REVIEW
       }
    */

    /* state write */
    MERGE INTO STATE_FILE:
        state = "REVIEW"
        ADD: handoff_to = "plan-builder", user_satisfaction = null
        INCREMENT: transition_count
END
```

---

## REVIEW

**Trigger:** State is REVIEW with `execution_result` present.

**Announce:** "Entering REVIEW... invoking expert validation"

**Purpose:** Validate execution against requirements through skill-driven expert review. Decide: done, iterate, or redesign.

```
BEGIN REVIEW
    /* Guard: execution_result missing — plan was interrupted or didn't complete */
    IF execution_result NOT IN STATE_FILE:
        TELL: "[vega-punk] REVIEW state but no execution_result. Plan may have been interrupted."
        ASK: "(1) wait for result, (2) redesign, (3) start new task"
        WAIT for user choice
        CASE (1) wait for result → STAY in REVIEW, EXIT
        CASE (2) redesign → Archive ROADMAP_FILE → GOTO DESIGN, EXIT
        CASE (3) new task → APPLY Post-Completion Cleanup → GOTO ROUTE, EXIT

    /* Layer 1: Expert Validation — prefer cached contexts, re-invoke only if needed */
    expert_validation = {}
    IF expert_contexts NOT empty:
        /* Use SCAN-cached expertise — no need to reload full SKILL.md */
        FOR EACH skill_name IN expert_contexts:
            REVIEW execution_result against expert_contexts[skill_name]:
                - quality_standards: does result meet the skill's quality bar?
                - common_pitfalls: does result fall into known mistakes?
                - expertise_domains: does result cover all essentials in this domain?
            COLLECT: expert_validation[skill_name] = { passed, issues, recommendations }
    ELSE IF selected_skills NOT empty:
        /* Fallback: no cached context, re-invoke skills */
        FOR EACH skill_name IN selected_skills:
            INVOKE skill_name via Skill tool (if not already in context)
            ASK skill: "Review the execution result against the original requirements and your domain expertise. Did the implementation meet quality standards? What's missing, broken, or suboptimal?"
            COLLECT: expert_validation[skill_name] = { passed, issues, recommendations }

    /* Layer 2: Compare against requirements */
    READ execution_result from STATE_FILE
    COMPARE against requirements.success
    MERGE expert_validation into review analysis

    /* Layer 3: Present summary to user */
    PRESENT summary:
        - Requirements check: [which success criteria met / not met]
        - Expert validation: [which skills reviewed, pass/fail per skill, key issues]
        - Overall verdict: success / partial / failed

    /* capture satisfaction BEFORE routing — always ask, never skip */
    RECORD user_satisfaction: "satisfied" / "neutral" / "dissatisfied"

    /* update consecutive dissatisfaction counter */
    IF user_satisfaction == "dissatisfied": INCREMENT consecutive_dissatisfied_count
    ELSE: RESET consecutive_dissatisfied_count = 0

    /* persist counter */
    WRITE COUNTERS_FILE: { "consecutive_dissatisfied_count": value }

    /* Find the matching row — check in order, stop at first match */
    /* expert_validation informs the classification */

    | # | Condition | Message to user | Recommend |
    |---|-----------|-----------------|-----------|
    | 1 | success + verification passed + expert validation passed + satisfied | "All criteria met. Expert review: no issues flagged." | DONE (auto-complete) |
    | 2 | success + verification passed + expert flagged concerns + satisfied | "Criteria met. Expert flagged: [summary]. Acceptable?" | DONE (if user confirms) or DESIGN |
    | 3 | success + verification passed + dissatisfied | "Criteria met but you're not happy — what's missing?" | CLARIFY |
    | 4 | success + verification failed | "Implementer reported success but verification failed." | DESIGN |
    | 5a | partial + missing indicates unclear requirements ("ambiguous spec", "unclear requirement") | "Partially done — requirements were unclear." | CLARIFY |
    | 5b | partial + missing indicates design gap ("architecture issue", "wrong pattern", "component missing") | "Partially done — design gap detected." | DESIGN |
    | 5c | partial + unclear cause | "Partially done." | DESIGN |
    | 6a | failed + notes indicate requirement ambiguity ("ambiguous", "unclear requirement", "spec contradiction", "missing spec") | "Execution failed due to unclear requirements." | CLARIFY |
    | 6b | failed + notes indicate architectural issue ("architecture", "wrong pattern", "fundamental", "wrong approach", "redesign") | "Execution failed due to design problem." | DESIGN |
    | 6c | failed + generic (no clear type) | "Execution failed." | DESIGN |

    /* Rule 1 is the only auto-complete path — skip user confirmation */
    IF matched rule 1: MERGE INTO STATE_FILE: { "state": "DONE" }, EXIT

    /* For rules 2-12: tell the message, then ask user to confirm or override */
    TELL: [Message from matched row]

    IF consecutive_dissatisfied_count >= 3:
        TELL: "[vega-punk] Last 3 tasks dissatisfied. Let's pause and align on process."
        ASK: "Should I change approach? (1) more clarification upfront, (2) tighter QA, (3) different workflow"
        WAIT for user response

    /* archive old roadmap before any re-entry */
    IF ROADMAP_FILE exists: RENAME ROADMAP_FILE → roadmap.ARCHIVED.json

    ASK: "Recommended next step: [Recommend from matched row]. (1) proceed, (2) iterate on design, (3) redesign from scratch, (4) new task?"
    MATCH user choice:
    CASE (1) proceed → GOTO [Recommend from matched row]
    CASE (2) iterate → GOTO DESIGN
    CASE (3) redesign → GOTO CLARIFY
    CASE (4) new task → APPLY Post-Completion Cleanup → GOTO ROUTE
END
```

---

## DONE

**Trigger:** State is DONE.

**Announce:** (none — task complete)

**Purpose:** Terminal state. Task finished, resources cleaned up.

```
BEGIN DONE
    APPLY Post-Completion Cleanup
    WAIT for new user request
    GOTO ROUTE
END
```

---

## Bootstrap (First Run)

```
BEGIN BOOTSTRAP
    MKDIR ~/.vega-punk/specs
    VERIFY skills/vega-punk/scripts/ exists (session-hook.sh, discover-skills.sh)
    IF missing → inform user
    GOTO ROUTE
END
```

---

## Self-Recovery Guide

When vega-punk's state becomes corrupted or inconsistent:

```
BEGIN RECOVERY
    READ STATE_FILE
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
            DELETE STATE_FILE
            GOTO ROUTE
            TELL: "State file was corrupted. Starting fresh."

    CASE state == DESIGN AND design field missing or empty:
        /* design lost (session interrupted) */
        state = CLARIFY
        TELL: "Design context was lost. Let me re-clarify the requirements."

    CASE state == DESIGN_QA OR state == SPEC_QA AND expert_contexts missing:
        /* cached expertise lost — will fall back to re-invoking skills */
        PROCEED from current state (QA layers have fallback to re-invoke skills)

    CASE state == HANDOFF OR state == REVIEW AND spec_path file missing:
        /* spec was never written or deleted */
        IF design AND dependencies fields present:
            REGENERATE spec from design + dependencies
            state = SPEC
            TELL: "Spec file was lost. I'll regenerate it from our design."
        ELSE:
            state = CLARIFY
            TELL: "Spec file was lost. Let me re-run the design flow."

    CASE state == REVIEW AND (ROADMAP_FILE missing OR invalid JSON):
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
        RENAME SPEC_DIR*.md → *.CANCELLED.md
        DELETE STATE_FILE
        DELETE ROADMAP_FILE (if exists)
        DELETE FINDINGS_FILE (if exists)
        DELETE PROGRESS_FILE (if exists)
        TELL: "[vega-punk] Full reset complete. Starting fresh. What shall we build?"
        GOTO ROUTE
END
```

---

## Red Flags — STOP, You're Rationalizing

| If you think...                            | The reality is...                                                          |
|--------------------------------------------|----------------------------------------------------------------------------|
| "This is too simple to need a design"      | Use CONDENSED, don't skip                                                  |
| "I'll just do this one thing first"        | Check the state machine BEFORE acting                                      |
| "Let me explore the codebase first"        | SCAN handles context gathering                                             |
| "This doesn't need a formal skill"         | Check description — if it doesn't mention your task, you're right. Don't invoke. |
| "The skill is overkill"                    | Use CONDENSED, not nothing                                                 |
| "Dependencies are obvious"                 | Write them down. "Obvious" causes merge conflicts                          |
| "This is just a simple question"           | Questions are tasks. Check skill descriptions.                             |
| "I need more context first"                | Skill check comes BEFORE clarification                                     |
| "Let me gather information first"          | Skill descriptions tell you HOW — if applicable                          |
| "I remember this skill"                    | Skills evolve. Read the current description.                               |
| "This doesn't count as a task"             | Action = task. Check skill descriptions.                                   |
| "I know what that means"                   | Knowing the concept ≠ description matches your task                        |
| "This feels productive"                    | Undisciplined action wastes time. Read descriptions before invoking.       |
| "This is just a draft, we'll polish later" | No drafts. First output IS the final output.                               |
| "I'll ask all my questions at once"        | CLARIFY enforces one question at a time. Batch questions = batch confusion |
| "This bug needs the full flow"             | Fast mode exists — prod down → CONDENSED, diagnose → FULL                  |

**Self-recovery:** Built-in — see "Self-Recovery Guide" section above. No external reference needed.

## Key Principles

- **One state at a time** — Never skip states. CONDENSED for speed.
- **Dependencies drive execution** — Serial blocks, parallel unblocks.
- **One question at a time** — Don't overwhelm.
- **YAGNI ruthlessly** — Remove unrequested features.
- **Follow existing patterns** — Targeted improvements only. No unrelated refactoring.
- **Skill orchestration** — Discover skills via script, read name + description, judge semantic relevance. No signal/table matching needed.

## Skill Trigger Reference

### Discovery

`discover-skills.sh` scans platform dirs + project-local skills → outputs `{ name, description, source, path }`.
This is the **only** source of available skills. No external registry.

### Matching

The AI judges each skill's relevance by reading `name` + `description` against the user's task intent.
Auto-add rules always fire: fast mode → `verify-gate`, code → `test-first`, bug → `root-cause`.

### Direct Invokes (vega-punk calls these explicitly)

| Skill            | When    | How                                                                                   |
|------------------|---------|---------------------------------------------------------------------------------------|
| **root-cause**   | ROUTE   | message contains `bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception` |
| **worktree-setup** | HANDOFF | task needs isolation (multi-file changes, feature branch)                           |
| **plan-builder** | HANDOFF | via Skill tool — NOT trigger phrase                                                   |

All other skills are matched by semantic reading of name + description during SCAN, or added via auto-add rules. Skills whose descriptions do not match the task are NOT invoked.

> ### How to choose skills — SEMANTIC MATCHING
> 1. `discover-skills.sh` returns all skills with `{ name, description, source, path }`
> 2. For each skill: read name + description, judge if it applies to the user's task
> 3. Add auto-add skills: test-first (code), verify-gate (fast mode), root-cause (bug)
> 4. No match = no invoke. No "1% chance" rule.

> ### How to invoke skills — NON-NEGOTIABLE
> 1. **Use the `Skill` tool directly** — do NOT rely on trigger phrase matching
> 2. Trigger phrases ("I'm using the X skill to...") are deprecated — they were unreliable
> 3. The `Skill` tool guarantees the skill's full SKILL.md is loaded into context
> 4. After the skill completes, it returns control to you — resume your own flow
