# Skill Invocation Chain

The complete workflow showing where vega-punk's responsibility ends and downstream skills take over.

## Flow Diagram

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

## Execution Skills (managed by planning-with-json, not vega-punk)

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
