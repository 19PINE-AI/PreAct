#!/usr/bin/env python3
"""Generate all figures for the PreAct paper as PDF (+PNG preview).

Every quantitative figure is sourced from the manuscript's result tables
(paper/latex/preact.tex); schematic figures (architecture, program graph,
gate-decision flow, day-1/day-2 timeline, related-work landscape) encode the
paper's described structure. Run:

    python3 generate_figures.py

Shared "report" aesthetic: serif type, a slate-blue accent, a muted red for
the "bad"/gate-off condition, soft tinted panels, value labels, light grids.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from matplotlib.lines import Line2D
import numpy as np

# ------------------------------------------------------------- palette ------
INK    = "#1A1A2E"
ACCENT = "#34507F"   # slate-blue: PreAct / good / gate-ON
ACC2   = "#5B7DB1"
ACC_LT = "#9FB3D4"
TEAL   = "#2F7E7E"
GOLD   = "#C0892D"
GREEN  = "#3C7A57"   # pass / store
BAD    = "#B23A48"   # gate-OFF / regression / reject
GRAY   = "#8A94A6"
GRID   = "#D5DCE8"
PANEL  = "#F6F8FC"
INKBOX = "#EEF2F8"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.edgecolor": "#B9C2D2",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.linewidth": 0.9,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.04,
})


def save(fig, name):
    fig.savefig(name + ".pdf")
    fig.savefig(name + ".png", dpi=150)
    plt.close(fig)
    print("wrote", name + ".pdf")


def panel(ax, axis="y", title=None):
    """Apply the shared card aesthetic to an Axes."""
    ax.set_facecolor(PANEL)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if axis in ("y", "both"):
        ax.grid(True, axis="y", color=GRID, ls="-", lw=0.7, alpha=0.9)
    if axis in ("x", "both"):
        ax.grid(True, axis="x", color=GRID, ls="-", lw=0.7, alpha=0.9)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=ACCENT, fontweight="bold", loc="left",
                     fontsize=11, pad=8)


def rbox(ax, x, y, w, h, text, fc=INKBOX, ec=ACCENT, fs=9.5, lw=1.3, tc=INK,
         bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.10",
                 fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal")


def arrow(ax, p, q, color=INK, dashed=False, lw=1.3):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12,
                 color=color, lw=lw, linestyle="--" if dashed else "-",
                 shrinkA=2, shrinkB=2))


# ====================================================================== Fig 1
def fig_rerun_crisis():
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    N = np.arange(1, 11)
    c, speedup, comp = 1.0, 10.0, 1.8
    cua = c * N
    preact = np.empty(len(N))
    preact[0] = c + comp
    for i in range(1, len(N)):
        preact[i] = preact[i - 1] + c / speedup
    panel(ax, "y")
    ax.fill_between(N, preact, cua, color=ACC_LT, alpha=0.25, zorder=1)
    ax.plot(N, cua, "-o", color=BAD, lw=2.4, ms=5, zorder=3,
            label="CUA — re-derives every run")
    ax.plot(N, preact, "-s", color=ACCENT, lw=2.4, ms=5, zorder=3,
            label="PreAct — compile once, then replay")
    ax.annotate("one-time compile + verify\n(+162% / +217% of a solve)",
                xy=(1, preact[0]), xytext=(2.0, 6.4), fontsize=8.5,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9))
    ax.annotate("warm replays: no LLM calls\n(8.5–13× faster wall-clock)",
                xy=(7, preact[6]), xytext=(4.2, 1.7), fontsize=8.5,
                color=ACCENT,
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=0.9))
    ax.text(9.6, cua[-1] - 0.2, "savings\ngrow", color=BAD, fontsize=8,
            ha="center", va="top", style="italic")
    ax.set_xlabel("Number of times the task is run")
    ax.set_ylabel("Cumulative LLM cost (relative)")
    ax.set_xlim(0.6, 10.4); ax.set_ylim(0, 10.5); ax.set_xticks(N)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "fig_rerun_crisis")


# ====================================================================== Fig 2
def fig_landscape():
    """Qualitative positioning. Axes are the two properties PreAct combines:
    (x) self-extension/refinement of the store, (y) the stored artifact runs
    WITHOUT an LLM in the loop. Skill/memory systems self-extend but are
    LLM-bound at run time; record-replay runs LLM-free but only appends."""
    fig, ax = plt.subplots(figsize=(6.8, 4.3))
    ax.set_facecolor(PANEL)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axhline(5, color=GRID, lw=1.0); ax.axvline(5, color=GRID, lw=1.0)
    ax.text(9.85, 0.18, "self-extends / refines its store $\\rightarrow$",
            ha="right", fontsize=11.5, color=INK, fontweight="bold")
    ax.text(0.18, 9.85, "artifact runs without an LLM $\\rightarrow$",
            ha="left", va="top", fontsize=11.5, color=INK, fontweight="bold",
            rotation=90)
    # shaded top-right region (PreAct's combination)
    ax.add_patch(Rectangle((5, 5), 5, 5, color=ACCENT, alpha=0.06, zorder=0))
    #            name                 x    y   ldx   ldy  ha       color
    pts = [
        ("RPA scripts",         1.3, 9.0, 0.0, -0.55, "center", GRAY),
        ("Muscle-Mem",          3.3, 8.3, 0.0, -0.55, "center", GRAY),
        ("Workflow-Use",        1.5, 6.9, 0.0, -0.55, "center", GRAY),
        ("ActionEngine",        2.9, 5.9, 0.0, -0.55, "center", GRAY),
        ("AgentRR",             3.7, 4.4, 0.0, -0.55, "center", GRAY),
        ("memory systems\n(Mem0, A-MEM)", 5.6, 4.0, 0.0, -0.5, "center", GRAY),
        ("Voyager",             8.8, 3.4, 0.0, -0.55, "center", GRAY),
        ("TroVE",               7.1, 2.3, 0.0, -0.55, "center", GRAY),
        ("ExpeL",               8.7, 2.0, 0.0, -0.55, "center", GRAY),
        ("PreAct",              8.5, 8.5, 0.0, -0.7,  "center", ACCENT),
    ]
    for name, x, y, ldx, ldy, lha, col in pts:
        star = (name == "PreAct")
        ax.scatter([x], [y], s=360 if star else 130, color=col, zorder=3,
                   edgecolor="white", lw=1.4, marker="*" if star else "o")
        ax.text(x + ldx, y + ldy, name, ha=lha, va="top",
                fontsize=10 if star else 8.6,
                fontweight="bold" if star else "normal",
                color=ACCENT if star else INK)
    ax.text(7.5, 5.2, "directly executable\n+ self-extending", ha="center",
            fontsize=8, color=ACCENT, style="italic")
    for s in ax.spines.values():
        s.set_color("#B9C2D2")
    ax.set_xticks([]); ax.set_yticks([])
    save(fig, "fig_landscape")


# ====================================================================== Fig 3
def fig_program_graph():
    """The real compiled 'add a contact' program (program ab4390a9) as a
    compact two-row (snake) state machine: 4 states top L->R, 3 bottom R->L.
    Box = state id (wrapped); action on each arrow; predicates are in Listing 1.
    Wide-and-short so it includes near full width with a legible font."""
    ids = ["contacts\n_app_open", "create\n_contact_form", "first_name\n_entered",
           "last_name\n_entered", "phone\n_entered", "phone_type\n_selected",
           "contact\n_saved"]
    acts = ["tap '+'", "type first_name", "type last_name",
            "type phone_number", "tap 'Mobile'", "tap 'Save'"]
    BW, BH = 3.7, 1.15
    PX = 4.4                       # column pitch
    x0 = 0.3
    yA, yB = 2.9, 0.7              # top-row / bottom-row box bottoms

    def rc(i):
        return (0, i) if i < 4 else (1, 3 - (i - 4))
    def bx(i):
        return x0 + rc(i)[1] * PX
    def by(i):
        return yA if rc(i)[0] == 0 else yB

    W = x0 + 3 * PX + BW + 0.3
    fig, ax = plt.subplots(figsize=(7.6, 7.6 * (5.0 / W)))
    ax.set_xlim(0, W); ax.set_ylim(0, 5.0); ax.set_aspect("equal")
    ax.axis("off")

    for i, lab in enumerate(ids):
        x, y = bx(i), by(i); term = (i == len(ids) - 1)
        ax.add_patch(FancyBboxPatch((x, y), BW, BH,
                     boxstyle="round,pad=0.02,rounding_size=0.10",
                     fc="#FBF1DD" if term else INKBOX,
                     ec=GOLD if term else ACCENT, lw=1.4))
        ax.text(x + BW / 2, y + BH / 2, lab, ha="center", va="center",
                fontsize=10, fontweight="bold", color=GOLD if term else ACCENT)

    for i, act in enumerate(acts):
        (rf, cf), (rt, ct) = rc(i), rc(i + 1)
        ymf = by(i) + BH / 2
        if rf == rt and cf < ct:                       # rightward (top row)
            arrow(ax, (bx(i) + BW, ymf), (bx(i + 1), ymf), color=ACCENT, lw=1.8)
            ax.text((bx(i) + BW + bx(i + 1)) / 2, by(i) + BH + 0.28, act,
                    ha="center", va="bottom", fontsize=9.5, color=ACCENT)
        elif rf == rt and cf > ct:                     # leftward (bottom row)
            arrow(ax, (bx(i), ymf), (bx(i + 1) + BW, ymf), color=ACCENT, lw=1.8)
            ax.text((bx(i) + bx(i + 1) + BW) / 2, by(i) - 0.28, act,
                    ha="center", va="top", fontsize=9.5, color=ACCENT)
        else:                                          # down (col 3)
            xm = bx(i) + BW / 2
            arrow(ax, (xm, by(i)), (xm, by(i + 1) + BH), color=ACCENT, lw=1.8)
            ax.text(xm - 0.35, (by(i) + by(i + 1) + BH) / 2, act, ha="right",
                    va="center", fontsize=9.5, color=ACCENT)
    save(fig, "fig_program_graph")


# ====================================================================== Fig 4
def fig_architecture():
    fig, ax = plt.subplots(figsize=(7.6, 3.7))
    ax.set_xlim(0, 15); ax.set_ylim(0, 7.4); ax.axis("off")
    TOP, BOT, H = 3.9, 1.3, 1.0

    def box(x, y, w, text, fc=INKBOX, ec=ACCENT, fs=9.5):
        rbox(ax, x, y, w, H, text, fc=fc, ec=ec, fs=fs)

    def lab(p, q, text, color=INK, off=(0, 0.16), fs=8, ha="center"):
        arrow(ax, p, q, color=color)
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        ax.text(mx + off[0], my + off[1], text, ha=ha, va="bottom", fontsize=fs,
                color=color)

    box(0.2, TOP, 2.0, "User\ngoal  T")
    box(3.0, TOP, 2.2, "Program\nSelector")
    box(6.2, TOP, 2.4, "State-machine\nReplayer")
    box(6.2, BOT, 2.6, "CUA\nfallback", fc="#FDEFEF", ec=BAD)
    box(9.8, BOT, 2.0, "Compiler")
    box(9.6, TOP, 2.3, "Verify-before-\nStore Gate", fc="#FDEFEF", ec=BAD)
    box(12.7, TOP, 2.1, "Program\nCorpus", fc="#FBF1DD", ec=GOLD)
    yc = TOP + H / 2
    lab((2.2, yc), (3.0, yc), "")
    lab((5.2, yc), (6.2, yc), "P")
    # "no candidate": draw arrow, then place label clear of the line (lower-left)
    arrow(ax, (4.1, TOP), (6.4, BOT + H), color=INK)
    ax.text(3.95, 2.45, "no candidate", ha="left", va="center", fontsize=7.5,
            color=INK)
    lab((7.4, TOP), (7.4, BOT + H), "replay\nfail", color=BAD, fs=7.5,
        off=(0.55, -0.5))
    lab((8.8, BOT + H / 2), (9.8, BOT + H / 2), "trace", fs=7.5)
    lab((10.8, BOT + H), (10.8, TOP), "P'", off=(0.22, -0.5))
    lab((11.9, yc), (12.7, yc), "store /\nreplace", off=(0.0, 0.58), fs=7.5)
    # feedback loop corpus -> selector: single clean path with ONE arrowhead
    fy = 6.7
    ax.plot([13.75, 13.75], [TOP + H, fy], color=ACCENT, lw=1.3, ls="--")
    ax.plot([13.75, 4.1], [fy, fy], color=ACCENT, lw=1.3, ls="--")
    ax.plot([4.1, 4.1], [fy, 5.3], color=ACCENT, lw=1.3, ls="--")
    arrow(ax, (4.1, 5.3), (4.1, TOP + H), color=ACCENT)
    ax.text(9.0, fy + 0.12, "retrieve on next invocation", ha="center",
            fontsize=8, color=ACCENT)
    save(fig, "fig_architecture")


# ====================================================================== Fig 5
def fig_daytimeline():
    """Day 1 (explore + compile) vs Day 2 (replay) cost structure."""
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.set_xlim(0, 12.6); ax.set_ylim(0, 4.2); ax.axis("off")
    # Day 1 lane
    ax.text(0.1, 3.55, "Day 1", fontweight="bold", color=INK, fontsize=10)
    x = 1.4
    for i in range(4):
        for lbl, col in [("obs", ACC_LT), ("reason", ACC2), ("act", ACCENT)]:
            rbox(ax, x, 3.0, 0.62, 0.8, "", fc=col, ec="white", lw=0.8)
            x += 0.66
        x += 0.12
    ax.text(1.4, 2.7, "screenshot → reason → act,  ≈$N$ LLM calls", fontsize=8,
            color=INK, va="top")
    rbox(ax, x + 0.1, 3.0, 2.2, 0.8, "compile\n+ verify", fc="#FBF1DD",
         ec=GOLD, fs=8.5)
    ax.text(x + 1.2, 2.7, "one-time", fontsize=7.5, color=GOLD, va="top",
            ha="center")
    # Day 2 lane
    ax.text(0.1, 1.45, "Day 2", fontweight="bold", color=INK, fontsize=10)
    rbox(ax, 1.4, 0.9, 3.8, 0.8, "replay the program",
         fc=ACCENT, ec="white", fs=10, tc="white", bold=True)
    ax.text(1.4, 0.6, "0 LLM calls · 8.5–13× faster · verified before stored",
            fontsize=8, color=ACCENT, va="top")
    arrow(ax, (5.3, 1.3), (6.3, 1.3), color=GREEN, lw=1.6)
    rbox(ax, 6.4, 0.9, 1.7, 0.8, "done", fc="#E8F2EC", ec=GREEN, fs=9,
         tc=GREEN, bold=True)
    save(fig, "fig_daytimeline")


# ====================================================================== Fig 6
def fig_monotonic():
    fig, ax = plt.subplots(figsize=(4.7, 3.9))
    panel(ax, "y")
    seeds = {"seed 42": (10, 11), "seed 100": (9, 11), "seed 1337": (9, 10)}
    for i, (name, (cold, warm)) in enumerate(seeds.items()):
        ax.plot([0, 1], [cold, warm], "-o", color=ACC_LT, lw=1.7, ms=6,
                zorder=2, label="per seed (n=3)" if i == 0 else None)
    ax.plot([0, 1], [9.33, 10.67], "-o", color=ACCENT, lw=3.2, ms=9, zorder=3,
            label="mean")
    ax.text(-0.06, 9.33, "9.33", ha="right", va="center", fontsize=9.5,
            color=ACCENT, fontweight="bold")
    ax.text(1.06, 10.67, "10.67", ha="left", va="center", fontsize=9.5,
            color=ACCENT, fontweight="bold")
    ax.text(0.5, 8.62, "+1.33 tasks — all 3 seeds improve", ha="center",
            va="center", fontsize=9, color=ACCENT)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_xlim(-0.5, 1.6); ax.set_ylim(8.3, 12.0); ax.set_xticks([0, 1])
    ax.set_xticklabels(["Cold\n(empty corpus)", "Warm\n(built corpus)"])
    ax.set_ylabel("Tasks solved (of 15)")
    save(fig, "fig_monotonic")


# ====================================================================== Fig 7
def fig_gatecost():
    """Verify-replay overhead (the gate's one-time cost), L3 numbers."""
    fig, ax = plt.subplots(figsize=(5.0, 3.5))
    panel(ax, "y")
    plats = ["Android", "OSWorld"]
    solve = [47, 65]; verify = [76, 141]
    xx = np.arange(2); w = 0.36
    b1 = ax.bar(xx - w / 2, solve, w, color=ACCENT, label="CUA solve (Run 1)",
                edgecolor="white", lw=1.0)
    b2 = ax.bar(xx + w / 2, verify, w, color=GOLD,
                label="verify-replay (gate, one-time)", edgecolor="white",
                lw=1.0)
    for xs, v in zip(xx - w / 2, solve):
        ax.text(xs, v + 3, f"{v}s", ha="center", fontsize=10)
    for xs, v in zip(xx + w / 2, verify):
        ax.text(xs, v + 3, f"{v}s", ha="center", fontsize=10)
    ax.set_xticks(xx); ax.set_xticklabels(plats)
    ax.set_ylabel("Median wall time per task (s)")
    ax.set_ylim(0, 175)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "fig_gatecost")


