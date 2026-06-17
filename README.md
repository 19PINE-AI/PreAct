# PreAct: Computer-Using Agents that Get Faster on Repeated Tasks

[![arXiv](https://img.shields.io/badge/arXiv-2606.17929-b31b1b.svg)](https://arxiv.org/abs/2606.17929)
[![Website](https://img.shields.io/badge/website-01.me%2Fresearch%2FPreAct-1f6feb.svg)](https://01.me/research/PreAct/)

**Paper:** [arxiv.org/abs/2606.17929](https://arxiv.org/abs/2606.17929) · **Website:** [01.me/research/PreAct](https://01.me/research/PreAct/) · **Author:** Bojie Li (Pine AI)

Computer-using agents drive real software through the screen — clicking and typing — but they
solve every task from scratch: asked to repeat a task, an agent re-reads the screen, re-reasons
every tap, and pays the full cost again. **PreAct** lets such an agent get faster on tasks it has
done before. The first time it succeeds, PreAct compiles the run into a small state-machine
program — states that check the screen, transitions that act — and on later runs replays it
directly instead of invoking the agent: **8.5–13× faster, with no per-step language-model calls.**

Replay is not blind: at each step PreAct checks that the screen matches what the program expects
before acting, and hands control back to the agent the moment something is off. PreAct applies the
same discipline when deciding what to keep — a freshly compiled program enters the store only if,
re-run from a clean state, an independent evaluator confirms it solved the task. Across a mobile,
a desktop, and a web benchmark, this store-time check separates repeated runs that **improve** from
ones that **degrade** as faulty programs accumulate — worth 1.75–2.6 tasks per benchmark.

## Repository layout

| Path | Contents |
|---|---|
| `paper/` | arXiv preprint source (`latex/preact.tex`), figures, and findings tables |
| `site/` | Project website (React + Vite) — source for [01.me/research/PreAct](https://01.me/research/PreAct/) |
| `benchmark/` | Benchmark harnesses (AndroidWorld, OSWorld, WebArena) |
| `run_evaluation.py`, `run_ablation.py` | Top-level evaluation and ablation entry points |
| `RESULTS.md`, `EVALUATION_REPORT.md` | Empirical results and per-experiment write-ups |

## Reproducing experiments

Each ablation in the paper is selected by flipping a single environment variable. For example, the
cross-platform verify-gate ablation on AndroidWorld:

```bash
# cold → warm, verify-gate on
PREACT_VERIFY_GATE=on python -m benchmark.androidworld.run_docker --tasks official-15 --seed 42
```

## Citation

```bibtex
@article{li2026preact,
  title   = {{PreAct}: Computer-Using Agents that Get Faster on Repeated Tasks},
  author  = {Li, Bojie},
  journal = {arXiv preprint arXiv:2606.17929},
  year    = {2026},
}
```
