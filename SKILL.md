---
name: vega-punk
description: "Central nervous system for AI sessions. Routes requests, designs solutions, analyzes dependencies, selects skills, and hands off to planning. Use at session start for any task beyond simple Q&A. Triggers on: new session, ambiguous request, multi-step task, skill selection needed, or when user says 'let's think about' / 'how should we' / 'what's the plan'."
metadata:
  session_start_hook: "if [ -f .vega-punk-state.json ]; then echo '[vega-punk] Resuming from state:'; cat .vega-punk-state.json 2>/dev/null | head -5; echo '[vega-punk] To continue, describe your task. To start over, say \"new task\".'; else echo '[vega-punk] Ready. What shall we build?'; fi"
---

# Vega-Punk: Session State Machine

**Purpose:** Ensure every creative/implementation task follows a disciplined design flow before execution. Analyzes causal dependencies so the execution plan can maximize parallelism.

**Boundary:** vega-punk owns design and routing. After HANDOFF, planning-with-json takes over — it generates the plan, presents it to the user, and manages execution. vega-punk does not participate in execution.

**State file:** `.vega-punk-state.json` in the working directory.
**Spec directory:** `vega-punk/specs/` in the working directory.

For **OpenClaw**, the working directory is your current project. For **Claude Code**, it's the directory where you started the session.

**Recovery:** On session start, read `.vega-punk-state.json`. If valid JSON and `state` is not "DONE", resume from that state. If missing or corrupted, restart from ROUTE.

- **Claude Code:** Session persists. State file is in your working directory.
- **OpenClaw:** Check for state file in your agent's working directory. OpenClaw sessions may span multiple messages.

**Reset:** User says "start over" / "new task" / "forget previous" → delete `.vega-punk-state.json` → restart ROUTE.

- When this happens, tell the user: "[vega-punk] Starting fresh. What shall we build?"

**State JSON format:**
```json
{"state": "<STATE_NAME>", "task": "<user request>", "...state-specific fields..."}
```

**Git:** Add `.vega-punk-state.json` and `vega-punk/` to `.gitignore` if not present.

**Progress reporting:** At each transition:
> "Entering [STATE]... (Step X of Y: [remaining steps])"

| State | Est. | Remaining |
|-------|------|-----------|
| ROUTE | 1 min | 5-6 states |
| SCAN | 2 min | 5 states |
| CLARIFY | 3-5 min | 4 states |
| DESIGN | 5 min | 3 states |
| DEPENDENCIES | 3 min | 2 states |
| SPEC | 5 min | 1 state |
| HANDOFF | 1 min | 0 |

CONDENSED mode: 2 steps (3-sentence spec → approval).

If user asks "where are we?" or "how much left?", print current state and remaining steps.

---

## Three Hard Disciplines

These are not guidelines. They are rules.

### 1. HARD-GATE: No Design, No Code

Do NOT write any code, scaffold any project, invoke any implementation skill, or take any implementation action until the design has been presented and the user has approved it. This applies to EVERY project regardless of perceived simplicity. A todo list, a single-function utility, a config change — all of them. The design can be short (a few sentences for truly simple projects via CONDENSED mode), but you MUST present it and get approval.

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

Skills tell you HOW to explore. Check for skills BEFORE gathering information, BEFORE asking clarifying questions, BEFORE doing anything. "I need more context first" is a red flag — skills tell you how to gather context.

**When you invoke a skill, announce it:** "Using [skill] to [purpose]."

**If the skill has a checklist:** Create a TodoWrite task for each item and complete them in order.

**Invoke the skill tool** — don't just read the skill file.

- **Claude Code:** Use the `Skill` tool.
- **OpenClaw:** Use `openclaw skills` command or the platform's skill invocation mechanism.

### Skill Types

- **Rigid** (TDD, systematic-debugging, verification-before-completion): Follow exactly. Don't adapt away discipline.
- **Flexible** (ui-ux-pro-max, frontend-design): Adapt principles to context.

The skill itself tells you which. Read the current version — skills evolve.

### Deep Understanding First

- Understand the WHY before the WHAT
- Identify the real problem, not just the stated request
- Map constraints before proposing solutions

### Visual Companion — Browser vs Terminal

Decide per-question, not per-session. The test: **would the user understand this better by seeing it than reading it?**

