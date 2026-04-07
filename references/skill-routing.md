# Skill Routing Table

Complete dispatch logic for all installed skills. Use during SCAN state to match tasks to skills.

**Maintenance:** This table is manually updated. When a new skill is installed, update this routing table within the same session. If unsure whether a skill applies, invoke it anyway (1% Rule).

## How to Route

1. Read the user's task intent
2. Match against categories below (top to bottom)
3. Select ALL relevant skills — tasks often need multiple
4. Note execution order if skills chain (e.g., design → code → test)

---

## File Processing

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **docx** | Create/edit/read Word documents | `.docx`, `Word doc`, `report`, `memo`, `letter`, `template`, `tracked changes`, `find-and-replace in Word`, `Word 文档`, `创建文档` |
| **pdf** | Any PDF operation | `.pdf`, `merge PDF`, `split PDF`, `extract text`, `watermark`, `PDF form`, `OCR`, `rotate PDF`, `合并 PDF`, `提取 PDF 文字` |
| **pptx** | Create/edit presentations | `.pptx`, `deck`, `slides`, `presentation`, `pitch deck`, `PowerPoint`, `演示文稿`, `幻灯片` |
| **xlsx** | Spreadsheet operations | `.xlsx`, `.csv`, `.tsv`, `Excel`, `spreadsheet`, `formulas`, `charting`, `financial model`, `clean data`, `表格`, `数据处理` |

## Frontend & Design

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **frontend-design** | Build web pages/components with unique aesthetics | `build web component`, `landing page`, `dashboard`, `React component`, `HTML/CSS`, `beautify UI`, `frontend`, `前端`, `网页` |
| **flutter-lens** | Convert screenshots/designs to Flutter code | `复刻 UI`, `实现设计`, `把图变成代码`, `写成 Flutter`, `screenshot to Flutter`, `design to code`, `pixel-perfect Flutter` |
| **ui-ux-pro-max** | UI/UX design decisions, color schemes, accessibility | `UI design`, `UX`, `color scheme`, `typography`, `accessibility`, `dashboard design`, `mobile app design`, `review UI`, `improve UX`, `界面设计`, `用户体验` |
| **brand-guidelines** | Apply Anthropic brand colors/typography | `branding`, `brand colors`, `typography`, `Anthropic brand`, `corporate identity`, `visual formatting` |
| **theme-factory** | Apply visual themes to outputs | `theme`, `color palette`, `font pairing`, `apply theme`, `Ocean Depths`, `Modern Minimalist`, `custom theme`, `主题` |
| **canvas-design** | Create posters/art/design as static images | `poster`, `art`, `design`, `static piece`, `visual art`, `canvas`, `海报`, `设计图` |
| **algorithmic-art** | Generative/algorithmic art with p5.js | `generative art`, `algorithmic art`, `flow field`, `particle system`, `art using code`, `p5.js`, `生成艺术` |

## Development Workflow

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **planning-with-json** | Create structured implementation plans | `plan`, `roadmap.json`, `multi-step task`, `break down`, `implementation plan`, `create a plan`, `spec to tasks`, `计划`, `规划` |
| **executing-plans** | Execute roadmap.json step by step | `execute plan`, `roadmap.json`, `implementation plan`, `execute steps`, `执行计划` |
| **subagent-driven-development** | Parallel task execution with subagents | `subagent-driven development`, `dispatch subagent`, `implement tasks`, `roadmap execution`, `子代理` |
| **dispatching-parallel-agents** | Run 2+ independent tasks concurrently | `parallel`, `independent tasks`, `multiple failures`, `different root causes`, `dispatch agents`, `并行`, `并发` |
| **using-git-worktrees** | Isolated workspace for feature work | `worktree`, `isolated workspace`, `feature branch`, `set up workspace`, `隔离工作区` |
| **finishing-a-development-branch** | Post-implementation integration decisions | `implementation complete`, `merge`, `create PR`, `finish development`, `complete branch`, `integrate work`, `合并代码` |

## Code Quality

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **test-driven-development** | Write tests before implementation | `TDD`, `test-driven`, `write test first`, `red-green-refactor`, `implement feature`, `bug fix`, `refactoring`, `测试驱动`, `先写测试` |
| **systematic-debugging** | Debug bugs, test failures, unexpected behavior | `bug`, `test failure`, `unexpected behavior`, `debug`, `fix this issue`, `not working`, `error`, `performance problem`, `调试`, `修复 bug` |
| **receiving-code-review** | Process code review feedback | `code review feedback`, `reviewer suggestion`, `fix review comments`, `implement feedback`, `reviewer said`, `处理审查意见` |
| **requesting-code-review** | Request code review before merge | `code review`, `review my code`, `request review`, `before merge`, `check code quality`, `代码审查` |
| **verification-before-completion** | Verify before claiming done | `done`, `complete`, `fixed`, `all tests pass`, `build succeeds`, `ready to commit`, `should work`, `验证完成` |

## Automation & Tools

| Skill | When to Use | Triggers |
|-------|-------------|----------|
| **agent-browser** | Automate browser interactions | `open a website`, `fill out a form`, `click a button`, `take a screenshot`, `scrape data`, `test this web app`, `login to a site`, `automate browser`, `浏览器自动化` |
| **mcp-builder** | Create MCP servers for API integration | `MCP server`, `Model Context Protocol`, `FastMCP`, `MCP SDK`, `external API integration`, `tool server` |
| **slack-gif-creator** | Create animated GIFs for Slack | `GIF for Slack`, `animated GIF`, `make a GIF`, `Slack emoji`, `animated emoji`, `GIF of X doing Y` |
| **find-skills** | Discover and install new skills | `how do I do X`, `find a skill for X`, `is there a skill that can`, `extend capabilities`, `install a skill`, `npx skills`, `找技能` |

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
