# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A row counter web app for knitters. The entire app is one self-contained file, `index.html` (inline CSS + vanilla JS, no framework, no build step, no dependencies). Hard constraints from the owner:

- **Fully offline**: no CDN, no external fonts/scripts, must work when opened via `file://` double-click. Don't add `type="module"` scripts, `fetch()`, or any network dependency.
- **Minimal look**: warm-neutral palette via CSS variables in `:root`, system font stack, quiet secondary controls. New controls should match the existing muted style (see `.reset`, `.rowmark`).
- All state persists in `localStorage`; the app must never lose counts across reloads.

## Commands

There is no build, lint, or test tooling. To develop: edit `index.html`, reload the browser.

Preview server (for the `preview_*` MCP tools): `.claude/launch.json` runs `python3` on a `serve.py` copied into the session scratchpad, serving on port 8742. macOS TCC blocks the sandboxed python from reading this Documents folder directly, so the server serves a **copy** — after editing `index.html`, re-copy it into the scratchpad `serve/` directory (see the `cp` in launch.json's script path) or the preview shows stale code. `.claude/serve.py` is the template for that script.

## Architecture

Single IIFE in the `<script>` block. One in-memory `state` object is the source of truth; every mutation calls `saveState()` (JSON → localStorage key `stitchCounter.v1`) then `render()` (full DOM rebuild of the counter list). Exception: `updateNote()` saves without re-rendering, so typing in a label doesn't lose input focus — preserve this if touching label logic.

State shape:

```json
{
  "version": 1,
  "nextId": 4,
  "counters": [{ "id": "c_1", "count": 3, "note": "Sleeve", "rowMark": "start" }],
  "rows": [["c_1"], ["c_2", "c_3"]],
  "history": [{ "count": 3, "note": "Sleeve", "action": "removed", "ts": 0 }]
}
```

- `rows` is the layout: each row holds 1–2 counter ids. **Compact mode is derived, never stored**: if any row has 2 ids, `.list` gets the `compact` class and all cards render half-width (`isCompact()`).
- `nextId` increments forever, never reused.
- `history` keeps the last 5 reset/removed counts (`HISTORY_MAX`).
- `loadState()` normalizes/validates everything and falls back to `seed()` on corrupt data; it also migrates a legacy schema where counters had `half` flags instead of `rows`.

Event handling is **delegated**: single `click`/`input`/`focusout`/`dblclick`/`pointer*` listeners on `#list`, dispatched via `data-action` attributes and `data-id` on cards. Never attach listeners inside `buildCard()` — they'd be lost on re-render.

Drag-to-reorder (`pointerdown` on `.drag` handle) uses pointer events + `setPointerCapture`, a fixed-positioned card, and a placeholder element (`ph-row` for own-row drops, `ph-card` for pairing beside a lone card — pointer on the outer 35% of it). On drop, `endDrag()` derives the new `rows` from placeholder DOM position and calls `render()`. The handle has `touch-action: none`; counting buttons use `touch-action: manipulation`.

## Behavioral rules (owner decisions — keep these)

- Decrement clamps at 0; counter never goes negative.
- Reset (button or double-tap on the number) and remove show the confirm modal — **except** when count is 0: then they act silently and are NOT added to history.
- The app never drops below one counter: removing the last counter resets it (count 0, label cleared, rowMark "start") instead of deleting it.
- Labels are trimmed on blur; empty label shows the `…` placeholder.
- Width is never set manually: pairing happens by dragging a card beside another; when no pairs remain, all cards return to full width automatically.
- The label, count, and Reset button must all be horizontally centered on the card. The label is absolutely positioned with `left`/`right` insets — **keep them equal** (currently 118px full, 54px compact) or the label drifts off-center; the insets just need to clear the rowmark pill (wider than the × button). Verify centering by comparing `getBoundingClientRect()` centers, not by eye.
