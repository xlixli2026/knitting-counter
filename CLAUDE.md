# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A row counter web app for knitters. The entire app is one self-contained file, `index.html` (inline CSS + vanilla JS, no framework, no build step, no dependencies). Hard constraints from the owner:

For hosting (GitHub Pages) there are optional companion files — `manifest.webmanifest`, `sw.js` (offline cache, registered only over https), `icon-180.png`/`icon-512.png` (regenerate with a script if the palette changes; teal square, cream circle, teal plus) — but `index.html` must keep working alone via `file://` when they're absent.

- **Fully offline**: no CDN, no external fonts/scripts, must work when opened via `file://` double-click. Don't add `type="module"` scripts, `fetch()`, or any network dependency.
- **Minimal look**: warm-neutral palette via CSS variables in `:root`, system font stack, quiet secondary controls. New controls should match the existing muted style (see `.reset`, `.rowmark`).
- All state persists in `localStorage`; the app must never lose counts across reloads.

## Commands

There is no build, lint, or test tooling. To develop: edit `index.html`, reload the browser.

Preview server (for the `preview_*` MCP tools): `.claude/launch.json` runs `python3` on a `serve.py` copied into the session scratchpad, serving on port 8742. macOS TCC blocks the sandboxed python from reading this Documents folder directly, so the server serves a **copy** — after editing `index.html`, re-copy it into the scratchpad `serve/` directory (see the `cp` in launch.json's script path) or the preview shows stale code. `.claude/serve.py` is the template for that script.

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
    "counters": [{ "id": "c_1", "count": 3, "note": "Sleeve", "rowMark": "start" }],
    "rows": [["c_1"], ["c_2", "c_3"]],
    "history": [{ "count": 3, "note": "Sleeve", "action": "removed", "ts": 0 }]
  }]
}
```

- Each project owns its `counters`, `rows`, and `history`. `cur()` returns the current project; all counter operations act on it.
- Two screens in one page: `#screen-project` (counters; header = editable project name input + "‹ Projects" back button, no subtitle/tagline — owner removed it, don't re-add) and `#screen-projects` (all projects + "+ Add project"). The in-memory `view` variable ("project" | "projects") picks which; it is **not persisted** — reload always lands on the current project's counters.
- `rows` is the layout: each row holds 1–2 counter ids. **Compact mode is derived, never stored**: if any row has 2 ids, `.list` gets the `compact` class and all cards render half-width (`isCompact()`).
- `nextId` and `nextProjectId` increment forever, never reused. Default project names are "Project N" from `nextProjectId`.
- `history` keeps the last 5 reset/removed counts per project (`HISTORY_MAX`). The list is tucked behind a clock icon (`#history-toggle`, inline SVG) at the top right under the header: hidden by default, toggled by the in-memory `historyOpen` flag (not persisted, reset when switching projects), and the icon itself only renders when the project has history (needs its `[hidden] { display: none }` guard since the button is `display: flex`).
- `loadState()` normalizes/validates everything and falls back to `seed()` on corrupt data. It migrates v1 data (top-level `counters`/`rows`/`history`) into a single project named "Project 1", and still handles the older legacy schema where counters had `half` flags instead of `rows`.

Event handling is **delegated**: single `click`/`input`/`focusout`/`dblclick`/`pointer*` listeners on `#list`, dispatched via `data-action` attributes and `data-id` on cards. Never attach listeners inside `buildCard()` — they'd be lost on re-render.

Drag-to-reorder (`pointerdown` on `.drag` handle) uses pointer events + `setPointerCapture`, a fixed-positioned card, and a placeholder element (`ph-row` for own-row drops, `ph-card` for pairing beside a lone card — pointer on the outer 35% of it). On drop, `endDrag()` derives the new `rows` from placeholder DOM position and calls `render()`. The handle has `touch-action: none`; counting buttons use `touch-action: manipulation`.

## Behavioral rules (owner decisions — keep these)

- Decrement clamps at 0; counter never goes negative.
- Reset (button or double-tap on the number) and remove show the confirm modal — **except** when count is 0: then they act silently and are NOT added to history.
- The app never drops below one counter: removing the last counter resets it (count 0, label cleared, rowMark "start") instead of deleting it.
- Projects follow the same pattern: deleting a project confirms ("…Its counters will be lost.") **except** when nothing was ever counted (all counts 0, empty history) — then it deletes silently. The app never drops below one project: deleting the last one resets it in place (name "Project 1", one fresh counter, empty history). Deleting the current project switches to the first remaining one.
- Project names are trimmed on blur; an empty name shows the "Untitled project" placeholder (and muted "Untitled project" text in the projects list).
- Labels are trimmed on blur; empty label shows the `…` placeholder.
- Width is never set manually: pairing happens by dragging a card beside another; when no pairs remain, all cards return to full width automatically.
- The label, count, and Reset button must all be horizontally centered on the card. The label is absolutely positioned with `left`/`right` insets — **keep them equal** (currently 118px full, 54px compact) or the label drifts off-center; the insets just need to clear the rowmark pill (wider than the × button). Verify centering by comparing `getBoundingClientRect()` centers, not by eye.