- **Use the browser** for visual content: mockups, wireframes, layouts, architecture diagrams, side-by-side visual comparisons, spatial relationships.
- **Use the terminal** for text content: requirements questions, conceptual choices, tradeoff lists, scope decisions, clarifying questions.

A question *about* a UI topic is not automatically a visual question. "What kind of wizard do you want?" is conceptual — terminal. "Which of these wizard layouts feels right?" is visual — browser.

When offering the companion, make it its own message — do not combine with clarifying questions or any other content. Wait for the user's response before continuing.

**Starting a session:** Run `<vega-punk-dir>/scripts/start-server.sh --project-dir <project-root>`. Save `screen_dir` and `state_dir` from the response. Tell user to open the URL.

**The loop:** Write HTML content fragments to `screen_dir` → tell user what to expect → end your turn → on next turn, read `$STATE_DIR/events` for browser interactions → merge with terminal text → iterate or advance.

**When returning to terminal:** Write `waiting.html` to `screen_dir` to clear stale content from the browser.

Full guide: [visual-companion.md](visual-companion.md)

### Ask, Don't Assume

- Ambiguous requirements → ask ONE clarifying question
- Prefer multiple-choice questions with recommended option
- If user says "you decide" → document assumption, proceed

### Code Over Words

- When explaining, show code examples
- When designing, show architecture diagrams in text
- When comparing approaches, show concrete diffs

### Safety First

- NEVER commit/push without explicit request
- NEVER run destructive commands without confirmation
- Warn before any irreversible operation
- Add to `.gitignore` before creating temp files

### Verify Before Claiming Done

- Run tests before saying "tests pass"
- Run lint/typecheck before saying "code is clean"
- Build before saying "it works"
- Evidence before assertions, always

---

## State Machine

```
ROUTE → SCAN → CLARIFY → DESIGN → DEPENDENCIES → SPEC → HANDOFF → DONE
  ↓
CONDENSED → HANDOFF
```

**Valid transitions only.** Never skip states. Never go backwards except CONDENSED → SCAN (user rejects condensed, wants full flow).

---

## ROUTE

**Trigger:** New user message. No state file, or state is "DONE".

**Announce:** "Entering ROUTE... (Step 1 of 7)"

**Action:**
1. **Apply the 1% Rule first.** Might any skill apply? Invoke it. Even a simple question is a task. Check for skills before responding.
2. **Bug detection:** If user message contains bug-related keywords (`bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`), invoke systematic-debugging skill first.
3. Classify:
   - **Informational** (simple Q&A, definitions, explanations) → Answer directly. Set state: DONE. Stop.
   - **Creative/Implementation** (build, fix, modify, design, create) → Set state: SCAN. Proceed.
   - **Ambiguous** → Ask one question to classify.
4. **If user says "just write code" / "skip design" / "you decide":** Set state: CONDENSED.

