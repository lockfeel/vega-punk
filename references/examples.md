# Examples: Planning with JSON in Action

## Example 1: Research Task

**User Request:** "Research the benefits of morning exercise and write a summary"

### roadmap.json (Executable Plan)
```json
{
  "version": "2.0",
  "project": "Morning Exercise Benefits Research",
  "goal": "Create a research summary on benefits of morning exercise",
  "created": "2026-04-04T10:00:00Z",
  "updated": "2026-04-04T10:00:00Z",
  "phases": [
    {
      "id": 1,
      "name": "Research & Discovery",
      "status": "in_progress",
      "steps": [
        {
          "id": "1.1",
          "action": "Search for physical health benefits",
          "tool": "WebSearch",
          "target": "morning exercise physical health benefits",
          "verify": {
            "type": "command_success",
            "expected": "Search returns results"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "1.2",
          "action": "Search for mental health benefits",
          "tool": "WebSearch",
          "target": "morning exercise mental health benefits",
          "verify": {
            "type": "command_success",
            "expected": "Search returns results"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "1.3",
          "action": "Save research findings",
          "tool": "Edit",
          "target": "findings.json",
          "verify": {
            "type": "content_contains",
            "expected": "morning exercise"
          },
          "status": "pending",
          "result": ""
        }
      ]
    },
    {
      "id": 2,
      "name": "Synthesize & Write",
      "status": "pending",
      "steps": [
        {
          "id": "2.1",
          "action": "Create summary document",
          "tool": "Write",
          "target": "morning_exercise_summary.md",
          "verify": {
            "type": "file_exists",
            "expected": "morning_exercise_summary.md created"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "2.2",
          "action": "Deliver to user",
          "tool": "Read",
          "target": "morning_exercise_summary.md",
          "verify": {
            "type": "file_exists",
            "expected": "Summary delivered"
          },
          "status": "pending",
          "result": ""
        }
      ]
    }
  ],
  "current_phase": 1,
  "current_step": "1.1",
  "metadata": {
    "total_steps": 5,
    "completed_steps": 0,
    "completion_rate": "0%"
  }
}
```

### Auto-Execution Flow

1. **Read roadmap.json** → AI knows current step is `1.1`
2. **Execute step 1.1** → Calls `WebSearch` with target
3. **Verify result** → Check if search returned results
4. **Update step status** → Mark `1.1` complete, move to `1.2`
5. **Repeat** → Until all steps complete

---

## Example 2: Bug Fix Task

**User Request:** "Fix the login bug in the authentication module"

### roadmap.json
```json
{
  "version": "2.0",
  "project": "Fix Login Bug",
  "goal": "Identify and fix the login authentication bug",
  "created": "2026-04-04T09:00:00Z",
  "updated": "2026-04-04T09:30:00Z",
  "phases": [
    {
      "id": 1,
      "name": "Reproduce & Understand",
      "status": "complete",
      "steps": [
        {
          "id": "1.1",
          "action": "Run login and capture error",
          "tool": "Bash",
          "target": "npm test -- --grep login",
          "verify": {
            "type": "content_contains",
            "expected": "TypeError"
          },
          "status": "complete",
          "result": "TypeError: Cannot read property 'token' of undefined"
        }
      ]
    },
    {
      "id": 2,
      "name": "Locate & Fix",
      "status": "in_progress",
      "steps": [
        {
          "id": "2.1",
          "action": "Find validateToken function",
          "tool": "Grep",
          "target": "validateToken",
          "verify": {
            "type": "command_success",
            "expected": "Found in src/auth/login.ts"
          },
          "status": "complete",
          "result": "Found at line 42"
        },
        {
          "id": "2.2",
          "action": "Fix async/await issue",
          "tool": "Edit",
          "target": "src/auth/login.ts",
          "verify": {
            "type": "command_success",
            "expected": "File updated"
          },
          "status": "pending",
          "result": ""
        }
      ]
    },
    {
      "id": 3,
      "name": "Test & Verify",
      "status": "pending",
      "steps": [
        {
          "id": "3.1",
          "action": "Run tests to verify fix",
          "tool": "Bash",
          "target": "npm test -- --grep login",
          "verify": {
            "type": "content_contains",
            "expected": "PASS"
          },
          "status": "pending",
          "result": ""
        }
      ]
    }
  ],
  "current_phase": 2,
  "current_step": "2.2",
  "metadata": {
    "total_steps": 4,
    "completed_steps": 2,
    "completion_rate": "50%"
  }
}
```

