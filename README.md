# PreAct: Computer-Using Agents that Get Faster on Repeated Tasks

[![arXiv](https://img.shields.io/badge/arXiv-2606.17929-b31b1b.svg)](https://arxiv.org/abs/2606.17929)
[![Website](https://img.shields.io/badge/website-01.me%2Fresearch%2FPreAct-1f6feb.svg)](https://01.me/research/PreAct/)

**Paper:** [arxiv.org/abs/2606.17929](https://arxiv.org/abs/2606.17929) · **Website:** [01.me/research/PreAct](https://01.me/research/PreAct/) · **Author:** Bojie Li (Pine AI)

## What this is

Computer-using agents drive real software through the screen — clicking and typing — but they
solve every task from scratch: asked to repeat a task, an agent re-reads the screen, re-reasons
every tap, and pays the full cost again.

**PreAct** lets such an agent get faster on tasks it has done before. The first time it succeeds,
PreAct compiles the run into a small **state-machine program** — states that check the screen,
transitions that act — and on later runs **replays it directly** instead of invoking the agent:
**8.5–13× faster, with no per-step language-model calls.**

Two checks make this safe:

- **Replay-time check.** At each step PreAct verifies that the screen matches what the program
  expects *before* acting, and hands control back to the agent the moment something is off.
- **Store-time check (verify-before-store).** A freshly compiled program enters the library only
  if, re-run from a clean state, an independent evaluator confirms it actually solved the task —
  catching programs that replay to their last step yet leave the task undone.

Across a mobile (AndroidWorld), a desktop (OSWorld), and a web (WebArena) benchmark, the
store-time check is what separates repeated runs that **improve** from ones that **degrade** as
faulty programs accumulate — worth 1.75–2.6 tasks per benchmark, the same direction on all three.
A fallback that explores afresh when no program fits brings PreAct level with a strong
record-and-replay baseline. The paper also reports what did *not* matter: prompt wording, runtime
guardrails, and whether a language model or a plain embedding retriever selects which program to
reuse.

## Repository layout

| Path | Contents |
|---|---|
| `preact/` | The PreAct library: compiler, executor, RAG program store, LLM clients, per-platform agents |
| `benchmark/androidworld/` | AndroidWorld runner (`run_docker.py`) |
| `benchmark/osworld/` | OSWorld runner (`run_osworld.py`) |
| `benchmark/webarena/` | WebArena runner (`run_webarena.py`) + environment setup helpers |
| `paper/` | arXiv preprint source (`latex/preact.tex`) and findings tables |
| `site/` | Project website (React + Vite) — source for [01.me/research/PreAct](https://01.me/research/PreAct/) |
| `RESULTS.md`, `EVALUATION_REPORT.md` | Full empirical results and per-experiment write-ups |

## Setup

PreAct itself is a Python package; the three benchmarks each wrap an upstream environment that you
install separately.

```bash
# Python 3.11+
pip install -e .
```

Set the API keys for the models you intend to use:

| Variable | Needed for |
|---|---|
| `ANTHROPIC_API_KEY` | Compilation + program selection (always), and the Claude computer-use agent on OSWorld / WebArena and optionally AndroidWorld |
| `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | The Gemini 3 Flash agent used by default for AndroidWorld steps |

**Benchmark environments** (each is the upstream project; follow its own install guide):

- **AndroidWorld** — a Docker image exposing the HTTP control server on port 5000:
  `sudo docker run --privileged -p 5000:5000 -it android_world:latest`
- **OSWorld** — a local `~/OSWorld` checkout providing `evaluation_examples/<task-set>.json` and a
  VM/Docker backend.
- **WebArena** — the `shopping_admin` Docker environment; helpers live in
  `benchmark/webarena/setup.py`.

## Reproducing the experiments

The central result is the **verify-before-store** ablation, run as a cold→warm pair (empty library
→ reused library) with the gate **on** vs **off**. The gate is controlled per platform as noted
below; all numbers in the paper come from these runners.

**AndroidWorld** — gate is the `--verify-before-store` / `--no-verify-before-store` flag (default
on). The 15 task types of the `official-15` subset:

```bash
TASKS="ContactsAddContact ContactsNewContactDraft AudioRecorderRecordAudio \
AudioRecorderRecordAudioWithFileName BrowserDraw BrowserMaze CameraTakePhoto \
CameraTakeVideo ClockStopWatchPausedVerify ClockStopWatchRunning FilesDeleteFile \
MarkorCreateFolder MarkorCreateNote SystemBrightnessMax SystemWifiTurnOn"

# gate ON (default) — the agent uses Gemini 3 Flash for steps by default
python -m benchmark.androidworld.run_docker --tasks $TASKS --n-instances 1 --seed 42

# gate OFF (ablation)
python -m benchmark.androidworld.run_docker --tasks $TASKS --n-instances 1 --seed 42 \
  --no-verify-before-store
```

**OSWorld** — gate is the same flag (default on); task set is read from
`~/OSWorld/evaluation_examples/<task-set>.json`:

```bash
python -m benchmark.osworld.run_osworld --task-set test_tiny                          # gate ON
python -m benchmark.osworld.run_osworld --task-set test_tiny --no-verify-before-store # gate OFF
```

**WebArena** — gate is the `PREACT_VERIFY_BEFORE_STORE` environment variable (`on` default / `off`):

```bash
PREACT_VERIFY_BEFORE_STORE=on  python -m benchmark.webarena.run_webarena   # gate ON
PREACT_VERIFY_BEFORE_STORE=off python -m benchmark.webarena.run_webarena   # gate OFF
```

### Other ablations (environment variables)

Each remaining experiment in the paper is selected by one environment variable:

| Variable | Default | Values | Controls |
|---|---|---|---|
| `PREACT_VERIFY_BEFORE_STORE` | `on` | `on` / `off` | Store-time verify gate (WebArena; Android/OSWorld use the CLI flag above) |
| `PREACT_CACHE_MISS_FALLBACK` | `skip` | `skip` / `cua` | On a cache miss, skip the repeat run or explore afresh with the full agent (WebArena) |
| `PREACT_SELECTOR_MODE` | `agentic` | `agentic` / `embedding` | Pick the reuse candidate with an LLM tool call or a plain embedding retriever |
| `PREACT_RUNTIME_MODE` | `state_machine` | `state_machine` / `flat_script` | Replay as a verified state machine or a flat action script |
| `PREACT_GUARDRAILS` | `on` | `on` / `off` | Runtime code-level guardrails (AndroidWorld) |
| `PREACT_CUA_PROVIDER` | `gemini` | `gemini` / `anthropic` | Backend for AndroidWorld agent steps |
| `PREACT_COMPILE_PROVIDER` | _(Claude)_ | `gemini` | Swap the compile-step LLM to Gemini for the cross-provider check |
| `PREACT_MODEL` | `claude-sonnet-4-6` | model id | Model used for compilation and program selection |

See `RESULTS.md` for the per-experiment result tables and the exact runs behind each paper figure.

## Citation

```bibtex
@article{li2026preact,
  title   = {{PreAct}: Computer-Using Agents that Get Faster on Repeated Tasks},
  author  = {Li, Bojie},
  journal = {arXiv preprint arXiv:2606.17929},
  year    = {2026},
}
```
