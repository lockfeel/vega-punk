# Skill Routing Table

Complete dispatch logic for all installed skills. Use during SCAN state to match tasks to skills.

**Auto-generated.** Run `bash scripts/sync-routing.sh` to regenerate after adding or editing a sub-skill.

## How to Route

1. Read the user's task intent
2. Match against categories below (top to bottom)
3. Select ALL relevant skills — tasks often need multiple
4. Note execution order if skills chain (e.g., design → code → test)

---

## Development Workflow

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **branch-landing** | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup | `implementation complete`, `merge`, `create PR`, `finish development`, `complete branch`, `integrate work` |
| **parallel-swarm** | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies | `parallel`, `independent tasks`, `multiple failures`, `different root causes`, `dispatch agents` |
| **plan-builder** | Resilient executable planning that never loses context. Creates roadmap.json with phases, steps, code, tools, and verification. Auto-recovers from mid-task disconnects. AI executes step-by-step with automatic progression. Use when you have a spec or requirements for a multi-step task, before touching code. | `plan`, `roadmap.json`, `multi-step task`, `break down`, `implementation plan`, `create a plan`, `spec to tasks` |
| **plan-executor** | Use when you have a written implementation plan (roadmap.json) to execute in the current session with review checkpoints | `execute plan`, `roadmap.json`, `implementation plan`, `execute steps` |
| **task-dispatcher** | Use when executing implementation plans with independent tasks in the current session | `subagent-driven development`, `dispatch subagent`, `implement tasks`, `roadmap execution` |
| **worktree-setup** | Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification | `worktree`, `isolated workspace`, `feature branch`, `set up workspace` |

## Code Quality

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **review-intake** | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation | `code review feedback`, `reviewer suggestion`, `fix review comments`, `implement feedback`, `reviewer said` |
| **review-request** | Use when completing tasks, implementing major features, or before merging to verify work meets requirements | `code review`, `review my code`, `request review`, `before merge`, `check code quality` |
| **root-cause** | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes | `bug`, `fix`, `error`, `not working`, `crash`, `failed`, `exception`, `test failure`, `unexpected behavior`, `debug`, `performance problem` |
| **test-first** | Use when implementing any feature or bugfix, before writing implementation code | `TDD`, `test-driven`, `write test first`, `red-green-refactor`, `implement feature`, `bug fix`, `refactoring` |
| **verify-gate** | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always | `done`, `complete`, `fixed`, `all tests pass`, `build succeeds`, `ready to commit`, `should work` |

## External Skills (not in this repo)

| Skill | When to Use | Triggers |
|-------|-------------|----------|

---

## Common Skill Chains

Tasks often require multiple skills in sequence. Recognize these patterns:

### Web App Development
```
ui-ux-pro-max → frontend-design → test-first → verify-gate → review-request
```

### Bug Fix
```
root-cause → test-first → verify-gate
```

### Feature Development
```
plan-builder → task-dispatcher → review-request → branch-landing
```

### Design to Code
```
flutter-lens → verify-gate → review-request
```

### Skill Development
```
skill-creator → self-improving-agent (to learn from the experience)
```

---

## Decision Rules

1. **Always select verify-gate** for any implementation task
2. **Always select test-first** for any feature/bugfix in codebases with tests
3. **Always select root-cause** when something is broken or failing
4. **Prefer ui-ux-pro-max over frontend-design** when design decisions come first
5. **Prefer task-dispatcher over parallel-swarm** when there's a roadmap.json
6. **CONDENSED mode** for tasks completable in < 5 minutes of work
7. **Full flow** for anything spanning multiple files, components, or subsystems
