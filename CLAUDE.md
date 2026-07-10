# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A row counter web app for knitters. The entire app is one self-contained file, `index.html` (inline CSS + vanilla JS, no framework, no build step, no dependencies). Hard constraints from the owner:

For hosting (GitHub Pages) there are optional companion files — `manifest.webmanifest`, `sw.js` (offline cache, registered only over https; bump its `CACHE` name when assets change), `icon-180.png`/`icon-512.png` — but `index.html` must keep working alone via `file://` when they're absent. App name is "KnitCount" (title, manifest, apple-mobile-web-app-title).

The app icon (yarn ball + two knob-tipped needles top-right + a short needle lower-left) is **pixel-traced from the owner's reference image**, `icon-source.png` (kept in the repo root for regeneration), not hand-drawn. `icon-source.png` is an opaque image — a dark/black glyph on a light background (flat or gradient), not a transparent-bg asset — so `.claude/build_icons.py`'s `get_alpha()` derives coverage from per-pixel darkness (contrast-stretched above `DARK_THRESH`) rather than an alpha channel. Any near-white pixels inside the glyph's own negative space (e.g. gaps between strands, if the source renders those pure white instead of the card color) get swept into "background" the same way and recolored uniformly — the darkness threshold only cares about the black glyph itself. That same pure-stdlib script (no PIL/numpy) crops to the glyph's bounding box and box-downsamples with recoloring to produce `icon-180.png`/`icon-512.png` (black glyph on `#f4f4f4`, the card color, with extra edge padding via `APP_ICON_PAD`) and a small `#ced0d3`-on-transparent raster (`EMPTY_ICON_PAD`, tighter) for the in-app empty-state icon, which sits on the navy page background instead. Run `python3 .claude/build_icons.py` any time `icon-source.png` or the palette changes; it writes the PNGs plus `.claude/empty-icon-datauri.txt` — paste that file's contents into `EMPTY_ICON`'s `<img src="...">` in `index.html` (search for `EMPTY_ICON`). `EMPTY_ICON` is an inline base64 data URI (not a `<svg>`) specifically so it stays pixel-identical to the app icon with zero hand-tracing drift, while still working with no external file over `file://`.

- **Fully offline**: no CDN, no external fonts/scripts, must work when opened via `file://` double-click. Don't add `type="module"` scripts, `fetch()`, or any network dependency. Icons are inline SVG strings, except `EMPTY_ICON` which is an inline base64 PNG data URI (see above).
- **Minimal look, dark theme**: navy page (`--bg #202835`), light cards (`--card #f4f4f4`), teal accent — via CSS variables in `:root`, with a second scope on `.card, .modal, .prow` that re-maps `--text/--muted/--line/--btn` for content drawn on the light cards. Keep the two scopes in sync when adding colors. System font stack, quiet secondary controls (see `.reset`, `.rowmark`). The red `#e5484d` on the swipe-Delete button is the only red allowed.
- All state persists in `localStorage`; the app must never lose counts across reloads.

## Before every push (owner requirement)

This repo is public. Before running `git push` — every time, not just when something feels risky — check that nothing about to go out carries the owner's personal info: their machine username, real email address, passwords/credentials/API keys/tokens, or absolute local paths (e.g. `/Users/<name>/...`). Concretely:

- `git diff` / `git show` the commit(s) being pushed, not just the working tree — a file can look clean now but still carry a leak in an earlier commit that's part of this push.
- Grep the diff for the owner's username, email, and any `/Users/` or other local-machine paths.
- Remember `.claude/launch.json` is gitignored for exactly this reason (it embeds a session-specific absolute path with the username) — if a new file or script does something similar, gitignore it too rather than committing it.
- This already happened once: the username was baked into `.claude/launch.json` across the first two commits and had already reached GitHub before it was caught. It took a `git filter-branch` rewrite + force-push to remove — expensive to fix after the fact, cheap to check before pushing. If a check ever turns up a leak in history (not just the working tree), stop and tell the owner before rewriting anything — rewriting pushed history is destructive and needs their sign-off.

## Commands

There is no build, lint, or test tooling. To develop: edit `index.html`, reload the browser.

