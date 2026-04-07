---
name: vega-punk
description: "Central nervous system for AI sessions. Routes requests, designs solutions, analyzes dependencies, selects skills, and hands off to planning. Use at session start for any task beyond simple Q&A. Triggers on: new session, ambiguous request, multi-step task, skill selection needed, or when user says 'let's think about' / 'how should we' / 'what's the plan'."
user-invocable: true
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch"
hooks:
  SessionStart:
    - type: command
      command: "bash scripts/planning-resume.sh"
    - type: command
      command: "bash scripts/session-hook.sh 2>/dev/null || echo '[vega-punk] Ready. What shall we build?'"
---

# Vega-Punk: Session State Machine

**Purpose:** Ensure every creative/implementation task follows a disciplined design flow before execution. Analyzes causal dependencies so the execution plan can maximize parallelism.

**Boundary:** vega-punk handles design and routing. After HANDOFF, the planning-with-json sub-skill takes over — it reads the state file, generates the roadmap, and manages execution. vega-punk remains available to review execution results in the REVIEW state.

**State file:** `.vega-punk-state.json` in the working directory.
**Spec directory:** `vega-punk/specs/` in the working directory.

For **OpenClaw**, the working directory is your current project. For **Claude Code**, it's the directory where you started the session.

## How State Works

**On every user message:**

1. Read `.vega-punk-state.json` if it exists.
2. If the file exists and `state` is not "DONE", **do NOT start from ROUTE**. Execute the current state's actions directly.
3. If the file is missing or `state` is "DONE", start from ROUTE.

**Special: REVIEW state.** If state is "REVIEW" and `execution_result` exists, enter REVIEW immediately. If `execution_result` is missing, check `roadmap.json`: if it exists with incomplete steps, resume execution from its `current_step` (the execution layer handles this). Otherwise wait for user input — do not restart ROUTE.

**Recovery:** If the session_start_hook outputs "Resuming from [STATE]...", read `.vega-punk-state.json`, find the state value, and execute the actions for that state. Do NOT re-announce the resume message — the hook already did. Do NOT go back to ROUTE. Continue from where you left off.

**Reset:** User says "start over" / "new task" / "forget previous" → apply Post-Completion Cleanup → restart ROUTE.

- When this happens, tell the user: "[vega-punk] Starting fresh. What shall we build?"

**Skill loop protection:** The `scan_depth` field in the state JSON tracks consecutive SCAN entries. If it reaches 3, skip skill routing and proceed directly to CLARIFY. This prevents skill → SCAN → skill loops. Increment on each SCAN entry, reset on each CLARIFY entry.

**State JSON format:** Read the current JSON file, change the `state` field, add new fields, and write back. **Do NOT delete existing fields.** Always preserve `task`.

**State JSON cleanup:** On transition to DONE, the state file is deleted (see Post-Completion Cleanup). On REVIEW → new task transition, the old state is archived via spec rename and state file deletion. This prevents indefinite growth.

**Example state progression:**

After SCAN:

```json
{
  "state": "CLARIFY",
  "task": "build todo app",
  "context": "...",
  "selected_skills": [],
  "scope": "single"
}
```

After CLARIFY:

```json
{
  "state": "DESIGN",
  "task": "build todo app",
  "context": "...",
  "selected_skills": [],
  "scope": "single",
  "requirements": {}
}
```

After HANDOFF:

```json
{
  "state": "REVIEW",
  "task": "build todo app",
  "context": "...",
  "selected_skills": [],
  "scope": "single",
  "requirements": {},
  "design": {},
  "dependencies": {},
  "spec_path": "...",
  "handoff_to": "planning-with-json"
}
```

After REVIEW (execution callback):

```json
{
  "state": "DONE",
  "task": "build todo app",
  "...previous fields...": "...",
  "execution_result": {
    "status": "success",
    "summary": "...",
    "artifacts": [],
    "verification": "passed"
  }
}
```

