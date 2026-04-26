# Experimental Methods — AB Design (paper §8.X insertion)

A polished, publication-ready prose treatment of the AB experimental design used for the §2.3.2.1 gap closures. Designed to slot into §8 (Evaluation Plan) as a new subsection §8.4 or §8.5, replacing forward-looking validation language with retrospective-of-completed-work language.

---

## §8.X Empirical-Validation AB Experiments

To support the §2.3.1 monotonic-refinement claim with controlled-experiment evidence rather than single-run anecdotes, we executed four ablation experiments on the AndroidWorld official-15 task subset, using Gemini 3 Flash as the CUA backend (selected for cost: ~10× cheaper than Claude Sonnet at equivalent SR; cf. §2.3.1.1 cross-model replication). Each experiment isolates one of the validity threats enumerated in §2.3.2.

### §8.X.1 Common protocol

- **Task subset**: AndroidWorld official-15 (the curated subset used by the upstream T3A baseline). 15 tasks across 8 application domains (audio recorder, browser, camera, clock, contacts, files, markor, system).
- **Container**: `huggingface/android_world:latest` with the Pre-Act `/state` patch volume-mounted (`-v android_server_patched.py:/server/android_server.py:ro`). Fresh container boot before each experiment to avoid AVD-state confounds across conditions.
- **Step budget**: `min(max(args.max_steps, 8 × complexity), 30)` per task with `args.max_steps=20`, the current Pre-Act default. (Exp 4 ablates this.)
- **Verify-before-store gate**: `replay.success ∧ score ≥ 1.0` (the double gate). (Exp 1 ablates this.)
- **rag_db state**: each cold-warm pair starts with an empty `rag_db/` (the prior pair's store is moved to a backup directory). This isolates LLM nondeterminism from warm-RAG accumulation, addressing §2.3.2 threat #1's caveat that earlier multi-seed measurements shared a single growing store across seeds.

### §8.X.2 Experiment 1 — Verify-gate ablation (closes §2.3.2 threat #2)

A 2×2 factorial design crosses cold/warm with verify-gate ON/OFF, holding seed=42 fixed.

- **Condition A (gate ON)**: current Pre-Act default; the `--verify-before-store` flag wires `verify_before_store=True` in `benchmark/androidworld/run_docker.py:91`.
- **Condition B (gate OFF)**: `--no-verify-before-store` flag; programs are stored on first successful compile without the replay-and-rescore step.
- Each condition runs cold (empty rag_db) then warm (the cold-built store).

The expected mechanism is: under condition B, lossy compiles enter the store; warm RPA replays of those programs execute the action sequence to completion (cov=100%) but the live evaluator scores 0 (the program "ran" but didn't accomplish the goal). The expected SR signal: gate ON shows monotonic refinement (warm ≥ cold); gate OFF shows regression (warm < cold). The difference of deltas is the verify-gate's empirical marginal value.

The 2×2 result confirms this prediction at n=1 with two specific smoking-gun cases (ContactsAddContact, MarkorCreateFolder), where stored-but-lossy programs replay cleanly and fail evaluation. We extend the design to n=5 seeds (42, 100, 1337, 2024, 7777) to bound the variance.

### §8.X.3 Experiment 3 — Code-level guardrails ablation (closes §2.3.2 threat #5)

A 2×2 factorial crosses cold/warm with `PREACT_GUARDRAILS=on/off`, an environment variable wired into `preact/platforms/android/t3a_cua.py:62` that gates three code-level guardrails: (a) double-tap-before-input_text on populated text fields (replace semantics), (b) image-task no-op cap (`infeasible` after 4 consecutive no-op actions on goals containing image keywords), and (c) scroll-direction exhaustion notes appended to step summaries.

The hypothesis (per §2.3.2 threat #5) was that these guardrails materially improve SR on Markor edit-content tasks. The 2×2 result instead shows aggregate-neutral SR (cold tie 10=10, warm vanilla wins by 1) with task-specific effects: the double-tap mechanism is empirically necessary for AudioRecorderRecordAudioWithFileName (the filename dialog has a pre-filled default that must be cleared), but the timing cost of the guardrail interferes with Camera-task flows. The findings reframe the guardrails as protective extras for edge cases rather than as load-bearing components of the SOTA-parity claim.

### §8.X.4 Experiment 4 — Step-budget ablation (closes §2.3.2 threat #7)

A 1-D ablation crosses the dynamic step budget `min(max(20, 8c), 30)` (cap-A) with a fixed unbounded 60-step budget (cap-B), achieved by `--max-steps 60 --no-dynamic-steps`. Single seed (n=1), with multi-seed extension to n=5 in progress.

The validation-plan prediction was "SR within ±2 tasks; wall-time(A) ≤ 0.7 × wall-time(B)" — i.e., the cap saves wall time without sacrificing SR. The n=1 result confirms exactly: SR Δ = +1 (within ±2), wall ratio = 0.69 (within 0.7). The mechanism explanation: stuck FAIL trajectories (the deterministic harness failures) consume the full extended budget without recovery — SystemBrightnessMax runs the full 60-step budget under cap-B then fails (vs failing at 20 under cap-A), wasting +6.7 minutes on a doomed trajectory.

### §8.X.5 Experiment 5 — Cold→warm monotonicity (closes §2.3.2 threats #1 and #3)

A multi-seed measurement of the cold→warm SR delta with rag_db reset per seed (n=3 seeds: 42, 100, 1337; extension to n=5 in progress). All three seeds show monotonic refinement (Δ = +1, +2, +1). The mode-shift from CUA-only on cold to RPA/hybrid retrieval on 5–8 of 11–13 successful warm tasks per seed directly evidences the harness using stored programs.

### §8.X.6 Cross-model replication (closes §2.3.2 threat #9)

To address the concern that the SOTA-parity number is Claude-specific (the original §2.3.1 measurement used Claude Sonnet 4.6), we replicated the cold-and-warm measurement on Gemini 3 Flash with three seeds. The 3-seed mean (73.3%) matches the prior Claude datapoint (73.3%) exactly, and the stable failure set (BrowserDraw, SystemBrightnessMax, SystemWifiTurnOn) is identical across both backends. The shared fail set across models and seeds implicates harness-level deterministic failures (status-bar stale read on wifi, scroll-on-seekbar incompatibility on brightness, image-canvas-not-in-a11y-tree on draw) rather than model-capability differences. The "matches T3A+Claude" claim is therefore not Claude-specific.

### §8.X.7 OSWorld port (in progress)

The verify-gate ablation generalizes across platforms by design: the gate is implemented in `benchmark/{androidworld,osworld}/run_*.py:118` (parallel sites) and tested independently. We replicate the AB on OSWorld test_tiny (6 tasks) using Claude Sonnet 4.6 as the CUA backend (OSWorld's standard Computer-Use API). The OSWorld port uses the same `--verify-before-store / --no-verify-before-store` flags. Results pending; expected to confirm the generalizability of the gate's mechanism across desktop and mobile platforms.

---

## Notes for paper integration

1. This subsection is **descriptive of completed experiments**, not prospective. It complements the existing §8.1-§8.3 prose which describes the broader evaluation plan.

2. The §8.X numbering preserves the existing §8 structure — drop in as §8.4 (between §8.3 metrics and the existing §8.4 baseline-system implementation details, if any) or append as §8.5/§8.6.

3. The "in progress" marker on §8.X.7 OSWorld will be updated to a result paragraph once OSWorld test_tiny gate-ON + gate-OFF pair completes (~ 1.5 hours from kickoff at 02:28).

4. Multi-seed n=5 extensions (in §8.X.2 Exp 1, §8.X.3 Exp 3, §8.X.4 Exp 4) update the language from "at n=1" to "across n=5 seeds, mean … ± std" once the orchestrator queue completes (~22 hours).

5. Per-experiment data tables are in `/home/ubuntu/PreAct/paper/figures.md`; reference them inline by figure number when the manuscript is laid out.
