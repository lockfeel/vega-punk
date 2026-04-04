---
name: vega-punk
description: "Central nervous system for AI sessions. Routes requests, designs solutions, analyzes dependencies, selects skills, and hands off to planning. Use at session start for any task beyond simple Q&A."
---

# Vega-Punk: Session State Machine

**Purpose:** Ensure every creative/implementation task follows a disciplined design flow before execution. Analyzes causal dependencies so the execution plan can maximize parallelism.

**State file:** `.vega-punk-state.json` in the current working directory.
**Spec directory:** `vega-punk/specs/` in the current working directory.

**Recovery:** On session start, read `.vega-punk-state.json`. If valid JSON and `state` is not "DONE", print "Resuming vega-punk from [STATE]: [task]" and resume from that state. If file is missing or corrupted, restart from ROUTE.

**Reset:** If user says "start over" / "new task" / "forget previous", delete `.vega-punk-state.json` and restart from ROUTE.

**State JSON format:** Every state write includes these base fields:
```json
{"state": "<STATE_NAME>", "task": "<user request>", "...state-specific fields..."}
```

**Git:** Add `.vega-punk-state.json` and `vega-punk/` to `.gitignore` if not already present.

**Progress reporting:** At each state transition, announce:
> "Entering [STATE]... (Step X of Y: [remaining steps])"

Use this progress table for estimates:

| State | Estimated | Remaining after |
|-------|-----------|-----------------|
| ROUTE | 1 min | 5-6 states |
| SCAN | 2 min | 5 states |
| CLARIFY | 3-5 min (depends on questions) | 4 states |
| DESIGN | 5 min | 3 states |
| DEPENDENCIES | 3 min | 2 states |
| SPEC | 5 min | 1 state |
| HANDOFF | 1 min | 0 |

If user asks "where are we?" or "how much left?", print the current state and remaining steps.

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
1. Classify:
   - **Informational** → Answer. Set state: DONE. Stop.
   - **Creative/Implementation** → Set state: SCAN. Proceed.
   - **Ambiguous** → Ask one question to classify.
2. **If user says "just write code" / "skip design":** Set state: CONDENSED.

**State write:**
```json
{"state": "SCAN", "task": "<user request>"}
```

---

## SCAN

**Trigger:** State is SCAN.

**Announce:** "Entering SCAN... (Step 2 of 7)"

**Action:**
1. Check project context: files, docs, recent commits.
2. Check scope: If request spans multiple independent subsystems, decompose.
3. Select skills: For each installed skill whose description mentions the task domain, mark it as relevant. Invoke it.

**State write:**
```json
{"state": "CLARIFY", "task": "...", "context": "<summary>", "selected_skills": ["skill1", ...], "scope": "<single|decomposed>"}
```

---

## CLARIFY

**Trigger:** State is CLARIFY.

**Announce:** "Entering CLARIFY... (Step 3 of 7)"

**Action:**
1. Ask clarifying questions one at a time.
2. Prefer multiple choice. Focus on: purpose, constraints, success criteria.
3. If user says "you decide", document assumption and proceed.

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
1. Present the finalized design covering: architecture, components, data flow, error handling, testing.
2. **Design rule:** Each unit has one clear purpose. Can you understand it without reading internals? Can you change internals without breaking consumers? If not, boundaries need work.
3. Get explicit user approval.

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
2. Self-review:
   - Placeholders → Fill or remove
   - Contradictions → Resolve
   - Scope creep → Trim or decompose
   - Ambiguity → Pick one interpretation
   - Dependency check: Are serial dependencies justified?
3. Ask user: "Spec written to `<path>`. Please review before we create the implementation plan."
4. Wait for approval. If changes → Fix → Re-run self-review.

**State write:**
```json
{"state": "HANDOFF", "task": "...", "spec_path": "vega-punk/specs/YYYY-MM-DD-<topic>-design.md"}
```

---

## CONDENSED

**Trigger:** State is CONDENSED.

**Announce:** "Entering CONDENSED mode... (Step 2 of 3)"

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

**Announce:** "Entering HANDOFF... (Step 7 of 7). Design complete, transitioning to planning."

**Action:**
1. Invoke planning-with-json skill.
2. **Data passing:** The `.vega-punk-state.json` file IS the data transfer mechanism. planning-with-json will:
   - Read `.vega-punk-state.json` from the current working directory
   - Extract `dependencies` (if present) to structure phases
   - Extract `selected_skills` to know available skills
   - Extract `spec_path` to read the full design document
3. Do NOT invoke any other implementation skill.

**State write:**
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

## Key Principles

- **One state at a time** — Never skip states. Use CONDENSED for speed.
- **Dependencies drive execution** — Serial blocks, parallel unblocks.
- **One question at a time** — Don't overwhelm.
- **YAGNI ruthlessly** — Remove unrequested features.
- **Working in existing codebases** — Follow existing patterns. No unrelated refactoring.