The final file contains the complete design context for downstream skills to read.

**Git:** Add `.vega-punk-state.json` to `.gitignore`. **Do NOT** gitignore `vega-punk/specs/` — spec history is project memory and should be committed.

**Progress reporting:** At each transition:
> "Entering [STATE]..."

If user asks "where are we?" or "how much left?", print current state and remaining steps.

| State        | Full Path     | Condensed Path |
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

- **Rigid** (TDD, systematic-debugging, verification-before-completion): Follow exactly. Don't adapt away discipline.
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

```
ROUTE → SCAN → CLARIFY → DESIGN ────→ DEPENDENCIES → SPEC ────→ HANDOFF ─→ REVIEW ─→ DONE
  ↓                     ↓                              ↓
  ↓                   DESIGN_QA                      SPEC_QA
  ↓                     ↓                              ↓
CONDENSED ──→ HANDOFF ↩ DESIGN                       ↩ SPEC
    ↓         ↘
  ↩ SCAN  (if user rejects)  (if user rejects)
```

**Never skip or reverse states.** Exception: the rollback rules below.

## Allowed Rollbacks

These are the only state reversals permitted. All other transitions are forward-only.

| Trigger                                    | Rollback                                                                             | Rationale                                                       |
|--------------------------------------------|--------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| DESIGN_QA FAIL                             | → DESIGN (max 3 retries)                                                             | Design has a concrete flaw that must be fixed                   |
| SPEC_QA FAIL                               | → SPEC (max 3 retries)                                                               | Spec has gaps or contradictions that must be resolved           |
| User changes direction during DESIGN       | → CLARIFY (if fundamental goal change) or stay in DESIGN (if exploring alternatives) | User needs to redefine the problem                              |
| User changes direction during DEPENDENCIES | → DESIGN (if architecture changes needed)                                            | Design needs adjustment before dependency analysis can continue |
| CONDENSED rejected                         | → SCAN (user wants the full flow)                                                    | Condensed mode is a shortcut, not a commitment                  |
| User rejects proposed design in DESIGN     | Stay in DESIGN, restart from Phase 1                                                 | Not a rollback — re-iteration within the same state             |
| REVIEW: execution failed                   | → CLARIFY (if requirements changed) or → DESIGN (if design was wrong)                | Execution results don't match spec                              |
| REVIEW: execution partial                  | → DESIGN (implement remaining) or → CLARIFY (if scope changed)                       | Some requirements not yet met                                   |

---

## ROUTE

**Trigger:** No state file, or state is "DONE".

**Announce:** "Entering ROUTE..."

**Action:**

0. **Post-Completion Cleanup:** If state is "DONE" and `.vega-punk-state.json` exists, archive the previous spec file (rename `*.md` → `*.DONE.md`) and delete `.vega-punk-state.json`. This ensures a clean slate for the new task.
1. **Apply the 1% Rule first.** Might any skill apply? Invoke it. Even a simple question is a task. Check for skills before responding.
2. **Bug detection:** If user message contains bug-related keywords (`bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`), invoke systematic-debugging skill first.
3. Classify:
    - **Informational** (simple Q&A, definitions, explanations) → Answer directly. Set state: DONE. Stop.
    - **Creative/Implementation** (build, fix, modify, design, create) → Set state: SCAN. Proceed.
    - **Ambiguous** → Ask one question to classify.
4. **If user says "just write code" / "skip design" / "just do it" / "don't overthink":** Set state: CONDENSED.

**State write:**

