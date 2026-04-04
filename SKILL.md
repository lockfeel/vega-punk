---
name: vega-punk
description: "Use when starting any conversation - determines if brainstorming is needed or direct answer suffices. For creative/implementation tasks: explores intent, requirements, design, selects relevant skills, then transitions to planning. For simple queries: answers directly."
---

# Vega-Punk: Session Entry & Design

## Step 0 — Route the Request

**On every new conversation, decide immediately:**

| If the user says... | Then... |
|---------------------|---------|
| "What does X do?" / "Explain this error" / "Fix this typo" / "How do I...?" | **Answer directly. Done.** |
| "Build X" / "Add X" / "Refactor X" / "Design X" / Any create/modify/extend request | **Continue to Step 1** |

<HARD-GATE>
If this is a creative/implementation task: Do NOT write code, scaffold projects, or invoke implementation skills until the user has approved your design.
</HARD-GATE>

---

## Step 1 — Explore Context

Check the current project state: files, docs, recent commits.

**If the request is too large** (multiple independent subsystems), flag it immediately. Help the user decompose into sub-projects. Each sub-project gets its own spec → plan → implementation cycle.

---

## Step 2 — Offer Visual Companion (Conditional)

**Only if upcoming questions will involve visual content** (mockups, layouts, diagrams), offer this as its own message:

> "Some of what we're working on might be easier to explain if I can show it to you in a web browser. I can put together mockups, diagrams, comparisons, and other visuals as we go. This feature is still new and can be token-intensive. Want to try it? (Requires opening a local URL)"

**Wait for response.** If they decline, proceed to Step 3. If they accept, **first read `skills/vega-punk/visual-companion.md`**, then follow it.

---

## Step 3 — Ask Clarifying Questions

- One question at a time. Prefer multiple choice.
- Focus on: purpose, constraints, success criteria.
- Do not combine questions with other content.

---

## Step 4 — Propose Approaches

- Propose 2-3 approaches with trade-offs.
- Lead with your recommended option and explain why.

---

## Step 5 — Present Design

- Scale each section to complexity: a few sentences if straightforward, up to 200-300 words if nuanced.
- Ask after each section whether it looks right so far.
- Cover: architecture, components, data flow, error handling, testing.
- **Design rule:** Break the system into smaller units that each have one clear purpose. Can someone understand a unit without reading its internals? Can you change internals without breaking consumers? If not, the boundaries need work.

---

## Step 6 — Select Skills

Identify which skills to use during implementation. Announce them: "I'll use [skill names] during implementation."

**Skill priority:**
1. Process skills first (debugging, testing) — determine HOW to approach
2. Implementation skills second (frontend-design, mcp-builder) — guide execution

**The 1% rule:** If there's even a 1% chance a skill applies, invoke it.

**Skill types:**
- **Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.
- **Flexible** (patterns): Adapt principles to context. The skill itself tells you which.

**Instruction priority:** User's explicit instructions > Skills > Default system prompt.

---

## Step 7 — Write Design Doc

Save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. Commit to git.

---

## Step 8 — Spec Self-Review

Look at the spec with fresh eyes. Fix any issues inline:

1. **Placeholder scan:** Any "TBD", "TODO", incomplete sections? Fix them.
2. **Internal consistency:** Do any sections contradict each other? Fix them.
3. **Scope check:** Focused enough for a single plan, or needs decomposition?
4. **Ambiguity check:** Could any requirement be interpreted two different ways? Pick one and make it explicit.

---

## Step 9 — User Review Gate

> "Spec written and committed to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan."

**Wait for response.** If changes requested, make them and re-run Step 8. Only proceed once the user approves.

---

## Step 10 — Transition to Implementation

**Invoke the planning-with-json skill.** Do NOT invoke any other implementation skill. planning-with-json is the only next step.

---

## Red Flags — STOP, You're Rationalizing

| If you think... | The reality is... |
|-----------------|-------------------|
| "This is too simple to need a design" | Simple projects are where unexamined assumptions cause the most wasted work |
| "I'll just do this one thing first" | Check the flow BEFORE doing anything |
| "I need more context first" | Skill check comes BEFORE clarifying questions |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first |
| "This doesn't need a formal skill" | If a skill exists, use it |
| "The skill is overkill" | Simple things become complex. Use it |

## Key Principles

- **One question at a time** — Don't overwhelm
- **Multiple choice preferred** — Easier to answer
- **YAGNI ruthlessly** — Remove unrequested features
- **Explore alternatives** — Always propose 2-3 approaches
- **Incremental validation** — Present design, get approval before moving on
- **Working in existing codebases** — Follow existing patterns. Don't propose unrelated refactoring.
