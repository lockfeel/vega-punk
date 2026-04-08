# Self-Recovery Guide

When vega-punk's own state becomes corrupted or inconsistent, use these recovery procedures.

### Symptom: State file contains unknown state value

```
1. Read .vega-punk-state.json
2. If state is not one of: ROUTE, SCAN, CLARIFY, DESIGN, DESIGN_QA,
   DEPENDENCIES, SPEC, SPEC_QA, CONDENSED, QUICK, HANDOFF, REVIEW, DONE
3. → This is a corrupted state. Recovery:
   a. If task and context are present → Set state to CLARIFY (re-clarify with user)
   b. If only task is present → Set state to ROUTE (start from scratch)
   c. If file is empty or unreadable → Delete file, start fresh from ROUTE
4. Tell user: "State file was corrupted. Recovered to [STATE]. Let me know if this doesn't match where we were."
```

### Symptom: State says DESIGN but no design field exists

```
1. State says DESIGN but design field is missing or empty
2. → Design was lost (session interrupted before saving)
3. Recovery: Set state to CLARIFY — re-clarify with user and re-enter DESIGN
4. Tell user: "Design context was lost. Let me re-clarify the requirements."
```

### Symptom: State says HANDOFF but spec_path doesn't exist

```
1. State says HANDOFF or REVIEW but spec file is missing
2. → Spec was never written or was deleted
3. Recovery: Check if design and dependencies fields are present
   a. If present → Re-generate spec from design + dependencies, set state to SPEC
   b. If missing → Set state to CLARIFY, re-run the design flow
4. Tell user: "Spec file was lost. I'll regenerate it from our design."
```

### Symptom: roadmap.json is missing or corrupted

```
1. State says REVIEW but roadmap.json doesn't exist or is invalid JSON
2. → Execution was interrupted before/during planning
3. Recovery:
   a. If .vega-punk-state.json has spec_path and spec exists → Re-run HANDOFF
   b. If no spec exists → Use Self-Recovery for missing spec above
4. Tell user: "Execution plan was lost. I'll regenerate it from our spec."
```

### Symptom: Stuck in a QA loop (retries keep failing)

```
1. DESIGN_QA or SPEC_QA retries reaching 3
2. → The design/spec has a fundamental issue, not a fixable one
3. Recovery:
   a. Stop the loop
   b. Present the specific failing criteria to the user
   c. Ask: "This has failed [N] times. The core issue is: [summary].
           Should we (1) restart design, (2) change requirements, or (3) proceed despite the risk?"
   d. Follow user's direction
4. Do NOT silently increase retry limits
```

### Symptom: Session resumed but state feels wrong

```
1. planning-resume.sh says "Resuming from [STATE]" but the context doesn't match
2. → Stale state from a previous unrelated task
3. Recovery:
   a. Ask user: "I'm seeing state from a previous task ([task summary]).
                Should I continue that, or start fresh?"
   b. If fresh → Apply Post-Completion Cleanup, start ROUTE
   c. If continue → Proceed from the current state
```

### Nuclear Option: Full Reset

If nothing else works, or if the user says "reset everything":

```
1. Archive any existing specs: vega-punk/specs/*.md → *.CANCELLED.md
2. Delete .vega-punk-state.json
3. Delete roadmap.json (if exists)
4. Delete findings.json (if exists)
5. Delete progress.json (if exists)
6. Tell user: "[vega-punk] Full reset complete. Starting fresh. What shall we build?"
7. Start from ROUTE
```