```json
{
  "state": "SCAN",
  "task": "<user request>",
  "scan_depth": 0
}
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN..."

**Action:**

1. **Check scope BEFORE asking questions.** If the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), tell the user immediately that the project should be split. Don't spend time refining details of a project that needs to be decomposed first. Help the user identify independent pieces, how they relate, and what order to build them. Then proceed with the first sub-project.
2. Check project context: files, docs, recent commits.
3. **Skill Routing:** Read `scan_depth` from the state file. If it is 3 or greater, skip skill routing and proceed to step 4. Otherwise, try to read [references/skill-routing.md](references/skill-routing.md). If the file doesn't exist, skip skill routing and proceed to step 4. If it exists, match task against the routing table. Select ALL relevant skills and note execution order. Process skills first (brainstorming, debugging), implementation skills second. **Also check for any newly installed skills not yet in the routing table — if a skill might apply, invoke it (1% Rule).**
4. **Skill invocation purpose:** Invoking a skill loads its guidance into context — it tells you HOW to proceed. You do NOT execute the skill's implementation steps here. You use the skill's workflow to inform the CLARIFY → DESIGN → SPEC flow.

**State write:** Read the current JSON, change `state` to "CLARIFY", add `context`, `selected_skills`, `scope`. Increment `scan_depth` (or set to 1 if not present). Keep all existing fields.

```json
{
  "state": "CLARIFY",
  "task": "...",
  "context": "<summary>",
  "selected_skills": [
    "skill1",
    "skill2"
  ],
  "scope": "<single|decomposed>",
  "scan_depth": 1
}
```

---

## CLARIFY

**Trigger:** State is CLARIFY.

**Announce:** "Entering CLARIFY..."

**Action:**

1. **If the user's request is already clear** (purpose, constraints, and success criteria are clear from the request and SCAN output), skip questions and proceed to DESIGN. Announce: "Requirements are clear. Moving to design." Extract purpose, constraints, and success criteria from the user's original request and SCAN context.
2. Otherwise, ask clarifying questions one at a time. Only one question per message.
3. Prefer multiple choice. Focus on: purpose, constraints, success criteria.
4. If user says "you decide", document assumption and proceed.

**State write:** Read the current JSON, change `state` to "DESIGN", add `requirements`. Reset `scan_depth` to 0. Keep all existing fields.

```json
{
  "state": "DESIGN",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "scan_depth": 0,
  "requirements": {
    "purpose": "...",
    "constraints": "...",
    "success": "..."
  }
}
```

---

## DESIGN

**Trigger:** State is DESIGN.

**Announce:** "Entering DESIGN... Let's brainstorm the best approach together."

**Phase tracking:** Update the `design_phase` field in the state JSON as you progress: `"brainstorm"` → `"converge"` → `"present"`. This lets recovery know exactly where you left off.

**Phase 1 — Brainstorm (Collaborative):**

1. Present 2-3 approaches with trade-offs. Frame them as options to explore together, not decisions to approve.
2. For each approach, show: what it does well, what it costs, what risks it carries.
3. Lead with your recommendation but explain why — and why the others might also be valid.
4. **Ask the user:** "Which direction feels right? Or would you like to combine elements from different approaches?"

**Phase 2 — Converge (Co-create):**

1. Based on user feedback, refine the chosen approach.
2. If the user wants to combine approaches, show how that would look.
3. If the user has their own idea, integrate it and show the merged design.
4. This is a dialogue, not a presentation. Iterate until the design feels right to both of you.

**Phase 3 — Present (Formalize):**

1. Keep it brief if straightforward (a few sentences). Expand if nuanced (up to 200-300 words).
2. **After each section, ask: "Does this look right so far?"** This is incremental validation, not a presentation.
3. Cover: architecture, components, data flow, error handling, testing.
4. **Design for isolation:** Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently. For each unit: what does it do, how do you use it, what does it depend on? Can someone understand what it does without reading internals? Can you change internals without breaking consumers? If not, the boundaries need work.
5. **Working in existing codebases:** Explore current structure first. Follow existing patterns. Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design. Don't propose unrelated refactoring. Stay focused on what serves the current goal.
6. Get explicit user approval.

**If user rejects:** Announce "Revisiting approach..." and return to Phase 1. Stay in DESIGN.

**If user changes direction:** Apply the Allowed Rollbacks rules above.

**State write:** Read the current JSON, change `state` to "DESIGN_QA", add `design`. Keep all existing fields.

```json
{
  "state": "DESIGN_QA",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "requirements": {},
  "design": {},
  "qa": {
    "design_retries": 0,
    "design_feedback": ""
  }
}
```

---

## 通用 QA 模式 (Reusable QA Pattern)

Both DESIGN_QA and SPEC_QA use the same two-layer QA structure:

1. **Layer 1: Structured Self-Review** — Switch perspective, run domain-specific checklist, fix failures, re-run.
2. **Layer 2: User Secondary Review** — Present findings (passed/fixed/risks), user makes final PASS/FAIL.

**Decision Flow:**
| Step | Action | Outcome |
|------|--------|---------|
| 1 | Self-review runs | Checklist findings collected |
| 2 | Findings presented to user | User reviews and decides |
| 3 | User passes | → Next state |
| 3 (alt) | User fails | → Return to previous state (retry +1, max 3) |

**Retry limit:** Beyond 3 retries → "[vega-punk] I've hit the retry limit. Please review manually and tell me how to proceed." Stay in current QA state.

---

## DESIGN_QA

**Trigger:** State is DESIGN_QA.

**Announce:** "Entering DESIGN_QA... awaiting expert review + user secondary review"

**Action:**

Apply the **通用 QA 模式** (see below) with these design-specific checks:

- **Architecture:** Does the design follow separation of concerns? Can units be understood and changed independently?
- **Technology choices:** Are selected tools justified? Is there a simpler alternative?
- **Data flow:** Are dependencies acyclic? Any circular references between components?
- **Error handling:** What happens when each external call fails? Are error boundaries defined?
- **Edge cases:** What are the top 3 ways this design could break in production?
- **Scope creep:** Does the design include unrequested features? Remove them.

On PASS → Enter DEPENDENCIES. On FAIL → Return to DESIGN (retry count +1, max 3).

**State write:** Read the current JSON, change `state` to "DEPENDENCIES" (PASS) or "DESIGN" (FAIL), update `qa` fields. Keep all existing fields.

```json
{
  "state": "DEPENDENCIES",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "scan_depth": 0,
  "requirements": {},
  "design": {},
  "qa": {
    "design_retries": 0,
    "design_feedback": "",
    "design_status": "PASS"
  }
}
```

---

## DEPENDENCIES

**Trigger:** State is DEPENDENCIES.

**Announce:** "Entering DEPENDENCIES..."

**Purpose:** Analyze causal relationships. Output is INPUT for the planning-with-json sub-skill — NOT a plan.

**Action:**

1. List all components from the approved design.
2. For each pair, determine:

   | Relationship | Meaning |
   |--------------|---------|
   | **A → B (serial)** | B cannot start until A is complete |
   | **A ∥ B (parallel)** | A and B independent, can run simultaneously |
   | **A ↔ B (bidirectional)** | Warning sign — this usually means the two components should be merged or separated by an abstraction |

3. Identify critical path (longest serial chain).
4. Identify parallel groups.

**Rules:**

- Schema → API → Frontend = serial
- Independent UI components = parallel
- Shared types first (serial), then implementations (parallel)

**State write:** Read the current JSON, change `state` to "SPEC", add `dependencies`. Keep all existing fields.

```json
{
  "state": "SPEC",
  "task": "...",
  "...previous fields...": "...",
  "dependencies": {
    "components": [],
    "serial": [
      {
        "from": "A",
        "to": "B"
      }
    ],
    "parallel": [
      [
        "A",
        "B"
      ]
    ],
    "critical_path": []
  }
}
```

**If user changes direction:** Apply the Allowed Rollbacks rules above.

---

## SPEC

**Trigger:** State is SPEC.

**Announce:** "Entering SPEC..."

**Action:**

1. Write spec to `vega-punk/specs/YYYY-MM-DD-<topic>-design.md`. Create directory if not exists.
    - Required sections: Goal, Architecture, Components, Interfaces, Data Flow, Error Handling, Testing Plan, Dependency Graph.
2. **Spec Self-Review** — look at the spec with fresh eyes:
    - **Placeholder scan:** Any "TBD", "TODO", incomplete sections, or vague requirements? Fix them.
    - **Internal consistency:** Do any sections contradict each other? Does the architecture match the feature descriptions?
    - **Scope check:** Is this focused enough for a single implementation plan, or does it need decomposition?
    - **Ambiguity check:** Could any requirement be interpreted two different ways? If so, pick one and make it explicit.
    - **Dependency check:** Are serial dependencies justified?
3. Fix any issues inline. No need to re-review — just fix and move on.
4. Ask user: "Spec written to `<path>`. Review the spec. If it looks good, I'll hand off to planning."
5. Wait for approval. If changes → Fix → Re-run self-review.

**State write:** Read the current JSON, change `state` to "SPEC_QA", add `spec_path`, add `qa` field. Keep all existing fields.

```json
{
  "state": "SPEC_QA",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "scan_depth": 0,
  "requirements": {},
  "design": {},
  "dependencies": {},
  "spec_path": "vega-punk/specs/YYYY-MM-DD-<topic>-design.md",
  "qa": {
    "spec_retries": 0,
    "spec_feedback": ""
  }
}
```

---

## SPEC_QA

**Trigger:** State is SPEC_QA.

**Announce:** "Entering SPEC_QA... awaiting expert review + user secondary review"

**Action:**

Apply the **通用 QA 模式** (see above) with these spec-specific checks:

- **Completeness:** Can every section be implemented without guessing? No TBD, TODO, or vague statements.
- **Consistency:** Do any sections contradict each other? Does the dependency graph match the architecture?
- **Interface contracts:** Are all inputs, outputs, and data shapes explicitly defined?
- **Testability:** Can every requirement be tested? Is there a clear pass/fail criterion for each?
- **Dependency accuracy:** Are serial dependencies justified? Could anything be parallelized that is marked serial?
- **Scope discipline:** Does the spec include unrequested features? Remove them.

On PASS → Enter HANDOFF. On FAIL → Return to SPEC (retry count +1, max 3).

**State write:** Read the current JSON, change `state` to "HANDOFF", update `qa` fields. Keep all existing fields.

```json
{
  "state": "HANDOFF",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "requirements": {},
  "design": {},
  "dependencies": {},
  "spec_path": "...",
  "qa": {
    "spec_retries": 0,
    "spec_feedback": "",
    "spec_status": "PASS"
  }
}
```

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode..."

**Action:**

1. Write a minimal spec: What, Why, How (3 sentences max).
2. Define at least one key interface or entry point: input → output, or function signature, or API shape. This gives the planning layer something concrete to structure phases around.
3. **Approval:** Ask: "I'll implement [X] using [Y]. Proceed?" Wait for user response.
4. **If approved →** Set state: HANDOFF.
5. **If rejected →** Set state: SCAN. User wants the full flow from the beginning.
6. **After approval, before HANDOFF, do a quick self-review:** Are there any TBD, TODO, or ambiguous statements in the minimal spec? Fix them inline.

**State write:** Read the current JSON, change `state` to "HANDOFF", add `mode`, `spec`. Keep all existing fields.

```json
{
  "state": "HANDOFF",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "requirements": {},
  "mode": "condensed",
  "spec": "<3-sentence summary>"
}
```

---

## HANDOFF

**Trigger:** State is HANDOFF.

**Announce:** "Entering HANDOFF... Design complete, transitioning to planning."

**Action:**

1. **Invoke the sub-skill:** Read [references/planning-with-json/SKILL.md](references/planning-with-json/SKILL.md) and follow its planning workflow.
2. **Data contract:** The `.vega-punk-state.json` file IS the data transfer mechanism. The sub-skill reads it directly to extract:
    - `spec_path` (or `spec` if condensed) — the design document for planning
    - `dependencies` — serial/parallel analysis for phase structuring
    - `selected_skills` — relevant skills for the execution plan
    - `design` — architecture and component details
    - `requirements` — purpose, constraints, success criteria
3. **Transition to Planning Phase:** The sub-skill creates `roadmap.json` from this context. Follow its execution loop for step-by-step implementation.

**State write:** Read the current JSON, change `state` to "REVIEW", add `handoff_to`. Keep all existing fields — the full context remains available for downstream skills and execution callback.

```json
{
  "state": "REVIEW",
  "task": "...",
  "context": "...",
  "selected_skills": [],
  "scope": "...",
  "requirements": {},
  "design": {},
  "dependencies": {},
  "spec_path": "...",
  "handoff_to": "planning-with-json"
}
```

---

## Planning with JSON (Sub-skill)

Planning is managed by a sub-skill at [references/planning-with-json/SKILL.md](references/planning-with-json/SKILL.md). After HANDOFF, read that file and follow its workflow:

1. **Read** `references/planning-with-json/SKILL.md` — contains the full planning framework
2. **Create** `roadmap.json` per the sub-skill's specification
3. **Execute** steps per the sub-skill's execution loop
4. **Offer** execution choice (Subagent-Driven vs Inline) per the sub-skill's handoff section

The sub-skill defines: roadmap.json structure, step granularity rules, verification types, failure escalation, and anti-patterns.

---

## REVIEW

**Trigger:** State is REVIEW.

**Purpose:** Receive execution results, compare against the original spec's success criteria, and recommend next actions. This closes the design → execute → verify loop.

**Execution Result Writer Contract:** The execution layer (subagent-driven-development or executing-plans) is responsible for writing `execution_result` to `.vega-punk-state.json`. All execution sub-skills MUST follow this exact format when completing:

```json
{
  "state": "REVIEW",
  "task": "...",
  "...previous fields...": "...",
  "execution_result": {
    "status": "success|partial|failed",
    "summary": "...",
    "artifacts": ["path1", "path2"],
    "verification": "passed|failed",
    "notes": "..."
  }
}
```

This update triggers vega-punk's REVIEW state automatically. Do NOT modify any other fields in the state JSON during this write.

**How this is triggered:** After execution + verification completes, the execution layer writes the above JSON. vega-punk then reads `execution_result` and presents the outcome to the user.

**Action:**

1. Read `execution_result` from the state file.
2. Compare against `requirements.success` from the original spec.
3. Present a brief summary to the user:
    - **success + passed:** "Execution complete. All success criteria met. Artifacts: [list]. Start a new task?"
    - **success + failed:** "Execution complete but verification failed. Issues: [notes]. Iterate on the design or start fresh?"
    - **partial:** "Execution partially complete. Done: [summary]. Remaining: [summary]. Continue or redesign?"
    - **failed:** "Execution failed. Root cause: [notes]. Redesign needed?"
4. Based on user response:
    - **New task** → Post-Completion Cleanup → ROUTE
    - **Iterate** → Set state: DESIGN with `execution_result` as context
    - **Redesign** → Set state: CLARIFY with `execution_result` as context

---

## Execution Phase: Verification Contract

> **Ownership:** This phase is managed by the **planning-with-json** sub-skill during execution, using the **verification-before-completion** skill.
>
> The requirement is simple: every task type must have concrete, observable evidence before claiming done. What that evidence looks like, how to collect it, and how to retry — all defined by `verification-before-completion`. vega-punk only specifies **what success looks like** in the spec; the execution layer decides **how to prove it**.

## Post-Completion Cleanup

**Trigger:** ROUTE step 0 (when state is "DONE" and a new task starts), or user says "new task" / "start over" / "forget previous", or user cancels the flow.

1. **Archive spec files:** Rename `vega-punk/specs/*.md` → `*.DONE.md` for completed tasks, or rename to `*.CANCELLED.md` for cancelled tasks. Never delete specs — archive them so history is always recoverable.
2. **Delete `.vega-punk-state.json`.** The task is done or cancelled, the state is no longer needed for recovery.

**REVIEW → new task transition:** If the user starts a new task while in REVIEW state, apply Post-Completion Cleanup then restart ROUTE.

## Bootstrap (First Run)

When vega-punk is invoked for the first time in a project:

1. **Create spec directory:** `mkdir -p vega-punk/specs`
2. **Verify gitignore:** Add `.vega-punk-state.json` to `.gitignore`. **Do NOT** gitignore `vega-punk/` — spec history should be committed.
3. **Verify scripts exist:** `ls scripts/` should contain `planning-resume.sh`, `session-hook.sh`, etc. If missing, inform the user.
4. Proceed to ROUTE state. No state file needed for first run.

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

**Version policy:** vega-punk version N.x requires all referenced sub-skills at version N.x or later. Sub-skills are released in lockstep with the main skill. If a sub-skill version lags, read the sub-skill's own documentation for breaking changes.

**Sub-skills (referenced):**

- **planning-with-json** — [references/planning-with-json/SKILL.md](references/planning-with-json/SKILL.md) (called from HANDOFF)
- **executing-plans** — [references/executing-plans/SKILL.md](references/executing-plans/SKILL.md) (called from planning-with-json's Execution Handoff)

**External dependencies (called during execution):**

- **subagent-driven-development** — parallel execution
- **systematic-debugging** — on bugs
- **test-driven-development** — per task
- **verification-before-completion** — before claiming done
- **requesting-code-review** — before merge
- **finishing-a-development-branch** — after all tasks complete
- **dispatching-parallel-agents** — independent concurrent tasks
- **using-git-worktrees** — isolated workspace for feature work
- **receiving-code-review** — process code review feedback

## Key Principles

- **One state at a time** — Never skip states. Use CONDENSED for speed.
- **Dependencies drive execution** — Serial blocks, parallel unblocks.
- **One question at a time** — Don't overwhelm.
- **YAGNI ruthlessly** — Remove unrequested features.
- **Working in existing codebases** — Follow existing patterns. Targeted improvements only. No unrelated refactoring.
- **Sub-skill architecture** — planning in `planning-with-json/SKILL.md`, execution in `executing-plans/SKILL.md`. HANDOFF reads and follows them.

## Skill Trigger Reference

Centralized trigger conditions for all referenced skills:

| Skill | When to Invoke | Trigger Keywords / Conditions |
|-------|---------------|------------------------------|
| **systematic-debugging** | ROUTE detects bug keywords | `bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception` |
| **planning-with-json** | HANDOFF → create roadmap.json | `.vega-punk-state.json` has spec_path or spec |
| **executing-plans** | Inline execution chosen | `roadmap.json` exists, user chose inline |
| **test-driven-development** | Any code implementation step | Every feature, bugfix, refactor |
| **verification-before-completion** | Before claiming any step/task done | Every verification gate |
| **using-git-worktrees** | Before starting feature work | Required by subagent-driven-development and executing-plans |
| **subagent-driven-development** | After planning, parallel tasks preferred | `roadmap.json` exists, tasks mostly independent |
| **dispatching-parallel-agents** | 2+ independent tasks with no shared state | Different test files, different subsystems, no shared dependencies |
| **requesting-code-review** | After each task or before merge | Mandatory in subagent-driven-development |
| **receiving-code-review** | Processing review feedback | Code review comments received |
| **finishing-a-development-branch** | All tasks complete, tests passing | Merge/PR/keep/discard decision |