# ====================================================================== Fig 8
def fig_diff_of_deltas():
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    panel(ax, "y")
    plats = ["Android\n(n=5, Gemini)", "OSWorld\n(n=5, Claude)",
             "WebArena\n(n=4+4, Claude)"]
    on, on_e = [1.20, 0.20, -4.00], [0.45, 0.45, 2.94]
    off, off_e = [-1.40, -2.40, -5.75], [0.89, 0.55, 1.71]
    diff = [2.6, 2.6, 1.75]
    xx = np.arange(3); w = 0.34
    ax.axhline(0, color=INK, lw=0.9)
    ax.bar(xx - w / 2, on, w, yerr=on_e, capsize=4, color=ACCENT,
           label="Gate ON", edgecolor="white", lw=1.0,
           error_kw=dict(ecolor=INK, lw=1.1))
    ax.bar(xx + w / 2, off, w, yerr=off_e, capsize=4, color=BAD,
           label="Gate OFF", edgecolor="white", lw=1.0,
           error_kw=dict(ecolor=INK, lw=1.1))
    for i in range(3):
        ax.text(xx[i] - w / 2, on[i] + (0.2 if on[i] >= 0 else -0.55),
                f"{on[i]:+.1f}", ha="center", fontsize=8.5,
                va="bottom" if on[i] >= 0 else "top")
        ax.text(xx[i] + w / 2, off[i] - 0.55, f"{off[i]:+.1f}", ha="center",
                fontsize=8.5, va="top")
        # "gain" bracket placed at the top of the panel, clear of the bars
        ax.annotate("", xy=(xx[i] - w / 2, 2.05), xytext=(xx[i] + w / 2, 2.05),
                    arrowprops=dict(arrowstyle="<->", color=GRAY, lw=0.9))
        ax.text(xx[i], 2.3, f"gain {diff[i]}", ha="center", va="bottom",
                fontsize=8, color=GRAY)
    ax.set_xticks(xx); ax.set_xticklabels(plats)
    ax.set_ylabel("Cold→warm Δ (tasks)"); ax.set_ylim(-8.8, 3.2)
    ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=2)
    save(fig, "fig_diff_of_deltas")