**State write:**
```json
{"state": "SCAN", "task": "<user request>"}
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN... (Step 2 of 7)"

**Action:**
1. **Check scope BEFORE asking questions.** If the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), flag this immediately. Don't spend time refining details of a project that needs to be decomposed first. Help the user identify independent pieces, how they relate, and what order to build them. Then proceed with the first sub-project.
2. Check project context: files, docs, recent commits.
3. **Skill Routing:** Read [references/skill-routing.md](references/skill-routing.md). Match task against the routing table. Select ALL relevant skills and note execution order. Process skills first (brainstorming, debugging), implementation skills second.
4. **Skill invocation purpose:** Invoking a skill loads its guidance into context — it tells you HOW to proceed. You do NOT execute the skill's implementation steps here. You use the skill's workflow to inform the CLARIFY → DESIGN → SPEC flow.

**State write:**
```json
{"state": "CLARIFY", "task": "...", "context": "<summary>", "selected_skills": ["skill1", ...], "scope": "<single|decomposed>"}
```

---

## CLARIFY

**Trigger:** State is CLARIFY.

**Announce:** "Entering CLARIFY... (Step 3 of 7)"

**Action:**
1. **If the user's request is already clear** (purpose, constraints, and success criteria are evident from ROUTE/SCAN), skip questions and proceed to DESIGN. Announce: "Requirements are clear. Moving to design."
2. Otherwise, ask clarifying questions one at a time. Only one question per message.
3. Prefer multiple choice. Focus on: purpose, constraints, success criteria.
4. If user says "you decide", document assumption and proceed.

**State write:**
```json
{"state": "DESIGN", "task": "...", "requirements": {"purpose": "...", "constraints": "...", "success": "..."}}
```

---

## DESIGN

**Trigger:** State is DESIGN.

**Announce:** "Entering DESIGN... (Step 4 of 7). Let's brainstorm the best approach together."

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
1. Present the finalized design in sections, scaled to their complexity: a few sentences if straightforward, up to 200-300 words if nuanced.
2. **Ask after each section whether it looks right so far.** This is incremental validation, not a presentation.
3. Cover: architecture, components, data flow, error handling, testing.
4. **Design for isolation:** Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently. For each unit: what does it do, how do you use it, what does it depend on? Can someone understand what it does without reading internals? Can you change internals without breaking consumers? If not, the boundaries need work.
5. **Working in existing codebases:** Explore current structure first. Follow existing patterns. Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design. Don't propose unrelated refactoring. Stay focused on what serves the current goal.
6. Get explicit user approval.

**If user rejects:** Go back to Phase 1. Stay in DESIGN.

**State write:**
```json
{"state": "DEPENDENCIES", "task": "...", "design": {"approach": "...", "architecture": "...", "components": [...]}}
```

---

## DEPENDENCIES

**Trigger:** State is DEPENDENCIES.

**Announce:** "Entering DEPENDENCIES... (Step 5 of 7)"

**Purpose:** Analyze causal relationships. Output is INPUT for planning-with-json — NOT a plan.

**Action:**
1. List all components from the approved design.
2. For each pair, determine:

   | Relationship | Meaning |
   |--------------|---------|
   | **A → B (serial)** | B cannot start until A is complete |
   | **A ∥ B (parallel)** | A and B independent, can run simultaneously |
   | **A ↔ B (bidirectional)** | Design smell — merge or add abstraction |

3. Identify critical path (longest serial chain).
4. Identify parallel groups.

**Rules:**
- Schema → API → Frontend = serial
- Independent UI components = parallel
- Shared types first (serial), then implementations (parallel)

**State write:**
```json
{"state": "SPEC", "task": "...", "dependencies": {"components": [...], "serial": [{"from": "A", "to": "B"}], "parallel": [["A", "B"]], "critical_path": [...]}}
```

---

## SPEC

**Trigger:** State is SPEC.

**Announce:** "Entering SPEC... (Step 6 of 7)"

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
4. Ask user: "Spec written to `<path>`. Please review before we create the implementation plan."
5. Wait for approval. If changes → Fix → Re-run self-review.

**State write:**
```json
{"state": "HANDOFF", "task": "...", "spec_path": "vega-punk/specs/YYYY-MM-DD-<topic>-design.md"}
```

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode... (2 steps)"

**Action:**
1. Write a 3-sentence spec: What, Why, How.
2. Ask: "I'll implement [X] using [Y]. Proceed?"
3. If approved → Set state: HANDOFF.
4. If rejected → Set state: SCAN. User wants the full flow from the beginning.

**State write:**
```json
{"state": "HANDOFF", "task": "...", "mode": "condensed", "spec": "<3-sentence summary>"}
```

---

## HANDOFF

**Trigger:** State is HANDOFF.

**Announce:** "Entering HANDOFF... Design complete, transitioning to planning."

**Action:**
1. Invoke planning-with-json skill.
2. **Data passing:** The `.vega-punk-state.json` file IS the data transfer mechanism. planning-with-json will:
   - Read `.vega-punk-state.json` from the working directory
   - Extract `dependencies` (if present) to structure phases
   - Extract `selected_skills` to know available skills
   - Extract `spec_path` (or `spec` if condensed) to read the design document
3. **HANDOFF is the ONLY exit.** Do NOT invoke frontend-design, mcp-builder, or any implementation skill directly. planning-with-json is the next and only step.
4. Set state: DONE. vega-punk's responsibility ends here.

**What happens next (managed by planning-with-json, not vega-punk):**
- planning-with-json generates roadmap.json from the spec
- planning-with-json presents the plan to the user and offers execution choices
- planning-with-json invokes executing-plans or subagent-driven-development based on user choice
- Execution-stage skills (test-driven-development, systematic-debugging, verification-before-completion, requesting-code-review) are triggered during the execution phase, managed by planning-with-json and its sub-skills

**State write:**
```json
{"state": "DONE", "task": "...", "handoff_to": "planning-with-json"}
```

---

## Skill Invocation Chain

The complete workflow showing where vega-punk's responsibility ends and downstream skills take over:

```
┌─ ROUTE ──┐
│  1% Rule │ ──► systematic-debugging (if bug keywords detected)
└────┬─────┘
     ▼
