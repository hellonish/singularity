# Handoff: Singularity — Research + Chat Workspace

## Overview
Singularity is an AI research workspace. A user submits a prompt in either **Research** mode
(produces a long, sourced report) or **Chat** mode (quick back-and-forth). Reports are browsed
as cards, opened into a two-pane reading view (article + scoped chat), and providers/API keys are
managed in a settings modal. A first-run spotlight onboarding walks the user through connecting a
provider and sending a first message.

## About the Design Files
The file in this bundle — `Singularity.dc.html` — is a **design reference built in HTML**. It is a
working prototype that shows the intended look, layout, and interactions. **It is not production
code to copy.** Your task is to **recreate this design inside the existing `_frontend` Next.js app**,
using that codebase's established patterns (React components, Tailwind v4 `@theme` tokens in
`src/app/globals.css`, the App Router structure under `src/app/`). The routes already exist
(`/dashboard`, `/reports/[id]`, `/profile`) — map the prototype's views onto them rather than
introducing a new structure.

To view the prototype: open `Singularity.dc.html` in a browser (it self-loads its runtime). Read the
`class Component extends DCLogic` block at the bottom for exact state logic, data shapes, and handlers.

## Fidelity
**High-fidelity.** Colors, typography, spacing, radii, and interactions are final. Recreate the UI
faithfully using the codebase's Tailwind tokens and component conventions. The prototype's inline
styles map directly to the token table below — wire those into `globals.css` variables, don't hardcode
hex values in components.

## Design Tokens

The design is theme-driven via CSS custom properties on a `[data-app-theme]` wrapper. Two themes:
`light` (default) and `dark`. Wire these into the existing `:root` / theme layer in `globals.css`.

### Light theme (`data-app-theme="light"`)
| Token | Value |
|---|---|
| `--bg` | `#f7f5f0` (warm paper) |
| `--bg-sunken` | `#ece9e2` |
| `--surface` | `#ffffff` |
| `--surface-2` | `#faf8f4` |
| `--surface-3` | `#ece9e2` |
| `--border` | `rgba(42,40,36,0.10)` |
| `--border-strong` | `rgba(42,40,36,0.17)` |
| `--text` | `#2a2824` |
| `--text-dim` | `#5c5952` |
| `--text-faint` | `#9a968d` |
| `--accent` | `#7c5230` (deep brown — the selected accent) |
| `--accent-2` | `#5f3d21` (hover/links, darker) |
| `--accent-soft` | `rgba(124,82,48,0.12)` |
| `--ok` | `#0f9d78` · `--warn` `#c47510` · `--danger` `#d94a38` |
| `--shadow` | `0 18px 50px rgba(20,30,55,0.14)` |
| `--shadow-sm` | `0 1px 3px rgba(20,30,55,0.06)` |

### Dark theme (`data-app-theme="dark"`)
| Token | Value |
|---|---|
| `--bg` | `#0b0a09` (near-black, warm) |
| `--bg-sunken` | `#050505` |
| `--surface` | `#141210` |
| `--surface-2` | `#1c1915` |
| `--surface-3` | `#25211b` |
| `--border` | `rgba(255,255,255,0.09)` |
| `--border-strong` | `rgba(255,255,255,0.17)` |
| `--text` | `#efece6` |
| `--text-dim` | `#a9a39a` |
| `--text-faint` | `#6f685f` |
| `--accent` / `--accent-2` | **derived** — a lightened tint of the light-theme accent (see Accent behavior) |
| `--accent-soft` | `rgba(99,102,241,0.16)` base fallback |
| `--ok` | `#3fc8a4` · `--warn` `#e6a13c` · `--danger` `#f26d5b` |
| `--shadow` | `0 16px 48px rgba(0,0,0,0.5)` · `--shadow-sm` `0 1px 3px rgba(0,0,0,0.45)` |

### Accent behavior (important)
A single **selected accent** (default `#7c5230`) drives both themes:
- **Light theme:** `--accent` = selected hex; `--accent-2` = selected darkened ~14%.
- **Dark theme:** `--accent` = selected **lightened ~42%**; `--accent-2` = selected **lightened ~62%**.

Lightening formula (per channel, `amt` 0–1): `c + (255 - c) * amt`. Darkening (`amt` negative):
`c * (1 + amt)`. See `lighten(hex, amt)` and `applyAccent()` in the prototype for the reference
implementation. Implement this as a small util that recomputes `--accent`/`--accent-2` whenever the
theme or selected accent changes.

### Type
- **Serif (UI + body):** Newsreader (Google Fonts), weights 300–500, includes italic. Used for
  titles, report body, buttons-with-text, message bubbles. Headings use `font-weight:300`, often
  `font-style:italic`, `letter-spacing:-.02em`.
- **Mono (labels/meta):** JetBrains Mono, 400/500. Used for uppercase eyebrow labels
  (`letter-spacing:.12–.16em; text-transform:uppercase`), chips, metadata, code.