# ====================================================================== Fig 9
def fig_gate_flow():
    """The verify-before-store decision."""
    fig, ax = plt.subplots(figsize=(7.8, 3.0))
    ax.set_xlim(0, 16.4); ax.set_ylim(0, 4.7); ax.axis("off")
    yc = 2.5
    rbox(ax, 0.2, yc - 0.5, 2.1, 1.0, "CUA\nsucceeds", fc="#FDEFEF", ec=BAD,
         fs=9)
    rbox(ax, 2.8, yc - 0.5, 2.0, 1.0, "compile $P'$", fs=9)
    rbox(ax, 5.3, yc - 0.5, 2.9, 1.0, "reset env +\nverify-replay $P'$", fs=9)
    # decision diamond
    dx, dy = 9.9, yc
    diamond = plt.Polygon([(dx, dy + 1.05), (dx + 1.5, dy), (dx, dy - 1.05),
                           (dx - 1.5, dy)], closed=True, fc=INKBOX, ec=ACCENT,
                          lw=1.3)
    ax.add_patch(diamond)
    ax.text(dx, dy, "replay_ok\nand score" + r"$\,\geq\,$" + "1?", ha="center",
            va="center", fontsize=8.3)
    rbox(ax, 12.9, yc + 0.55, 3.2, 0.9, "store / replace", fc="#E8F2EC",
         ec=GREEN, fs=9.5, tc=GREEN, bold=True)
    rbox(ax, 12.9, yc - 1.45, 3.2, 0.9, "reject", fc="#FDEFEF", ec=BAD, fs=9.5,
         tc=BAD, bold=True)
    arrow(ax, (2.3, yc), (2.8, yc)); arrow(ax, (4.8, yc), (5.3, yc))
    arrow(ax, (8.2, yc), (dx - 1.5, yc))
    arrow(ax, (dx + 1.05, dy + 0.45), (12.9, yc + 1.0), color=GREEN)
    arrow(ax, (dx + 1.05, dy - 0.45), (12.9, yc - 1.0), color=BAD)
    ax.text(12.0, yc + 1.18, "yes", color=GREEN, fontsize=8.5)
    ax.text(12.0, yc - 1.15, "no", color=BAD, fontsize=8.5)
    ax.text(8.2, 0.3, "rejects the \"runs but doesn't work\" case:  "
            "cov=100%, score=0  (the contact is never written)", ha="center",
            fontsize=8, color=BAD, style="italic")
    save(fig, "fig_gate_flow")


