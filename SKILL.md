---
name: vega-punk
description: "Central nervous system for AI sessions. Routes requests, designs solutions, analyzes dependencies, selects skills, and hands off to planning. Use at session start for any task beyond simple Q&A. Triggers on: new session, ambiguous request, multi-step task, skill selection needed, or when user says 'let's think about' / 'how should we' / 'what's the plan'."
metadata:
  session_start_hook: "if [ -f .vega-punk-state.json ]; then STATE=$(python3 -c 'import json,sys; d=json.load(open(\".vega-punk-state.json\")); print(d.get(\"state\",\"\"))' 2>/dev/null); if [ -n \"$STATE\" ] && [ \"$STATE\" != \"DONE\" ]; then echo \"[vega-punk] Resuming from $STATE. Continue working or say 'new task'.\"; else echo \"[vega-punk] Ready. What shall we build?\"; fi; else echo \"[vega-punk] Ready. What shall we build?\"; fi"
---

# Vega-Punk: Session State Machine

**Purpose:** Ensure every creative/implementation task follows a disciplined design flow before execution. Analyzes causal dependencies so the execution plan can maximize parallelism.

**Boundary:** vega-punk is responsible for design and routing. After HANDOFF, planning-with-json takes over — it generates the plan, presents it to the user, and manages execution. vega-punk does not participate in execution.

**State file:** `.vega-punk-state.json` in the working directory.
**Spec directory:** `vega-punk/specs/` in the working directory.

For **OpenClaw**, the working directory is your current project. For **Claude Code**, it's the directory where you started the session.

## How State Works

**On every user message:**
1. Read `.vega-punk-state.json` if it exists.
2. If the file exists and `state` is not "DONE", **do NOT start from ROUTE**. Execute the current state's actions directly.
3. If the file is missing or `state` is "DONE", start from ROUTE.

**Recovery:** If the session_start_hook outputs "Resuming from [STATE]...", read `.vega-punk-state.json`, find the state value, and execute the actions for that state. Do NOT re-announce the resume message — the hook already did. Do NOT go back to ROUTE. Continue from where you left off.

**Reset:** User says "start over" / "new task" / "forget previous" → delete `.vega-punk-state.json` → restart ROUTE.

- When this happens, tell the user: "[vega-punk] Starting fresh. What shall we build?"

**State JSON format:** Read the current JSON file, change the `state` field, add new fields, and write back. **Do NOT delete existing fields.** Always preserve `task`.

**Example state progression:**
```json
// After SCAN: {"state": "CLARIFY", "task": "build todo app", "context": "...", "selected_skills": [...], "scope": "single"}
// After CLARIFY: {"state": "DESIGN", "task": "build todo app", "context": "...", "selected_skills": [...], "scope": "single", "requirements": {...}}
// After HANDOFF: {"state": "DONE", "task": "build todo app", "context": "...", "selected_skills": [...], "scope": "single", "requirements": {...}, "design": {...}, "dependencies": {...}, "spec_path": "...", "handoff_to": "planning-with-json"}
```

The final file contains the complete design context for downstream skills to read.

**Git:** Add `.vega-punk-state.json` and `vega-punk/` to `.gitignore` if not present.

**Progress reporting:** At each transition:
> "Entering [STATE]..."

If user asks "where are we?" or "how much left?", print current state and remaining steps.

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

---

## Three Hard Disciplines

These are rules. Do not treat them as suggestions.

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

**Starting a session:** Find the vega-punk skill directory (search `~/.agents/skills/vega-punk/` or the directory containing this SKILL.md) and run `scripts/start-server.sh --project-dir <project-root>`. Save `screen_dir` and `state_dir` from the response. Tell user to open the URL.

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

### Handle Off-Topic Input

If the user sends a message unrelated to the current state's purpose:
1. Briefly acknowledge or answer if it's a simple question
2. Guide back: "Back to [STATE] — [reminder of where we are]"
3. Continue from the current state. Do NOT change state or restart the flow.

---

## State Machine

```
ROUTE → SCAN → CLARIFY → DESIGN → DEPENDENCIES → SPEC → HANDOFF → DONE
  ↓
CONDENSED → HANDOFF
```

**Never skip or reverse states.** Exception: CONDENSED → SCAN (user rejects condensed, wants full flow).

---

## ROUTE

**Trigger:** No state file, or state is "DONE".

**Announce:** "Entering ROUTE..."

**Action:**
1. **Apply the 1% Rule first.** Might any skill apply? Invoke it. Even a simple question is a task. Check for skills before responding.
2. **Bug detection:** If user message contains bug-related keywords (`bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`), invoke systematic-debugging skill first.
3. Classify:
   - **Informational** (simple Q&A, definitions, explanations) → Answer directly. Set state: DONE. Stop.
   - **Creative/Implementation** (build, fix, modify, design, create) → Set state: SCAN. Proceed.
   - **Ambiguous** → Ask one question to classify.
4. **If user says "just write code" / "skip design" / "just do it" / "don't overthink":** Set state: CONDENSED.

