# PreAct — Interactive Paper Site

The companion website for **PreAct: Computer-Using Agents that Get Faster on
Repeated Tasks**. It is a single-page React app that explains the idea, lets you
walk a real compiled program through the verify-gate, browse the full corpus of
saved programs, replay real agent runs screenshot-by-screenshot, and read every
headline result as a live, rebuilt-from-data figure.

Live site: <https://01.me/research/PreAct/>
Source & reproduction: <https://github.com/19PINE-AI/PreAct>

---

## Quick start

```bash
cd site
npm install
npm run dev        # dev server → http://localhost:5174
npm run build      # static production bundle → dist/
npm run preview    # serve the built dist/ locally
```

Requires Node 18+ and npm. There is no backend — the app is fully static and all
data is bundled at build time.

---

## What's on the page

The app is one scrolling page (`src/App.jsx`). Each content section lives in its
own folder under `src/sections/`; the fixed nav and footer live under
`src/layout/`. The table below lists every section in scroll order, the DOM `id`
it scrolls to, the label shown in the nav, and what it renders.

| Section | DOM id | Nav label | What it shows |
|---|---|---|---|
| **Hero** | `#top` | *(brand)* | The thesis — *the artifact is the runtime* — with an animated state-machine loop and the four headline stats. |
| **Problem** | `#problem` | Problem | The rerun crisis (solving the same task N times is O(M×N); replaying a saved program is O(M)) and where PreAct sits versus related work. |
| **Architecture** | `#architecture` | How it works | Interactive harness diagram — click any of the six components (picker, runner, full agent, compiler, main loop, check). Includes the code-module map and a real worked program. |
| **Demo** | `#demo` | Try it | Walk the real `add a contact` program (corpus id `ab4390a9`) through the verify-gate. Pick *faithful / lossy / replay-fail* and watch the gate decide **SAVE** vs **REJECT** vs **HAND OFF**, replayed on a live phone frame. |
| **Corpus** | `#corpus` | Programs | Browse all **55** real compiled programs. Filter by platform, search by task, expand for the state machine — verification predicates and actions shown verbatim. |
| **Trajectories** | `#trajectories` | Real runs | Replay **12** real AndroidWorld agent runs, one screenshot per step, with the action taken at each step. |
| **Results** | `#results` | Results | The cross-platform verify-gate diff-of-deltas chart, per-seed tables, cold→warm monotonicity, head-to-head baselines, the cov=100%/score=0 smoking guns, the selector ablation, negative findings, cross-model parity, and the validity-threat grid. |
| **Footer** | `#cite` | Paper ↗ | Reproduction commands, the repository and paper links, and the BibTeX citation. |

---

## Project structure

```
site/
├── index.html              # document shell: <title>, meta, fonts, #root mount
├── vite.config.js          # Vite + React; base './', dev server on :5174
├── package.json
├── public/
│   └── traj/               # per-step trajectory screenshots (served verbatim)
└── src/
    ├── main.jsx            # React root; imports global.css
    ├── App.jsx             # section composition (the whole page)
    ├── layout/             # page chrome
    │   ├── Nav/            #   Nav.jsx + Nav.css (scroll-spy nav)
    │   └── Footer/         #   Footer.jsx + Footer.css (cite + repro)
    ├── sections/           # one folder per content section: <Section>.jsx + .css
    │   ├── Hero/           #   Hero + HeroGraph (section-local animation)
    │   ├── Problem/
    │   ├── Architecture/
    │   ├── Demo/
    │   ├── Corpus/
    │   ├── Trajectories/
    │   └── Results/        #   Results + GateChart (section-local chart)
    ├── components/         # shared, reused across sections
    │   ├── Reveal.jsx      #   scroll-into-view animation wrapper
    │   └── PhoneFrame.*    #   phone bezel used by Demo and Trajectories
    ├── data/               # all content — see "Data layer" below
    └── styles/
        └── global.css      # design tokens + base styles
```

**Where things go.** A component used by exactly one section lives inside that
section's folder (`Hero/HeroGraph.jsx`, `Results/GateChart.jsx`). A component
shared by two or more sections lives in `components/` (`Reveal`, `PhoneFrame`).
Each section keeps its CSS beside its JSX.

---

## Data layer

No figures are image-copied; every chart is rebuilt as live SVG from the data in
`src/data/`. All numbers are transcribed from the paper and the raw run logs —
the data files are the single source of truth for the page.

| File | Contents |
|---|---|
| `data/results.js` | Headline stats, the verify-gate ablation tables, monotonicity, baselines, selector ablation, negative findings, cross-model parity, threat grid. |
| `data/architecture.js` | The six harness components, the code-module map, the env-var ablation knobs, and the worked example program. |
| `data/benchmarks.js` | Per-benchmark metadata for the 33 tasks (AndroidWorld 15, OSWorld 6, WebArena 12). |
| `data/corpus.js` | The 55 real compiled programs (states + verification predicates + actions), from `rag_db_warm_baseline_20260425`. |
| `data/trajectories.js` | The 12 replayed agent runs — per-step screenshot paths and actions. |

### Provenance

Numbers and program contents trace back to, in the repository root:

- `paper/latex/preact.tex` and `paper/findings_summary.md` — the paper and its results summary.
- `benchmark/{androidworld,osworld,webarena}/results/` — raw per-run results JSON.
- the saved RAG databases (`rag_db_*/`) and run logs (`*.log`).

To refresh a figure, edit the relevant `data/*.js` file — the charts re-render
from it; nothing is hard-coded in the components.

---

## Tech stack

- **Vite 5 + React 18** — single-page app, static build.
- **Framer Motion** — orchestrated scroll reveals and animated SVG charts.
- **Fonts:** [Inter](https://fonts.google.com/specimen/Inter) (display + body) and
  [JetBrains Mono](https://fonts.google.com/specimen/JetBrains+Mono) (code/mono),
  loaded from Google Fonts in `index.html`.
- **"Schematic Dossier" design system** (`src/styles/global.css`) — a dark
  instrumentation panel where colour encodes the paper's findings:

  | Token | Colour | Meaning |
  |---|---|---|
  | `--pass` | lime `#b6f24a` | verified / store / gate-ON |
  | `--fail` | coral `#ff6b6b` | lossy / score=0 / gate-OFF |
  | `--replay` | cyan `#4fd6e6` | program replay / hybrid / select |
  | `--amber` | amber `#ffb454` | full agent / fallback / re-derive |

---

## Deployment

The build output in `dist/` is a self-contained static bundle (`base: './'`, so
it works under any sub-path). Deploy it by copying `dist/` to any static host:

```bash
npm run build
# then publish the dist/ directory (e.g. the path behind 01.me/research/PreAct/)
```

`dist/` and `node_modules/` are git-ignored; rebuild from source on each deploy.

---

## License & citation

See the main repository, <https://github.com/19PINE-AI/PreAct>, for license and
reproduction instructions. To cite the work:

```bibtex
@article{preact2026,
  title  = {PreAct: Computer-Using Agents that Get Faster on Repeated Tasks},
  author = {Bojie Li},
  year   = {2026},
  note   = {Pine AI},
}
```