- Body base ~17px / line-height 1.6–1.72. Report H1 38px, card title 17px, lead paragraph 21px.

### Radii & spacing
Radii: chips/buttons `9–11px`, cards `14px`, modals/menus `13–20px`, pills/dots `999px`/`50%`.
Composer container `20px`. Spacing is 4px-based (gaps of 8/12/16px dominate).

## Screens / Views

State machine: `view ∈ {'grid','chat','report'}`. Sidebar + top chrome persist across all.

### 1. Sidebar (persistent, collapsible)
- Width **264px** open, **62px** collapsed; `transition:width .2s`. Background `--surface`,
  right border `--border`.
- **Header (58px):**
  - *Open:* logo image (32px) + "Singularity" title (18px/500) + a **collapse arrow button on the
    far right** (`margin-left:auto`, 34px, chevron-left `‹`).
  - *Collapsed:* single centered 38px logo button that swaps to a chevron-right `›` on hover
    (crossfade, `.15s`).
- **New research** button (full-width, mono, 40px, `--surface-2` + `--border-strong`).
- **Research** section: list of reports. Each row = a **monochrome** file-glyph icon
  (`--text-faint`, NOT tier-colored), title (13.5px, ellipsis), and chat count (mono, faint).
  Active row `--accent-soft`. Active+open rows expand to show child chats (indented, left border)
  plus a "New chat" action.
- **Chats** section: standalone chats (message-glyph icon + title).

### 2. Grid / Dashboard (`view:'grid'`)
- Scroll area, max-width **1180px**, padding `90px 32px 40px`.
- Header row: mono eyebrow "Workspace", H1 *"Recent research"* (34px/300 italic), and a right-aligned
  "{n} reports" count.
- **Report cards** grid: `repeat(auto-fill, minmax(268px, 1fr))`, gap 16px. Each card
  (`--surface`, `--border`, radius 14px, `--shadow-sm`, `sg-rise` entrance):
  - Top row: **only** a right-aligned `v{ver}` badge (`--accent-soft`/`--accent-2`). *(The tier/mode
    label — Ultra/High/etc. — and its colored dot were intentionally removed.)*
  - Title (17px/300 italic).
  - Meta row (mono, 11px): time · chat-count-with-icon. *(Character count intentionally removed.)*
  - Whole card is a button → opens report.
- **Composer** (pinned bottom, gradient fade): max-width 720px, `--surface` card, radius 20px,
  `--shadow`. Contains: auto-grow textarea (18px serif) + a control row of chips
  (Mode / Effort / Model) + a send button. Below: centered mono hint line.

### 3. Standalone chat (`view:'chat'`)
- Same scroll container; centered column max-width 720px, padding-top 90px.
- Messages: user bubbles right-aligned (`--accent-soft`, radius `15px 15px 4px 15px`), assistant
  left-aligned plain text (16px). Each preceded by a mono uppercase "You" / "Singularity" label.
- Uses the same bottom composer as the grid.

### 4. Report view (`view:'report'`)
Two panes inside a flex row.
- **Article pane** (flex:1, scroll): `<article>` max-width 720px, padding `88px 40px 80px`.
  - Header block: mono eyebrow "Research Report" (`--accent-2`), H1 (38px/300), mono meta line
    (Depth · chars · version · time), bottom border.
  - Body is a sequence of typed blocks, each with its own style (see Block types).
- **Chat panel** (right, **400px**, `--surface`, left border) OR **collapsed rail** (56px).
  - *Panel header* (`display:flex; gap:8px`): **collapse arrow button on the LEFT** (38px,
    chevron-right `›`), then the **thread dropdown on the right** (`flex:1`) showing active chat
    title + "Chat X of N", opening a menu of the report's chats + "New chat on this report".
  - Messages list (same bubble styling as standalone chat).
  - Follow-up composer: `--surface-2` card, textarea + model chip + send.
  - *Collapsed rail:* vertical bar with an expand chevron and vertical "{n} chats" label; click expands.

### 5. Settings modal
- Scrim `rgba(6,9,14,0.58)` + `backdrop-filter:blur(3px)`, `sg-scrim` fade. Dialog
  `min(760px,100%)`, `--surface`, radius 20px, `sg-pop` entrance.
- Header: eyebrow "Settings" + H2 "Model providers" (italic) + close button.
- Two columns: **provider list** (212px, colored square dot + name + sub + connected dot) and a
  **detail pane** (provider blurb, password API-key input + Save, a "How to get your key" card with
  numbered steps and an external link).

### 6. Onboarding (spotlight, first run)
- Full-screen click blocker; a **spotlight** cut-out (2px `--accent-2` outline +
  `box-shadow:0 0 0 9999px rgba(6,9,14,0.74)`) positioned over the live target element measured via
  `getBoundingClientRect()`. A dashed **curved SVG arrow** points from the guidance card to the target.