**State write:**
```json
{"state": "SCAN", "task": "<user request>"}
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN..."

**Action:**
1. **Check scope BEFORE asking questions.** If the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), tell the user immediately that the project should be split. Don't spend time refining details of a project that needs to be decomposed first. Help the user identify independent pieces, how they relate, and what order to build them. Then proceed with the first sub-project.
2. Check project context: files, docs, recent commits.
3. **Skill Routing:** Read [references/skill-routing.md](references/skill-routing.md). Match task against the routing table. Select ALL relevant skills and note execution order. Process skills first (brainstorming, debugging), implementation skills second.
4. **Skill invocation purpose:** Invoking a skill loads its guidance into context — it tells you HOW to proceed. You do NOT execute the skill's implementation steps here. You use the skill's workflow to inform the CLARIFY → DESIGN → SPEC flow.

**State write:** Read the current JSON, change `state` to "CLARIFY", add `context`, `selected_skills`, `scope`. Keep all existing fields.
```json
{"state": "CLARIFY", "task": "...", "context": "<summary>", "selected_skills": ["skill1", ...], "scope": "<single|decomposed>"}
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

**State write:** Read the current JSON, change `state` to "DESIGN", add `requirements`. Keep all existing fields.
```json
{"state": "DESIGN", "task": "...", "context": "...", "selected_skills": [...], "scope": "...", "requirements": {"purpose": "...", "constraints": "...", "success": "..."}}
```

---

## DESIGN

**Trigger:** State is DESIGN.

**Announce:** "Entering DESIGN... Let's brainstorm the best approach together."

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

**If user rejects:** Announce "Revisiting approach..." and go back to Phase 1. Stay in DESIGN.

**If user changes direction:** (e.g., "let's go a different way", "I want something else entirely") → Announce "Starting fresh..." → Go back to Phase 1. If the change is fundamental (different product, different goal), go back to CLARIFY to re-extract requirements.

**State write:** Read the current JSON, change `state` to "DEPENDENCIES", add `design`. Keep all existing fields.
```json
{"state": "DEPENDENCIES", "task": "...", "context": "...", "selected_skills": [...], "scope": "...", "requirements": {...}, "design": {"approach": "...", "architecture": "...", "components": [...]}}
```

---

## DEPENDENCIES

**Trigger:** State is DEPENDENCIES.

**Announce:** "Entering DEPENDENCIES..."

**Purpose:** Analyze causal relationships. Output is INPUT for planning-with-json — NOT a plan.

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
{"state": "SPEC", "task": "...", "...previous fields...": "...", "dependencies": {"components": [...], "serial": [{"from": "A", "to": "B"}], "parallel": [["A", "B"]], "critical_path": [...]}}
```

**If user changes direction:** Go back to DESIGN. Announce "Adjusting design..."

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

**State write:** Read the current JSON, change `state` to "HANDOFF", add `spec_path`. Keep all existing fields.
```json
{"state": "HANDOFF", "task": "...", "...previous fields...": "...", "spec_path": "vega-punk/specs/YYYY-MM-DD-<topic>-design.md"}
```

**If user changes direction:** If it's a spec-level change (add/remove feature), fix the spec and re-run self-review. If it's a fundamental direction change, go back to DESIGN. Announce "Adjusting design..."

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode..."

**Action:**
1. Write a 3-sentence spec: What, Why, How.
2. Ask: "I'll implement [X] using [Y]. Proceed?"
3. If approved → Set state: HANDOFF.
4. If rejected → Set state: SCAN. User wants the full flow from the beginning.

**State write:** Read the current JSON, change `state` to "HANDOFF", add `mode`, `spec`. Keep all existing fields.
```json
{"state": "HANDOFF", "task": "...", "mode": "condensed", "spec": "<3-sentence summary>"}
```

---

## HANDOFF

**Trigger:** State is HANDOFF.

**Announce:** "Entering HANDOFF... Design complete, transitioning to planning."

**Action:**
1. Invoke planning-with-json skill.
2. **Data passing:** The `.vega-punk-state.json` file IS the data transfer mechanism. It contains the full design context accumulated through all states:
   - `spec_path` (or `spec` if condensed) — the design document for planning-with-json to read
   - `dependencies` — serial/parallel analysis for phase structuring
   - `selected_skills` — relevant skills for the execution plan
   - `design` — architecture and component details
   - `requirements` — purpose, constraints, success criteria
3. **HANDOFF is the ONLY exit.** Do NOT invoke frontend-design, mcp-builder, or any implementation skill directly. planning-with-json is the next and only step.
4. **Fallback:** If planning-with-json is not available, tell the user: "The planning skill is not installed. Please install it first, or I can describe the execution plan verbally." Keep state as HANDOFF. Only set state to DONE after planning-with-json is successfully invoked.
5. Set state: DONE. vega-punk's responsibility ends here.

**What happens next (managed by planning-with-json, not vega-punk):**
- planning-with-json reads the spec and generates roadmap.json
- planning-with-json presents the plan to the user and offers execution choices
- planning-with-json invokes executing-plans or subagent-driven-development based on user choice
- Execution-stage skills are triggered during the execution phase

**State write:** Read the current JSON, change `state` to "DONE", add `handoff_to`. Keep all existing fields — the full context remains available for downstream skills.
```json
{"state": "DONE", "task": "...", "handoff_to": "planning-with-json"}
```

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

## Skill Dependencies

**Direct dependency (vega-punk invokes):**

- **planning-with-json** — required (called from HANDOFF)

**Downstream dependencies (managed by planning-with-json during execution):**

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
