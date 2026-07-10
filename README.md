# KnitCount

A minimal, offline row counter for knitters. No sign-up, no ads, no tracking — just counters that remember themselves.

**Live app:** [xlixli2026.github.io/knitting-counter](https://xlixli2026.github.io/knitting-counter/)

## Features

- **Multiple projects**, each with its own counters, layout, and history
- **Tap to count**, double-tap (or the Reset button) to reset — with a confirm step so you can't lose a count by accident
- **Pair counters side by side** by dragging one next to another (e.g. left sock / right sock, front / back)
- **Row markers and labels** on each counter so you can tell your stitch counter from your row counter at a glance
- **History** of your last few resets, in case you reset the wrong one
- **Works fully offline** — installable as a home-screen app (PWA), and everything keeps working with no network at all
- **Nothing leaves your device** — all data lives in your browser's local storage, there is no backend or account

## Using it

Just open the live link above, or, for a fully local copy:

1. Download or clone this repo
2. Open `index.html` directly in a browser (double-click it — no server, no build step, no install)

That's it. `index.html` is the entire app: a single self-contained file with no external dependencies. The other files (`manifest.webmanifest`, `sw.js`, the icon PNGs) are optional extras that enable offline caching and "Add to Home Screen" support when the app is hosted; `index.html` works standalone without them.

## Development

There's no build, bundler, or package manager — it's plain HTML/CSS/JS in one file. To make changes, edit `index.html` and reload it in a browser.

See [CLAUDE.md](CLAUDE.md) for a detailed architecture and behavior reference if you're working on the code.
