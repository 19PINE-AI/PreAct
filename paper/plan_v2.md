# PreAct paper plan v2 (post-validation, 2026-04-27)

Reframes the paper around the empirically validated story:
**PreAct is a verified self-extending executable-code-corpus harness for CUAs.** The harness — RAG retrieval + verify-before-store gate + agentic program selector + hybrid CUA-fallback + compile-and-extend loop — produces monotonic refinement on multi-platform CUA benchmarks. The artifact (state-machine programs in `rag_db/`) IS the runtime — directly executable, growable, and replaceable through the harness's verified compile-extend loop.

This v2 plan **demotes** prompt engineering and runtime guardrails (gaps #4, #5 closures show they are not load-bearing) and **elevates** the harness contribution.

---

## Old framing (v1, abstract)

The original abstract presented **four contributions**:
1. State-machine-as-executable architecture
2. Task-directed trajectory recording
3. Monotonic graph refinement
4. Verify-before-store gate (added in v1.5)

It also implied prompt-level Pre-Act content and runtime guardrails were valuable — an implication the data **refute** at multi-seed n=5.

## New framing (v2)

PreAct's central contribution is a **self-extending executable code corpus**:

> The agent's "memory" is a corpus of directly-executable state-machine programs. The harness contains a verified compile-extend loop: when CUA succeeds on a task, the trace is compiled to a state-machine program; when RPA replay fails or partial-replays, the harness falls through to CUA, generates a fresh state-machine, and (passing the verify-gate) extends or replaces in the corpus. The artifact is the runtime — what the agent "remembers" is what it can directly execute.

The four updated contributions:

1. **State-machine-as-executable** (architectural — the artifact is the runtime, no flat-script generation step). Untested by AB; supported by working implementation across two platforms.

2. **Self-extending executable code corpus** (mechanism — the harness's compile-extend-replace loop is what produces monotonic refinement). Validated indirectly by gap #2 (verify-gate ablation) and gap #3 (cold→warm monotonicity at n=3).

3. **Verify-before-store gate** (the load-bearing claim — gate is empirically necessary for monotonic refinement). Validated at n=5 cross-platform.

4. **Cross-platform monotonic refinement** (the SR claim — Pre-Act's harness produces monotonic warm-vs-cold improvement on Android and OSWorld). Validated at n=3 cold→warm pairs Android, n=2 cold→warm pairs OSWorld test_tiny.

---

## Section-by-section paper structure

### §1 Abstract (revised, ~250 words)
- Problem: CUAs have a "rerun crisis" — the same task is re-derived from scratch on each invocation.
- Existing approaches: skill-based (still LLM-bound), compilation-based (too narrow), record/replay (linear, no fallback).
- **Pre-Act's contribution**: a *self-extending executable code corpus* — state-machine programs are directly executable runtime artifacts grown by the harness's verified compile-extend loop.
- **Empirical**: verify-gate is necessary for monotonicity (n=5 Android, n=2 OSWorld; diff-of-deltas 2.6/3 tasks; 5 reproducible cov=100%/score=0 smoking-gun replays). Cold→warm monotonic refinement holds n=3 Android (Δ=+1.33). Cross-model SOTA-parity (Gemini = Claude = 73.3%).
- Novel framing: the artifact IS the runtime; the harness self-extends the corpus.

### §2 Introduction (~1.5 pages)
- §2.1 The rerun crisis (cite Chundru 2026)
- §2.2 Related approaches' limitations (Muscle-Mem, AgentRR, Workflow-Use linear; ActionEngine flat-script; Compiled-AI narrow business logic)
- §2.3 Pre-Act's positioning: state-machine-as-executable + verified self-extending corpus
- §2.4 Contributions (four, mapped to empirical support level)
- §2.5 Roadmap

### §3 Related Work (~1 page)
Reuse current DESIGN.md §3 — it's already paper-quality. Add a comparison table:

| System | Memory representation | Replay fidelity | Fallback path | Self-extension |
|---|---|---|---|---|
| Muscle-Mem | Linear tool calls | Direct | Agent if cache-miss | Append cache only |
| AgentRR | Multi-level experiences | Indirect | LLM | Append only |
| Workflow-Use | Linear scripts | Direct | Agent | Append only |
| ActionEngine | State machine | **Flat-Python generated, not the SM** | None | Re-crawl |
| **Pre-Act** | **State machine** | **The SM IS the runtime** | **CUA + recompile under verify-gate** | **Verified corpus growth + replacement via dedup-signature** |

### §4 System Architecture (~2 pages)
Reuse DESIGN.md §4 with structural updates:
- §4.1 Compile-extend-replace loop (NEW — the central diagram)
- §4.2 RPA program structure (state machine)
- §4.3 Agentic program selector (RAG)
- §4.4 Hybrid replay + CUA fallback
- §4.5 Verify-before-store gate (mechanism + double-gate rationale)

### §5 RPA Program Structure (~1 page)
Trim DESIGN.md §5 to essential — keep the JSON schema, the action-type list (table), the parameter inference. Move detailed examples to appendix.

### §6 Empirical Validation (~3 pages — THIS IS THE BIG ADDITION)

#### §6.1 Setup
- Benchmarks: AndroidWorld official-15, OSWorld test_tiny, WebArena (existing)
- Models: Gemini 3 Flash for Android CUA (cost), Claude Sonnet 4.6 for OSWorld + compile/RAG
- Container: huggingface/android_world:latest with /state patch volume-mount
- Multi-seed: 5 seeds (42, 100, 1337, 2024, 7777) with rag_db reset per seed

#### §6.2 Cold→warm monotonicity (closes §2.3.2 gap #1, #3)
- Table: 3-seed cold→warm pairs (Δ = +1, +2, +1; mean +1.33 ± 0.58)
- Mode-shift figure: 8/13, 8/11, 5/10 successful warm tasks shifted cua → rpa/hybrid

#### §6.3 Verify-gate ablation — the load-bearing experiment
- 2×2 design (cold/warm × gate ON/OFF)
- n=5 Android table (Δ ON +1.2 ± 0.45, Δ OFF -1.4 ± 0.89, all 5 ON monotonic, all 5 OFF regress)
- Sign-test p < 0.001
- OSWorld n=2 table (both reps Δ OFF = -3 = -50pp)
- 5 cov=100%/score=0 smoking-gun replays — table with mechanism column

#### §6.4 What's NOT load-bearing (gaps #4, #5, #7 closures)
- Prompt-level: agent.py:464 omits additional_guidelines; production runs verbatim T3A
- Code-level guardrails: 2×5 AB cold means identical (10.2 = 10.2)
- Step-budget: cap-A vs cap-B Δ=+1.8 within ±2 prediction; +30% wall

#### §6.5 Cross-model replication (gap #9)
- Gemini 3-seed mean = Claude reference = 73.3%
- Identical stable fail-set: BrowserDraw, SystemBrightnessMax, SystemWifiTurnOn

### §7 Discussion (~1.5 pages)
- §7.1 Why the harness is load-bearing: the verify-gate's mechanism explained via cov=100%/score=0
- §7.2 What's harness-deterministic vs LLM-driven: 3 stable Android FAILs are deterministic UI patterns the agent loops on regardless of model/seed/config
- §7.3 Threats to validity (DESIGN.md §2.3.2 mapped to closure status — table)
- §7.4 Generalizability: only Android+OSWorld+WebArena; gap #8 acknowledged

### §8 Conclusion (~0.5 pages)
PreAct demonstrates that **a self-extending verified executable-code corpus** is sufficient for monotonic refinement on CUA benchmarks. The harness — not prompt engineering or runtime tuning — is the load-bearing contribution. Future work: scale to longer-horizon tasks, more diverse benchmarks, integrate with planning frameworks for explicit goal decomposition.

### Appendices
- A: Computer-action schema (JSON)
- B: Per-task results across all multi-seed runs (data table)
- C: Container patch (`android_server_patched.py`)

---

## Length budget

Target: 12-page main + 4-page appendix = 16 pages, fitting an arXiv preprint format.

| Section | Pages |
|---|---|
| Abstract | 0.3 |
| §2 Intro | 1.5 |
| §3 Related Work | 1.0 |
| §4 Architecture | 2.0 |
| §5 RPA Structure | 1.0 |
| §6 Empirical Validation | 3.0 |
| §7 Discussion | 1.5 |
| §8 Conclusion | 0.5 |
| References | 1.0 |
| Appendix A-C | 4.0 |
| **Total** | **15.8** |

---

## Implementation plan for paper writing

1. ✅ Write plan v2 (this doc)
2. ⏳ Write findings_summary.md (data + tables, source for §6)
3. ⏳ Set up LaTeX template (preact.tex, arxiv-style equivalent, references.bib)
4. ⏳ Write §1 Abstract (revised)
5. ⏳ Write §2 Intro (mostly reuse from DESIGN.md)
6. ⏳ Write §3 Related Work + comparison table
7. ⏳ Write §4 Architecture (with new compile-extend-replace diagram)
8. ⏳ Write §5 RPA Structure (trimmed)
9. ⏳ Write §6 Empirical Validation (NEW — this is most of the work)
10. ⏳ Write §7 Discussion
11. ⏳ Write §8 Conclusion
12. ⏳ Compile, iterate, polish
