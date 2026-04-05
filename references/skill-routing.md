# Skill Routing Table

Complete dispatch logic for all 29 installed skills. Use during SCAN state to match tasks to skills.

## How to Route

1. Read the user's task intent
2. Match against categories below (top to bottom)
3. Select ALL relevant skills — tasks often need multiple
4. Note execution order if skills chain (e.g., design → code → test)

---

## File Processing

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **docx** | Create/edit/read Word documents | `.docx`, `Word doc`, `report`, `memo`, `letter`, `template`, `tracked changes`, `find-and-replace in Word` |
| **pdf** | Any PDF operation | `.pdf`, `merge PDF`, `split PDF`, `extract text`, `watermark`, `PDF form`, `OCR`, `rotate PDF` |
| **pptx** | Create/edit presentations | `.pptx`, `deck`, `slides`, `presentation`, `pitch deck`, `PowerPoint` |
| **xlsx** | Spreadsheet operations | `.xlsx`, `.csv`, `.tsv`, `Excel`, `spreadsheet`, `formulas`, `charting`, `financial model`, `clean data` |

## Frontend & Design

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **frontend-design** | Build web pages/components with unique aesthetics | `build web component`, `landing page`, `dashboard`, `React component`, `HTML/CSS`, `beautify UI`, `frontend` |
| **flutter-lens** | Convert screenshots/designs to Flutter code | `复刻 UI`, `实现设计`, `把图变成代码`, `写成 Flutter`, `screenshot to Flutter`, `design to code`, `pixel-perfect Flutter` |
| **ui-ux-pro-max** | UI/UX design decisions, color schemes, accessibility | `UI design`, `UX`, `color scheme`, `typography`, `accessibility`, `dashboard design`, `mobile app design`, `review UI`, `improve UX` |
| **brand-guidelines** | Apply Anthropic brand colors/typography | `branding`, `brand colors`, `typography`, `Anthropic brand`, `corporate identity`, `visual formatting` |
| **theme-factory** | Apply visual themes to outputs | `theme`, `color palette`, `font pairing`, `apply theme`, `Ocean Depths`, `Modern Minimalist`, `custom theme` |
| **canvas-design** | Create posters/art/design as static images | `poster`, `art`, `design`, `static piece`, `visual art`, `canvas` |
| **algorithmic-art** | Generative/algorithmic art with p5.js | `generative art`, `algorithmic art`, `flow field`, `particle system`, `art using code`, `p5.js` |

## Development Workflow

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **planning-with-json** | Create structured implementation plans | `plan`, `roadmap.json`, `multi-step task`, `break down`, `implementation plan`, `create a plan`, `spec to tasks` |
| **executing-plans** | Execute roadmap.json step by step | `execute plan`, `roadmap.json`, `implementation plan`, `execute steps` |
| **subagent-driven-development** | Parallel task execution with subagents | `subagent-driven development`, `dispatch subagent`, `implement tasks`, `roadmap execution` |
| **dispatching-parallel-agents** | Run 2+ independent tasks concurrently | `parallel`, `independent tasks`, `multiple failures`, `different root causes`, `dispatch agents` |
| **using-git-worktrees** | Isolated workspace for feature work | `worktree`, `isolated workspace`, `feature branch`, `set up workspace` |
| **finishing-a-development-branch** | Post-implementation integration decisions | `implementation complete`, `merge`, `create PR`, `finish development`, `complete branch`, `integrate work` |

## Code Quality

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **test-driven-development** | Write tests before implementation | `TDD`, `test-driven`, `write test first`, `red-green-refactor`, `implement feature`, `bug fix`, `refactoring` |
| **systematic-debugging** | Debug bugs, test failures, unexpected behavior | `bug`, `test failure`, `unexpected behavior`, `debug`, `fix this issue`, `not working`, `error`, `performance problem` |
| **receiving-code-review** | Process code review feedback | `code review feedback`, `reviewer suggestion`, `fix review comments`, `implement feedback`, `reviewer said` |
| **requesting-code-review** | Request code review before merge | `code review`, `review my code`, `request review`, `before merge`, `check code quality` |
| **verification-before-completion** | Verify before claiming done | `done`, `complete`, `fixed`, `all tests pass`, `build succeeds`, `ready to commit`, `should work` |

## Automation & Tools

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **agent-browser** | Automate browser interactions | `open a website`, `fill out a form`, `click a button`, `take a screenshot`, `scrape data`, `test this web app`, `login to a site`, `automate browser` |
| **mcp-builder** | Create MCP servers for API integration | `MCP server`, `Model Context Protocol`, `FastMCP`, `MCP SDK`, `external API integration`, `tool server` |
| **slack-gif-creator** | Create animated GIFs for Slack | `GIF for Slack`, `animated GIF`, `make a GIF`, `Slack emoji`, `animated emoji`, `GIF of X doing Y` |
| **find-skills** | Discover and install new skills | `how do I do X`, `find a skill for X`, `is there a skill that can`, `extend capabilities`, `install a skill`, `npx skills` |

## Meta & Communication

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **self-improving-agent** | Learn from experience, improve skills | `self-improve`, `learn from experience`, `从经验中学习`, `自我进化`, `总结教训`, `analyze today's experience`, `improve a skill` |
| **skill-creator** | Create/edit/audit skills | `create a skill`, `author a skill`, `tidy up a skill`, `improve this skill`, `review the skill`, `clean up the skill`, `audit the skill` |
| **internal-comms** | Write internal communications | `3P update`, `company newsletter`, `status report`, `leadership update`, `FAQ`, `incident report`, `project update`, `internal comms`, `weekly update` |

---

## Common Skill Chains

Tasks often require multiple skills in sequence. Recognize these patterns:

### Web App Development
```
ui-ux-pro-max → frontend-design → test-driven-development → verification-before-completion → requesting-code-review
```

### Bug Fix
```
systematic-debugging → test-driven-development → verification-before-completion
```

### Feature Development
```
planning-with-json → subagent-driven-development → requesting-code-review → finishing-a-development-branch
```

### PDF/Document Processing
```
pdf → (docx or xlsx if extraction needed) → internal-comms if writing report
```

### Design to Code
```
flutter-lens → verification-before-completion → requesting-code-review
```

### Data Analysis
```
xlsx → (pdf if report needed) → internal-comms if presenting findings
```

### Browser Automation
```
agent-browser → xlsx (if scraping data) → systematic-debugging (if issues)
```

### Skill Development
```
skill-creator → self-improving-agent (to learn from the experience)
```

---

## Decision Rules

1. **Always select verification-before-completion** for any implementation task
2. **Always select test-driven-development** for any feature/bugfix in codebases with tests
3. **Always select systematic-debugging** when something is broken or failing
4. **Prefer ui-ux-pro-max over frontend-design** when design decisions come first
5. **Prefer subagent-driven-development over dispatching-parallel-agents** when there's a roadmap.json
6. **CONDENSED mode** for tasks completable in < 5 minutes of work
7. **Full flow** for anything spanning multiple files, components, or subsystems