# ===================================================================== Fig 10
def fig_baselines():
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    panel(ax, "x")
    rows = [("Workflow-Use", -7.00, 0.82, GRAY),
            ("PreAct gate-OFF", -5.75, 1.71, BAD),
            ("PreAct gate-ON", -4.00, 2.94, ACC_LT),
            ("PreAct gate-ON\n+ fallback", -1.00, 1.83, ACCENT),
            ("Muscle-Mem", -0.75, 1.50, GRAY)]
    labels = [r[0] for r in rows]; vals = [r[1] for r in rows]
    errs = [r[2] for r in rows]; cols = [r[3] for r in rows]
    yy = np.arange(len(rows))[::-1]
    ax.barh(yy, vals, xerr=errs, color=cols, capsize=4, edgecolor="white",
            lw=1.0, error_kw=dict(ecolor=INK, lw=1.1))
    for y, v in zip(yy, vals):
        ax.text(v - 0.18, y, f"{v:+.2f}", va="center", ha="right", fontsize=9,
                color=INK, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    ax.axvline(0, color=INK, lw=0.9)
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Warm − cold success-rate Δ (tasks, of 12)")
    ax.set_xlim(-9.6, 1.3)
    ax.annotate("", xy=(0.6, yy[3]), xytext=(0.6, yy[4]),
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=1.4))
    ax.text(0.8, (yy[3] + yy[4]) / 2, "indistinguishable\n(p≈0.84)", fontsize=8,
            color=ACCENT, va="center", ha="center")
    save(fig, "fig_baselines")