---

## Example 3: Feature Development

**User Request:** "Add dark mode toggle to settings page"

### roadmap.json
```json
{
  "version": "2.0",
  "project": "Dark Mode Toggle",
  "goal": "Add functional dark mode toggle to settings page",
  "created": "2026-04-04T08:00:00Z",
  "updated": "2026-04-04T08:00:00Z",
  "phases": [
    {
      "id": 1,
      "name": "Research & Design",
      "status": "in_progress",
      "steps": [
        {
          "id": "1.1",
          "action": "Examine existing theme system",
          "tool": "Read",
          "target": "src/styles/theme.ts",
          "verify": {
            "type": "file_exists",
            "expected": "Theme file exists"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "1.2",
          "action": "Find SettingsPage component",
          "tool": "Glob",
          "target": "**/SettingsPage.tsx",
          "verify": {
            "type": "command_success",
            "expected": "Component found"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "1.3",
          "action": "Save design decisions",
          "tool": "Edit",
          "target": "findings.json",
          "verify": {
            "type": "content_contains",
            "expected": "dark mode"
          },
          "status": "pending",
          "result": ""
        }
      ]
    },
    {
      "id": 2,
      "name": "Implementation",
      "status": "pending",
      "steps": [
        {
          "id": "2.1",
          "action": "Add dark theme colors",
          "tool": "Edit",
          "target": "src/styles/theme.ts",
          "verify": {
            "type": "content_contains",
            "expected": "#1a1a2e"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "2.2",
          "action": "Create useTheme hook",
          "tool": "Write",
          "target": "src/hooks/useTheme.ts",
          "verify": {
            "type": "file_exists",
            "expected": "Hook created"
          },
          "status": "pending",
          "result": ""
        },
        {
          "id": "2.3",
          "action": "Add toggle to SettingsPage",
          "tool": "Edit",
          "target": "src/components/SettingsPage.tsx",
          "verify": {
            "type": "content_contains",
            "expected": "useTheme"
          },
          "status": "pending",
          "result": ""
        }
      ]
    },
    {
      "id": 3,
      "name": "Testing",
      "status": "pending",
      "steps": [
        {
          "id": "3.1",
          "action": "Run TypeScript check",
          "tool": "Bash",
          "target": "npx tsc --noEmit",
          "verify": {
            "type": "command_success",
            "expected": "No errors"
          },
          "status": "pending",
          "result": ""
        }
      ]
    }
  ],
  "current_phase": 1,
  "current_step": "1.1",
  "metadata": {
    "total_steps": 7,
    "completed_steps": 0,
    "completion_rate": "0%"
  }
}
```

---

## The Verify-Action Loop

When executing a step:

```
1. READ current step from roadmap.json
   → Know what tool to call and with what target

2. EXECUTE the tool call
   → Perform the action

3. VERIFY the result
   → Check against step.verify.expected
   
4. UPDATE roadmap.json
   → Mark step complete, move to next
   
5. REPEAT until all steps done
```

### Verification Types

| Type | Description | Example |
|------|-------------|---------|
| `file_exists` | Check file was created | "config.json exists" |
| `content_contains` | Check file contains text | "dark mode" in theme.ts |
| `command_success` | Command exits 0 | "npm test passes" |
| `content_not_contains` | Check error is fixed | "TypeError" NOT in output |

---

## Read Before Execute Pattern

**Always read roadmap.json before starting:**

```
[New task received]
→ Read roadmap.json                    # Get current state
→ Find current_step (e.g., "2.1")
→ Execute that step's tool + target
→ Verify result
→ Update step status + move next
```

This creates a self-propelling loop until all phases complete.