┌─ SCAN ──┐
│ Skills   │ ──► (skills matching task domain)
└────┬─────┘
     ▼
┌─ CLARIFY ──┐
│ Questions  │ ──► (refine requirements)
└────┬───────┘
     ▼
┌─ DESIGN ──┐
│ Brainstorm │ ──► (architecture, components)
└────┬──────┘
     ▼
┌─ DEPENDENCIES ──┐
│ Analysis        │ ──► (serial/parallel mapping)
└────────┬────────┘
         ▼
┌─ SPEC ──────┐
│ Write spec  │ ──► (design document)
└──────┬──────┘
       ▼
┌─ HANDOFF ────────────────────────┐
│ planning-with-json (ONLY exit)   │ ──► vega-punk DONE
└──────────────────────────────────┘
         ▼
    [planning-with-json takes over]
    - generates roadmap.json
    - presents plan to user
    - offers execution choices
    - invokes executing-plans or subagent-driven-development
         ▼
    [execution phase — downstream skills]
    - test-driven-development (per task)
    - systematic-debugging (on error)
    - verification-before-completion (per task)
    - requesting-code-review (before merge)
```

## Skill Trigger Rules

| Skill | When to Invoke | Trigger |
|-------|----------------|---------|
| **systematic-debugging** | ROUTE: if user message contains bug-related keywords | `bug`, `fix`, `error`, `not working`, `crash`, `failed` |
| **planning-with-json** | HANDOFF: always | Hardcoded — the ONLY exit from vega-punk |

Skills triggered during execution (managed by planning-with-json, not vega-punk):

| Skill | When | Managed By |
|-------|------|------------|
| executing-plans | User chooses inline execution | planning-with-json |
| subagent-driven-development | User chooses parallel execution | planning-with-json |
| test-driven-development | Per task, before writing code | executing-plans / subagent-driven-development |
| verification-before-completion | Before claiming task done | executing-plans / subagent-driven-development |
| requesting-code-review | Before merge | finishing-a-development-branch |
| systematic-debugging | On error during execution | executing-plans / subagent-driven-development |

## Key Invocation Points

1. **ROUTE** — Check for bug keywords → trigger systematic-debugging if detected
2. **HANDOFF** — Always invoke planning-with-json (hardcoded)
3. **DONE** — vega-punk's responsibility ends. planning-with-json manages all subsequent stages.

---

## Red Flags — STOP, You're Rationalizing

| If you think... | The reality is... |
|-----------------|-------------------|
| "This is too simple to need a design" | Use CONDENSED mode, don't skip entirely |
| "I'll just do this one thing first" | Check the state machine BEFORE doing anything |
| "Let me explore the codebase first" | SCAN state handles context. Check first |
| "This doesn't need a formal skill" | If a skill exists, use it |
| "The skill is overkill" | Simple things become complex. Use CONDENSED, not nothing |
| "Dependencies are obvious" | Write them down. "Obvious" dependencies cause merge conflicts |
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "I remember this skill" | Skills evolve. Read the current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |

## External Skills Dependency

vega-punk directly invokes:

- **planning-with-json** — required (called from HANDOFF)

Skills triggered during execution (managed by planning-with-json):

- **executing-plans** — inline execution
- **subagent-driven-development** — parallel execution
- **systematic-debugging** — on bugs
- **test-driven-development** — per task
- **verification-before-completion** — before claiming done
- **requesting-code-review** — before merge

## Key Principles

- **One state at a time** — Never skip states. Use CONDENSED for speed.
- **Dependencies drive execution** — Serial blocks, parallel unblocks.
- **One question at a time** — Don't overwhelm.
- **YAGNI ruthlessly** — Remove unrequested features.
- **Working in existing codebases** — Follow existing patterns. Targeted improvements only. No unrelated refactoring.
- **Clear boundaries** — vega-punk stops at HANDOFF. planning-with-json manages everything after.
