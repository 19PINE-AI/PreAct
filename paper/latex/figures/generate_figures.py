#!/usr/bin/env python3
"""Generate all figures for the PreAct paper as PDF (+PNG preview).

Every number below is sourced from the manuscript's result tables
(paper/latex/preact.tex) so the figures and prose cannot drift. Run:

    python3 generate_figures.py

Outputs into the current directory (paper/latex/figures/).
Style is intentionally close to the author's other paper (User as Code):
clean serif type, a slate-blue accent, a muted-red "bad" colour, light grids.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# ---------------------------------------------------------------- palette ----
INK    = "#1A1A2E"   # near-black (matches body heading colour)
ACCENT = "#34507F"   # slate-blue: PreAct / "good" / gate-ON
ACC_LT = "#7E97C3"   # lighter accent
BAD    = "#B23A48"   # muted red: gate-OFF / regression
GRAY   = "#8A94A6"   # neutral baselines
GRID   = "#C2C8D6"   # light rule
GOLD   = "#C08A2D"   # secondary highlight

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.linewidth": 0.8,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})


def save(fig, name):
    fig.savefig(name + ".pdf")
    fig.savefig(name + ".png", dpi=150)
    plt.close(fig)
    print("wrote", name + ".pdf")


# ====================================================================== Fig 1
# The rerun crisis & PreAct's promise.
# Illustrative cumulative cost vs. number of repeated invocations of a
# familiar task. Annotated with the MEASURED warm-replay speedup band
# (8.5-13x on WebArena, preact.tex S4.3) and the one-time compile overhead
# (+162% Android / +217% OSWorld, preact.tex L3).
def fig_rerun_crisis():
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    N = np.arange(1, 11)
    c = 1.0                      # cost of one CUA solve (normalised)
    speedup = 10.0               # representative warm-replay speedup (8.5-13x band)
    compile_overhead = 1.8       # one-time verify+compile cost on top of run 1

    cua = c * N                                   # re-derives every time
    preact = np.empty_like(N, dtype=float)
    preact[0] = c + compile_overhead              # run 1: solve + compile+verify
    for i in range(1, len(N)):
        preact[i] = preact[i - 1] + c / speedup   # warm replays are cheap

    ax.plot(N, cua, "-o", color=BAD, lw=2.2, ms=5,
            label="CUA (re-derives every run)")
    ax.plot(N, preact, "-s", color=ACCENT, lw=2.2, ms=5,
            label="PreAct (compile once, then replay)")

    ax.annotate("one-time compile + verify\n(+162%/+217% over a solve)",
                xy=(1, preact[0]), xytext=(2.1, 6.2),
                fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
    ax.annotate("warm replays: 8.5–13× cheaper",
                xy=(7, preact[6]), xytext=(4.3, 2.0),
                fontsize=8.5, color=ACCENT,
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=0.8))

    ax.set_xlabel("Number of times the task is run")
    ax.set_ylabel("Cumulative LLM cost (relative)")
    ax.set_xlim(0.6, 10.4)
    ax.set_ylim(0, 10.5)
    ax.set_xticks(N)
    ax.grid(True, color=GRID, ls="--", lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "fig_rerun_crisis")


# ====================================================================== Fig 2
# Architecture: the verified compile-extend-replace loop (box-and-arrow).
def fig_architecture():
    fig, ax = plt.subplots(figsize=(7.6, 3.7))
    ax.set_xlim(0, 15); ax.set_ylim(0, 7.4); ax.axis("off")
    TOP, BOT, H = 3.9, 1.3, 1.0

    def box(x, y, w, text, fc="#EEF2F8", ec=ACCENT, fs=9.5):
        ax.add_patch(FancyBboxPatch((x, y), w, H,
                     boxstyle="round,pad=0.04,rounding_size=0.12",
                     fc=fc, ec=ec, lw=1.3))
        ax.text(x + w / 2, y + H / 2, text, ha="center", va="center",
                fontsize=fs, color=INK)

    def arrow(p, q, label="", color=INK, dashed=False, off=(0, 0.18),
              fs=8, ha="center"):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12,
                     color=color, lw=1.2,
                     linestyle="--" if dashed else "-", shrinkA=2, shrinkB=2))
        if label:
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            ax.text(mx + off[0], my + off[1], label, ha=ha, va="bottom",
                    fontsize=fs, color=color)

    box(0.2, TOP, 2.0, "User\ngoal  T")                                  # 0.2-2.2
    box(3.0, TOP, 2.2, "Program\nSelector")                              # 3.0-5.2
    box(6.2, TOP, 2.4, "State-machine\nReplayer")                        # 6.2-8.6
    box(6.2, BOT, 2.6, "CUA fallback\n(T3A / Claude-CU)")                # 6.2-8.8
    box(9.8, BOT, 2.0, "Compiler")                                       # 9.8-11.8
    box(9.6, TOP, 2.3, "Verify-before-\nStore Gate", ec=BAD)             # 9.6-11.9
    box(12.7, TOP, 2.1, "Program\nCorpus", fc="#FBF1DD", ec=GOLD)        # 12.7-14.8

    yc = TOP + H / 2  # 4.4
    arrow((2.2, yc), (3.0, yc))
    arrow((5.2, yc), (6.2, yc), "P", fs=8)
    arrow((4.1, TOP), (6.4, BOT + H), "no candidate", off=(-0.1, 0.0), fs=7.5)
    arrow((7.4, TOP), (7.4, BOT + H), "replay\nfail", color=BAD, fs=7.5,
          off=(0.62, -0.55))
    arrow((8.8, BOT + H/2), (9.8, BOT + H/2), "trace", fs=7.5)
    arrow((10.8, BOT + H), (10.8, TOP), "P'", off=(0.22, -0.55), fs=8)
    arrow((11.9, yc), (12.7, yc), "store/\nreplace", off=(0.0, 0.62), fs=7.5)
    # feedback: corpus -> selector, routed as a clean right-angle above the row
    ax.plot([13.75, 13.75], [TOP + H, 6.6], color=ACCENT, lw=1.2, ls="--")
    ax.plot([13.75, 4.6], [6.6, 6.6], color=ACCENT, lw=1.2, ls="--")
    ax.add_patch(FancyArrowPatch((4.6, 6.6), (4.1, 6.6), arrowstyle="-|>",
                 mutation_scale=12, color=ACCENT, lw=1.2, ls="--"))
    ax.plot([4.1, 4.1], [6.6, TOP + H], color=ACCENT, lw=1.2, ls="--")
    ax.add_patch(FancyArrowPatch((4.1, 5.1), (4.1, TOP + H), arrowstyle="-|>",
                 mutation_scale=12, color=ACCENT, lw=1.2, ls="--"))
    ax.text(9.0, 6.75, "retrieve on next invocation", ha="center",
            fontsize=8, color=ACCENT)

    ax.text(7.5, 0.35,
            "The corpus is the only growing structure; the harness code is fixed.",
            ha="center", fontsize=8.5, color=GRAY, style="italic")
    save(fig, "fig_architecture")


# ====================================================================== Fig 3
# Cold->warm monotonicity slopegraph (Android official-15, n=3 Gemini seeds).
# Source: preact.tex Table tab:monotonic.
def fig_monotonic():
    fig, ax = plt.subplots(figsize=(4.6, 3.9))
    seeds = {"seed 42": (10, 11), "seed 100": (9, 11), "seed 1337": (9, 10)}
    x = [0, 1]
    for i, (name, (cold, warm)) in enumerate(seeds.items()):
        ax.plot(x, [cold, warm], "-o", color=ACC_LT, lw=1.6, ms=6,
                zorder=2)
        ax.text(1.04, warm + (0.12 if name != "seed 1337" else -0.02),
                name, fontsize=8.5, color=INK, va="center")
    # mean line, emphasised
    ax.plot(x, [9.33, 10.67], "-o", color=ACCENT, lw=3.0, ms=8, zorder=3)
    ax.text(-0.04, 9.33, "mean 9.33", ha="right", va="center",
            fontsize=9, color=ACCENT, fontweight="bold")
    ax.text(1.16, 10.67 + 0.42, "mean 10.67\n(+1.33, all 3 ↑)", ha="left",
            va="center", fontsize=9, color=ACCENT, fontweight="bold")

    ax.set_xlim(-0.55, 1.95)
    ax.set_ylim(8.3, 12.0)
    ax.set_xticks(x)
    ax.set_xticklabels(["Cold\n(empty corpus)", "Warm\n(built corpus)"])
    ax.set_ylabel("Tasks solved (of 15)")
    ax.grid(True, axis="y", color=GRID, ls="--", lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "fig_monotonic")


# ====================================================================== Fig 4
# Cross-platform verify-gate ablation: cold->warm delta, gate ON vs OFF.
# Source: preact.tex Fig fig:diff-of-deltas / Tables tab:gate-*.
def fig_diff_of_deltas():
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    plats = ["Android\n(n=5, Gemini)", "OSWorld\n(n=5, Claude)",
             "WebArena\n(n=4+4, Claude)"]
    on   = [1.20, 0.20, -4.00]
    on_e = [0.45, 0.45, 2.94]
    off  = [-1.40, -2.40, -5.75]
    off_e = [0.89, 0.55, 1.71]
    diff = [2.6, 2.6, 1.75]
    xx = np.arange(len(plats)); w = 0.34

    ax.axhline(0, color=INK, lw=0.8)
    b1 = ax.bar(xx - w/2, on, w, yerr=on_e, capsize=4, color=ACCENT,
                label="Gate ON", error_kw=dict(ecolor=INK, lw=1.1))
    b2 = ax.bar(xx + w/2, off, w, yerr=off_e, capsize=4, color=BAD,
                label="Gate OFF", error_kw=dict(ecolor=INK, lw=1.1))

    for i in range(len(plats)):
        ax.text(xx[i]-w/2, on[i] + (0.18 if on[i] >= 0 else -0.5),
                f"{on[i]:+.1f}", ha="center", fontsize=8.5,
                va="bottom" if on[i] >= 0 else "top")
        ax.text(xx[i]+w/2, off[i]-0.5, f"{off[i]:+.1f}", ha="center",
                fontsize=8.5, va="top")
        ax.text(xx[i], 2.5, f"diff = {diff[i]}", ha="center", fontsize=8.5,
                color=GRAY)

    ax.set_xticks(xx); ax.set_xticklabels(plats)
    ax.set_ylabel("Cold→warm Δ (tasks)")
    ax.set_ylim(-8.6, 3.2)
    ax.grid(True, axis="y", color=GRID, ls="--", lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=2)
    save(fig, "fig_diff_of_deltas")


# ====================================================================== Fig 5
# Head-to-head on WebArena: warm-SR delta, baselines vs PreAct variants.
# Source: preact.tex Table tab:baselines.
def fig_baselines():
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    rows = [
        ("Workflow-Use",            -7.00, 0.82, GRAY),
        ("PreAct gate-OFF",         -5.75, 1.71, BAD),
        ("PreAct gate-ON",          -4.00, 2.94, ACC_LT),
        ("PreAct gate-ON\n+ fallback", -1.00, 1.83, ACCENT),
        ("Muscle-Mem",              -0.75, 1.50, GRAY),
    ]
    labels = [r[0] for r in rows]
    vals   = [r[1] for r in rows]
    errs   = [r[2] for r in rows]
    cols   = [r[3] for r in rows]
    yy = np.arange(len(rows))[::-1]

    ax.barh(yy, vals, xerr=errs, color=cols, capsize=4,
            error_kw=dict(ecolor=INK, lw=1.1))
    for y, v in zip(yy, vals):
        ax.text(v - 0.25, y, f"{v:+.2f}", va="center", ha="right",
                fontsize=8.5, color="white" if v < -1 else INK)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Warm − cold success-rate Δ (tasks, of 12)")
    ax.set_xlim(-9.2, 1.0)
    ax.grid(True, axis="x", color=GRID, ls="--", lw=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # bracket: the indistinguishable pair
    ax.annotate("", xy=(0.55, yy[3]), xytext=(0.55, yy[4]),
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=1.3))
    ax.text(0.72, (yy[3]+yy[4])/2, "indistinguishable\n(p≈0.84)",
            fontsize=8, color=ACCENT, va="center", rotation=0)
    save(fig, "fig_baselines")


# ====================================================================== Fig 6
# Selector operating curves: functional accuracy & false-pick vs threshold,
# for two embedding backbones, with the agentic selector as a reference.
# Source: preact.tex Table tab:selector-ablation.
def fig_selector():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.2, 3.5))

    mini_tau  = [0.40, 0.50, 0.65, 0.70, 0.85]
    mini_func = [100, 100, 100, 86.7, 64.4]
    mini_fp   = [6.7, 0, 0, 0, 0]
    bge_tau   = [0.50, 0.60, 0.65, 0.85]
    bge_func  = [100, 100, 100, 100]
    bge_fp    = [93.3, 20, 0, 0]

    # Left: functional accuracy
    axL.plot(mini_tau, mini_func, "-o", color=ACCENT, lw=2, ms=5,
             label="MiniLM-L6")
    axL.plot(bge_tau, bge_func, "-s", color=GOLD, lw=2, ms=5,
             label="bge-large")
    axL.axhline(75.6, color=GRAY, ls="--", lw=1.6)
    axL.text(0.41, 77.5, "agentic LLM (75.6%)", fontsize=8, color=GRAY)
    axL.set_xlabel("Threshold τ"); axL.set_ylabel("Functional accuracy (%)")
    axL.set_ylim(55, 105); axL.set_title("Correct-family retrieval", fontsize=10)
    axL.legend(frameon=False, fontsize=8.5, loc="lower left")

    # Right: false-pick on unrelated queries
    axR.plot(mini_tau, mini_fp, "-o", color=ACCENT, lw=2, ms=5,
             label="MiniLM-L6")
    axR.plot(bge_tau, bge_fp, "-s", color=GOLD, lw=2, ms=5, label="bge-large")
    axR.axhline(0, color=GRAY, ls="--", lw=1.6)
    axR.text(0.62, 4, "agentic LLM (0%)", fontsize=8, color=GRAY)
    axR.set_xlabel("Threshold τ"); axR.set_ylabel("False-pick rate (%)")
    axR.set_ylim(-4, 100); axR.set_title("Mis-routing unrelated queries",
                                         fontsize=10)
    axR.legend(frameon=False, fontsize=8.5, loc="upper right")

    for ax in (axL, axR):
        ax.grid(True, color=GRID, ls="--", lw=0.6, alpha=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    save(fig, "fig_selector")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    fig_rerun_crisis()
    fig_architecture()
    fig_monotonic()
    fig_diff_of_deltas()
    fig_baselines()
    fig_selector()
    print("all figures generated")
