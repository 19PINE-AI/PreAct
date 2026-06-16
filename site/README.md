# PreAct — Interactive Paper Site

A React single-page site for **PreAct: A Verified Self-Extending Executable Code
Corpus for Computer-Using Agents**. It presents the framing and implementation,
lets you browse every benchmark test case, and renders the major results as live,
interactive figures.

## Run it

```bash
cd site
npm install
npm run dev        # http://localhost:5174
npm run build      # static bundle in dist/
npm run preview    # serve the built bundle
```

## What's inside

| Section | What it does |
|---|---|
| **Hero** | Animated state-machine loop; the thesis — *the artifact is the runtime*. |
| **Problem** | The rerun crisis (O(M×N) → O(M)) and where PreAct sits vs related work. |
| **Architecture** | Interactive harness diagram — click any of the six components; Algorithm 1. |
| **Live Demo** | Walk the real `ContactsNewContactDraft` program through the verify-gate. Pick *faithful / lossy / replay-fail* and watch the gate decide STORE vs REJECT vs FALLBACK. |
| **Implementation** | Code-corpus map (~6.6k LOC), the RPAProgram JSON, action schema, and the env-var ablation knobs. |
| **Test Cases** | Browse all 33 tasks across AndroidWorld (15), OSWorld (6), WebArena (12). Search, filter by outcome, expand for goal / evaluator / per-seed results. |
| **Results** | The cross-platform verify-gate diff-of-deltas chart, per-seed tables, cold→warm monotonicity, head-to-head baselines, the cov=100%/score=0 smoking guns, selector ablation, negative findings, and the 11/11 validity-threat grid. |

## Data provenance

All numbers are transcribed from the paper (`../paper/latex/preact.tex`),
`../paper/findings_summary.md`, and the raw results JSON under
`../benchmark/{androidworld,osworld,webarena}/results/`. The data layer lives in
`src/data/` (`benchmarks.js`, `results.js`, `architecture.js`) — no figures are
image-copied; every chart is rebuilt as live SVG.

## Stack

Vite + React 18, Framer Motion for orchestrated reveals and animated SVG charts.
Custom "Schematic Dossier" design system — Syne / IBM Plex Sans / IBM Plex Mono,
with a semantic palette where colour encodes the paper's findings (lime = verified,
coral = lossy, cyan = replay).