# ===================================================================== Fig 11
def fig_compile_llm():
    """Gate behaviour under Claude vs Gemini compile."""
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.0, 3.2),
                                   gridspec_kw=dict(width_ratios=[1, 1]))
    comps = ["Claude\nSonnet 4.6", "Gemini\n3 Flash"]
    rej = [83, 89]; warm = [2.0, 0.0]
    xx = np.arange(2)
    panel(axL, "y", title="Gate-rejection rate")
    axL.bar(xx, rej, 0.55, color=[ACCENT, TEAL], edgecolor="white", lw=1.0)
    for x, v in zip(xx, rej):
        axL.text(x, v + 1.5, f"{v}%", ha="center", fontsize=9)
    axL.set_xticks(xx); axL.set_xticklabels(comps); axL.set_ylim(0, 100)
    axL.set_ylabel("% of compiles rejected")
    panel(axR, "y", title="Warm success rate")
    axR.bar(xx, warm, 0.55, color=[ACCENT, TEAL], edgecolor="white", lw=1.0)
    for x, v in zip(xx, warm):
        axR.text(x, v + 0.12, f"{v:.1f}", ha="center", fontsize=9)
    axR.set_xticks(xx); axR.set_xticklabels(comps); axR.set_ylim(0, 7)
    axR.set_ylabel("Tasks (of 12)")
    fig.suptitle("")
    fig.tight_layout()
    save(fig, "fig_compile_llm")


