---
name: brand-design
description: "Build UI against a named brand's design system. Ships 84 DESIGN.md specs (Vercel, Linear, Stripe, Apple, Figma, Claude, ...); resolve the brand, read its spec, map its tokens into the project, then generate. 做什么：按品牌设计系统生成统一风格 UI。何时用：用户要求某品牌风格的前端页面/组件/落地页、对比品牌、或询问可用品牌。触发词: design-md, brand design, 品牌设计, 按品牌生成, 用XX风格, 像Vercel一样, 列出品牌"
allowed-tools: "Read, Write, Edit, Bash, Glob, Grep"
---

# Brand Design

One brand per surface. The chosen `DESIGN.md` is the authority — read it before building, never fill gaps from memory.

## Precedence

When the user names a brand or points at this catalog, this skill outranks generic design skills (`frontend-design`, `ui-ux-pro-max`, `canvas-design`). When the user only wants "a clean modern look" with no brand, defer to those.

## Files

- `INDEX.md` — all 84 brands, one descriptive line each. Resolution starts here.
- `brands/<folder>/DESIGN.md` — the full spec. All 84 carry YAML frontmatter (`version`, `name`, `description`); depth varies:
  - **Full token spec** (74 files): frontmatter also carries `colors`, `typography`, `rounded`, `spacing`, `components`.
  - **Prose spec** (10 files): frontmatter carries `colors` only; remaining tokens live inline in the prose body.
- Target file: `<project-root>/DESIGN.md` — the project root is the git repository root, or the current directory when it is not a repository.

Upstream, commit, and licenses: see `NOTICE`.

## Workflow

### 1. Resolve the brand

Read `INDEX.md` and match the request to one folder. Do not glob all 84 files to guess.

Aliases: `linear`→`linear.app`, `x`/`twitter`→`x.ai`, `opencode`→`opencode.ai`, `mistral`→`mistral.ai`, `together`→`together.ai`, `runway`→`runwayml`, `bmw moto`→`bmw-m`, `dell`→`dell-1996`, `nintendo retro`→`nintendo-2001`.

- Listing brands asked → answer from `INDEX.md` folder names; group if helpful.
- No brand named → ask, offering `vercel`, `linear.app`, `stripe`, `apple`, `figma`, `claude`, or any of the 84.
- Named brand absent → say so and offer the closest `INDEX.md` matches. Never silently substitute.

### 2. Read the spec

Read `brands/<folder>/DESIGN.md` in full. Its tokens, type, layout rules, and prohibitions outrank generic defaults and the project's existing style when the user asked for that brand.

### 3. Choose how far to persist

- Project-wide restyle → copy the spec to `<project-root>/DESIGN.md`.
- One-off page/component → keep the spec in context, do not add a root file.
- Several brands in one project → one spec per brand under `design/<brand>/DESIGN.md`; ask first.
- A `DESIGN.md` already exists at the target → show the differences and ask before overwriting.

### 4. Map tokens into code

- **Token spec:** turn `colors` into CSS custom properties or the Tailwind theme, `typography` into font families and the type scale, `rounded` into radii, `spacing` into the spacing scale, `components` into component styles.
- **Prose spec:** take `colors` from frontmatter, then pull font names and other tokens out of inline backticks.
- **Resolve references first:** spec bodies use `{section.key}` references (e.g. `{colors.primary}`) that point into the YAML frontmatter. Resolve every reference before mapping; `{component.X}` (singular) means the `components` section. `{token.refs}` is a meta-instruction to use references, not a token. If a key is missing from frontmatter, look for its definition in the prose body; if still unresolved, say so and ask — never guess a value, and never emit a literal `{…}` into code.
- Keep every token in one block (`:root` or config). Components reference tokens; no literal hex outside that block.
- Apply the spec's explicit prohibitions. One brand only: never merge tokens from two brands.
- If the project already defines competing tokens, ask whether to replace or reconcile before writing code.
- Format reference: https://github.com/google-labs-code/design.md

### 5. Verify

- [ ] Every color in the UI is in the spec's token set (or a documented neutral).
- [ ] Primary/accent appears only where the spec prescribes; count focal uses.
- [ ] Font families and sizes match the spec.
- [ ] Radii and spacing follow the spec's scale.
- [ ] No second brand's tokens are present.
- [ ] The spec's prohibitions are respected.
- [ ] No literal hex values outside the token block.

Report the brand and the source path used, e.g. `brands/vercel/DESIGN.md`.

## Examples

- "做个像 Vercel 的登录页" → INDEX → `vercel` → read spec → one-off, no root file → build with tokens → run checklist → report source path.
- "这个项目整体用 Linear 风格" → read `linear.app` → ask before overwriting an existing root `DESIGN.md` → write it → build → checklist.
- "有哪些品牌？" → list folders from `INDEX.md`.
- "Vercel 但更暖一点" → start from `vercel`, list the explicit deviations, apply them deliberately; do not blend a second brand.

## Refreshing upstream

1. Copy the new `design-md/` folders into `brands/`.
2. Regenerate `INDEX.md` from each spec's frontmatter `description`.
3. Update the commit in `NOTICE`.

## Anti-patterns

- Recalling a brand's look from memory instead of reading its spec
- Mixing two brands in one UI
- Copying the file without reading it
- Overwriting an existing `DESIGN.md` without asking
- Putting raw hex values in components instead of the token block