Preview server (for the `preview_*` MCP tools): `.claude/launch.json` runs `python3` on a `serve.py` copied into the session scratchpad, serving on port 8742. macOS TCC blocks the sandboxed python from reading this Documents folder directly, so the server serves a **copy** — after editing `index.html`, re-copy it into the scratchpad `serve/` directory (see the `cp` in launch.json's script path) or the preview shows stale code. `.claude/serve.py` is the template for that script. `.claude/launch.json` is **gitignored** (it embeds an absolute local machine path that changes every session) — the `preview_start` tool recreates it automatically if it's missing, so this is expected and not a bug.

## Architecture

Single IIFE in the `<script>` block. One in-memory `state` object is the source of truth; every mutation calls `saveState()` (JSON → localStorage key `stitchCounter.v1`) then `render()` (full DOM rebuild). Exceptions: `updateNote()` and `renameProject()` save without re-rendering, so typing in a label / project name doesn't lose input focus — preserve this if touching that logic.

State shape (schema v2 — multi-project):

```json
{
  "version": 2,
  "nextId": 4,
  "nextProjectId": 3,
  "currentProjectId": "p_1",
  "projects": [{
    "id": "p_1",
    "name": "Project 1",
    "lastUsed": 0,
    "counters": [{ "id": "c_1", "count": 3, "note": "Sleeve", "rowMark": "start" }],
    "rows": [["c_1"], ["c_2", "c_3"]],
    "history": [{ "count": 3, "note": "Sleeve", "action": "removed", "ts": 0 }]
  }]
}
```

- Each project owns its `counters`, `rows`, and `history`. `cur()` returns the current project; all counter operations act on it. `touch(p)` stamps `lastUsed` — call it from every project-data mutation; the projects list renders sorted by it (newest last-edit first, display-sort only, storage order untouched) and deleting the current project falls back to the most recently used one.
- Two screens in one page, no subtitles/taglines (owner removed them, don't re-add):
  - `#screen-project`: top row = "All Projects" back button (left) + history clock (right); below it the title row = project-type icon + project name + pencil.
  - `#screen-projects`: recency-sorted rows (type icon + name + pencil, swipe left for Delete) + "Add a project to start." empty state centered on screen when there are none.
  - The in-memory `view` variable ("project" | "projects") picks which; it is **not persisted** — reload lands on the current project's counters (or the projects screen when there are zero projects). Screens toggle via the `hidden` attribute, which relies on the UA stylesheet's `[hidden]{display:none}`; because `#screen-project` also has its own `display:flex` (an ID selector, so it wins on specificity), there's an explicit `#screen-project[hidden]{display:none}` override right after it — drop that and the empty counter screen shows through behind the projects list.
- **Names are edited only via their pencil button** (`beginNameEdit`/`endNameEdit`): at rest name inputs are `readonly` + `pointer-events: none` (so taps fall through — on a list row that opens the project) and show no background; the pencil flips on the `.editing` class, focuses, and selects. Editing ends on focusout AND on any `pointerdown` outside the field (belt-and-suspenders — blur events don't always fire). The header name input auto-sizes to its text via canvas `measureText` (`sizeNameInput`), as do the list names, and the header pencil's 24px footprint mirrors the type icon so the title stays centered (its 18×18 SVG needs an explicit `.title-edit svg { width/height }` rule — it's a flex item inside another flex item, `.title-edit` inside `.title-row`, and without a pinned size it silently shrinks below its `width`/`height` attributes). The header's icon-to-name gap and name-to-pencil gap are two different values (12px / 16px) via `.project-name`'s asymmetric left/right padding, not `.title-row`'s `gap`.
- "+ Add project" stays on the projects list and puts the new row (smallest free "Project N") into name-edit mode with the text selected as a rename hint.
- Project-type icons: `PROJECT_ICONS` inline-SVG map + `ICON_KEYWORDS` whole-word matching on the name (specific garments before generic words; `yarn` ball is the fallback). Used in list rows and the header; updates live while typing.
- Both "+ Add …" buttons are `position: fixed` at the bottom (`.add`, z-index 4 under a dragged card at 5 and the modal at 10); `.wrap` carries extra bottom padding so content scrolls clear.
- `rows` is the layout: each row holds 1–2 counter ids. **Compact mode is derived, never stored**: if any row has 2 ids, `.list` gets the `compact` class and all cards render half-width (`isCompact()`).
- `nextId` and `nextProjectId` increment forever, never reused — but they only feed **ids**. Default project names come from `nextProjectName()`: the smallest "Project N" not already taken in the current list (gaps left by deletes get refilled; with no projects the next one is "Project 1" again). Custom names don't block numbers.
- `history` keeps the last 5 reset/removed counts per project (`HISTORY_MAX`). The list is tucked behind the clock icon (`#history-toggle`, inline SVG) on the All Projects row: hidden by default, toggled by the in-memory `historyOpen` flag (not persisted, reset when switching projects), and the icon itself only renders when the project has history (needs its `[hidden] { display: none }` guard since the button is `display: flex`). Opening scrolls the list (at the page bottom) into view. `#screen-project` is a flex column (`min-height: 100vh`/`100dvh`) and `.history` has `margin-top: auto` — this pushes History to the bottom of the screen when the counters don't fill it; when they do, the auto margin collapses to 0 and `.history`'s own `padding-top: 40px` is the only gap. The `HISTORY` heading is centered but the row content (`.h-row`) is left-aligned.
- `loadState()` normalizes/validates everything and falls back to `seed()` on corrupt data. `seed()` returns **zero projects** (empty `projects`, `currentProjectId: null`), so a first run — and the corrupt-data fallback — opens on the "Add a project to start." screen; nothing is persisted until the user adds a project. It migrates v1 data (top-level `counters`/`rows`/`history`) into a single project named "Project 1", and still handles the older legacy schema where counters had `half` flags instead of `rows`.

Event handling is **delegated**: single `click`/`input`/`focusout`/`dblclick`/`pointer*` listeners on `#list`, dispatched via `data-action` attributes and `data-id` on cards. Never attach listeners inside `buildCard()` — they'd be lost on re-render.

Drag-to-reorder (`pointerdown` on `.drag` handle) uses pointer events + `setPointerCapture`, a fixed-positioned card, and a placeholder element (`ph-row` for own-row drops, `ph-card` for pairing beside a lone card — pointer on the outer 35% of it). On drop, `endDrag()` derives the new `rows` from placeholder DOM position and calls `render()`. The handle has `touch-action: none`; counting buttons use `touch-action: manipulation`.

Swipe-to-delete on project rows: each `.prow` slides inside an `overflow: hidden` `.prow-wrap` over an absolutely-positioned red `.p-delete`. Delegated `pointer*` listeners on `#plist` engage only on a clearly horizontal move (≥12px and |dx|>|dy|; `.prow` has `touch-action: pan-y`), follow the finger clamped to [-96, 0], and snap via the `.swiped` class past -48. Two traps to preserve: the click after a swipe is suppressed (`suppressClick`, checked FIRST in the click handler so a swipe ending over Delete can't fire it), and a `pointerdown` on the open row's own Delete button must not close the row (or it slides back over the button mid-tap and the tap is lost).

## Behavioral rules (owner decisions — keep these)

- Decrement clamps at 0; counter never goes negative.
- Reset (button or double-tap on the number) and remove show the confirm modal — **except** when count is 0: then they act silently and are NOT added to history.
- The app never drops below one counter: removing the last counter resets it (count 0, label cleared, rowMark "start") instead of deleting it.
- Projects are deleted only via swipe-left → red Delete. It follows the same confirm pattern: confirms ("…Its counters will be lost.") **except** when nothing was ever counted (all counts 0, empty history) — then it deletes silently. Deleting the current project switches to the most recently used remaining one. Deleting the **last** project is allowed (owner decision — unlike counters there is no reset-in-place): zero projects is a valid persisted state, the projects list shows the "Add a project to start." empty state, and reload lands on the projects screen until one is added.
- Project names are trimmed on blur; an empty name shows the "Untitled project" placeholder. Renaming is pencil-only (owner decision, made airtight after taps kept editing names): tapping a name at rest must never focus it.
- Labels are trimmed on blur; empty label shows the `…` placeholder.
- Width is never set manually: pairing happens by dragging a card beside another; when no pairs remain, all cards return to full width automatically.
- The label, count, and Reset button must all be horizontally centered on the card. The label is absolutely positioned with `left`/`right` insets — **keep them equal** (currently 118px full, 54px compact) or the label drifts off-center; the insets just need to clear the rowmark pill (wider than the × button). Verify centering by comparing `getBoundingClientRect()` centers, not by eye.