# ===================================================================== Fig 12
def fig_selector():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.2, 3.5))
    mini_tau = [0.40, 0.50, 0.65, 0.70, 0.85]
    mini_func = [100, 100, 100, 86.7, 64.4]; mini_fp = [6.7, 0, 0, 0, 0]
    bge_tau = [0.50, 0.60, 0.65, 0.85]
    bge_func = [100, 100, 100, 100]; bge_fp = [93.3, 20, 0, 0]
    panel(axL, "y", title="Correct-family retrieval")
    axL.plot(mini_tau, mini_func, "-o", color=ACCENT, lw=2.2, ms=5,
             label="MiniLM-L6")
    axL.plot(bge_tau, bge_func, "-s", color=GOLD, lw=2.2, ms=5,
             label="bge-large")
    axL.axhline(75.6, color=BAD, ls="--", lw=1.8)
    axL.text(0.62, 73.0, "agentic LLM (75.6%)", fontsize=8.5, color=BAD,
             ha="center", va="top",
             bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    axL.set_xlabel("Threshold τ"); axL.set_ylabel("Functional accuracy (%)")
    axL.set_ylim(55, 105); axL.legend(frameon=False, fontsize=8.5,
                                      loc="lower left")
    panel(axR, "y", title="Mis-routing unrelated queries")
    axR.plot(mini_tau, mini_fp, "-o", color=ACCENT, lw=2.2, ms=5,
             label="MiniLM-L6")
    axR.plot(bge_tau, bge_fp, "-s", color=GOLD, lw=2.2, ms=5, label="bge-large")
    axR.axhline(0, color=BAD, ls="--", lw=1.8)
    axR.text(0.62, 8, "agentic LLM (0%)", fontsize=8.5, color=BAD, ha="center",
             bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    axR.set_xlabel("Threshold τ"); axR.set_ylabel("False-pick rate (%)")
    axR.set_ylim(-4, 100); axR.legend(frameon=False, fontsize=8.5,
                                      loc="upper right")
    fig.tight_layout()
    save(fig, "fig_selector")


# ===================================================================== Fig 13
def fig_ood():
    """Out-of-distribution: warm-OOD reps vs cold-OOD baseline."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    panel(ax, "y")
    reps = [21, 15, 14]
    ax.bar([0, 1, 2], reps, 0.55, color=ACC_LT, edgecolor="white", lw=1.0,
           label="warm-OOD per rep")
    for x, v in zip([0, 1, 2], reps):
        ax.text(x, v + 0.4, f"{v}", ha="center", fontsize=9)
    ax.axhline(16.7, color=ACCENT, lw=2.0, ls="-")
    ax.text(3.3, 16.7 + 0.45, "warm mean = 16.7", color=ACCENT, fontsize=8.5,
            ha="right", va="bottom",
            bbox=dict(fc="white", ec="none", pad=0.6))
    ax.axhline(20, color=BAD, lw=2.0, ls="--")
    ax.text(3.3, 20 + 0.45, "cold-OOD ≈ 20", color=BAD, fontsize=8.5,
            ha="right", va="bottom", bbox=dict(fc="white", ec="none", pad=0.6))
    ax.fill_between([-0.5, 2.5], 16.7, 20, color=BAD, alpha=0.08)
    ax.text(0.1, 18.35, "≈11 pp headwind", color=BAD, fontsize=8,
            style="italic")
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["rep 1", "rep 2", "rep 3"])
    ax.set_ylabel("Tasks solved (of 30 OOD)"); ax.set_ylim(0, 26)
    ax.set_xlim(-0.6, 3.4)
    save(fig, "fig_ood")


# ===================================================================== Fig 14
def fig_guardrails():
    """Guardrails ablation: aggregate-neutral."""
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    panel(ax, "y")
    groups = ["Cold", "Warm"]
    on = [10.2, 11.0]; off = [10.2, 10.6]
    xx = np.arange(2); w = 0.34
    ax.bar(xx - w / 2, on, w, color=ACCENT, label="guardrails ON",
           edgecolor="white", lw=1.0)
    ax.bar(xx + w / 2, off, w, color=ACC_LT, label="guardrails OFF",
           edgecolor="white", lw=1.0)
    for xs, v in zip(xx - w / 2, on):
        ax.text(xs, v + 0.08, f"{v}", ha="center", fontsize=10)
    for xs, v in zip(xx + w / 2, off):
        ax.text(xs, v + 0.08, f"{v}", ha="center", fontsize=10)
    ax.set_xticks(xx); ax.set_xticklabels(groups)
    ax.set_ylabel("Tasks solved (of 15)"); ax.set_ylim(8, 12)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    save(fig, "fig_guardrails")


# ===================================================================== Fig 15
def fig_compile_audit():
    """Composition of the 58-program Android corpus (compile-fidelity audit)."""
    fig, ax = plt.subplots(figsize=(6.4, 1.9))
    ax.set_xlim(0, 58); ax.set_ylim(0, 1); ax.axis("off")
    segs = [(16, BAD, "16 lossy-risk\n(edit/move/delete, no navigate_back)"),
            (27, ACC_LT, "27 benign linear\n(create/add/toggle)"),
            (15, GRAY, "15 other\n(<4 transitions / has back)")]
    x = 0
    for n, col, lbl in segs:
        ax.add_patch(Rectangle((x, 0.35), n, 0.5, color=col, ec="white",
                     lw=1.2))
        ax.text(x + n / 2, 0.6, str(n), ha="center", va="center",
                color="white", fontweight="bold", fontsize=11)
        ax.text(x + n / 2, 0.18, lbl, ha="center", va="top", fontsize=7.6,
                color=INK)
        x += n
    ax.text(0, 0.97, "58 stored Android programs", fontsize=9,
            color=ACCENT, fontweight="bold", va="top")
    save(fig, "fig_compile_audit")


# ===================================================================== Fig 16
def fig_arch_ab():
    """State-machine vs flat-script runtime."""
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    panel(ax, "y")
    modes = ["state-machine\n(verified)", "flat-script\n(ActionEngine-style)"]
    means = [11.67, 10.6]; errs = [0.58, 1.14]
    ax.bar([0, 1], means, 0.5, yerr=errs, capsize=5, color=[ACCENT, GRAY],
           edgecolor="white", lw=1.0, error_kw=dict(ecolor=INK, lw=1.1))
    for x, v in zip([0, 1], means):
        ax.text(x, v + 0.14, f"{v}", ha="center", fontsize=10)
    ax.set_xticks([0, 1]); ax.set_xticklabels(modes)
    ax.set_ylabel("Warm tasks solved (of 15)"); ax.set_ylim(9, 12.6)
    save(fig, "fig_arch_ab")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for fn in (fig_rerun_crisis, fig_landscape, fig_program_graph,
               fig_architecture, fig_daytimeline, fig_monotonic, fig_gatecost,
               fig_diff_of_deltas, fig_gate_flow, fig_baselines,
               fig_compile_llm, fig_selector, fig_ood, fig_guardrails,
               fig_compile_audit, fig_arch_ab):
        fn()
    print("all figures generated")