- Guidance card: logo + "Getting started" eyebrow + "Step X / Y" pill, title (25px/300 italic),
  description, progress bars, Skip + primary CTA.
- 5 steps target elements by `data-tour` attribute: `settings → providers → keyfield → mode →
  composer`. Steps may open the settings modal / switch view as needed. Re-measures on resize and
  after step changes (`setTimeout ~300ms`).

## Top chrome (persistent, absolute over main)
Right-aligned pill buttons (36px, `--surface`, `--border`, radius 999px): **theme toggle**
(sun/moon), **settings** (`data-tour="settings"`), and **account avatar** ("A", `--accent-soft`)
which opens a menu (name/email, Settings, Log out). When in report view, a left **"Projects"** back
pill appears.

## Interactions & Behavior
- **Chips** (Mode / Effort / Model / Provider / Thread): click toggles a popover; a full-screen
  transparent overlay (`z-index:40`) closes any open menu on outside click. Only one `openMenu` at a
  time (`'mode'|'effort'|'model'|'thread'|'rmodel'`).
- **Send gating:** research mode requires ≥10 chars; send button disabled state uses `--surface-3`.
  Enter submits, Shift+Enter newlines.
- **Submit:** research mode → opens report `r1` and seeds a scoped chat; chat mode → creates a new
  standalone chat prepended to the sidebar list, with a seeded assistant reply referencing the
  selected effort tier.
- **Theme toggle** flips `theme` and recomputes accent (see Accent behavior).
- **Animations:** `sg-rise` (cards), `sg-pop` (menus/modals), `sg-scrim` (backdrop), `sg-grow`
  (chart bars, `transform-origin:bottom`). Durations `.16–.5s`, easing `ease` /
  `cubic-bezier(.2,.8,.2,1)`.

## State Management
Single component state (port to React state / a store — the codebase has `src/stores/`):
`theme`, `accent`, `sidebarOpen`, `view`, `mode` ('research'|'chat'), `intensity`
('instant'|'medium'|'high'|'ultra'), `modelId`, `openMenu`, `chatCollapsed`, `settingsOpen`,
`userMenuOpen`, `onboarding`, `obStep`, `tourRect`, `provider`, `keys` (per-provider),
`query`, `reportQuery`, `activeReportId`, `activeChatId`, `activeStandaloneId`, `standaloneChats[]`,
`chatMessages[]`.

Tweakable defaults (surface as config/props): `startTheme` (default `light`), `defaultMode`
(default `chat`), `accent` (default `#7c5230`).

## Reference data shapes (from prototype)
- `MODELS`: groups (Anthropic/OpenAI/DeepSeek/xAI/Groq) each `{group, dot, items:[{id,name}]}`.
- `PROVIDERS`: `{id,name,sub,dot,url,prefix,blurb,docHint}`.
- `INTENSITIES`: `{id,name,bars,desc}` — Instant/Medium/High/Ultra.
- `REPORTS`: `{id,title,time,chars,ver,tier,chats:[{id,title}]}`.
- `BLOCKS`: report body block types — `lead, h2, p, callout, stats, chart, table, image, quote, refs`.
  Chart bars animate; last bar uses `--ok`. Tables render mono, first column `--text`.

## Block types (report body)
`lead` (21px/300), `h2` (15px/500 with bottom border), `p` (17px/1.72), `callout`
(`--accent-soft`, left `--accent` border), `stats` (3-col metric cards), `chart` (CSS bar chart,
`data-om-raster`), `table` (bordered, mono), `image` (striped placeholder — swap for real asset
slot), `quote` (22px/300 italic, left accent border), `refs` (numbered reference list with links).

## Assets
- `assets/singularity-logo.png` — app logo (sidebar + onboarding card). Move into `public/` or
  `src/assets/` per codebase convention.
- Report `image` blocks use a striped monospace placeholder — replace with real figure assets or an
  upload slot.
- Provider "dot" colors are brand marks (Anthropic `#d97757`, OpenAI `#10a37f`, DeepSeek `#4d6bfe`,
  xAI `#c9ccd1`, Groq `#f55036`).

## Files
- `Singularity.dc.html` — the full hifi prototype (markup + logic). Read the bottom `<script>` block
  for exact handlers, seed copy, and geometry math (onboarding spotlight/arrow).
- `assets/singularity-logo.png` — logo asset.

## Target codebase notes (`_frontend`)
- Next.js App Router, Tailwind v4 (`@theme` in `src/app/globals.css`), Newsreader + JetBrains Mono
  already configured as `--font-newsreader` / `--font-jetbrains-mono`.
- Existing routes: `/dashboard`, `/reports/[id]`, `/profile`, plus `api/auth`. Map: grid→dashboard,
  report view→`/reports/[id]`, account menu→profile.
- The current `globals.css` accent is `#6366f1` — update the shell/accent tokens to the values in
  this doc (or make accent configurable per the Accent behavior section).
