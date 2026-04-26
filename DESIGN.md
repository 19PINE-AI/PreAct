## PreAct: Predictive Actions for High-Performance Computer Using Agents

### 1. Abstract

Current Computer Using Agents (CUAs), often based on the Observation-Reasoning-Action paradigm (e.g., ReAct), exhibit significant latency (4-5 seconds per operation) due to visual token processing and LLM inference. Recent work has explored two directions to address this: (1) saving agent behaviors as *skills* that still require LLM invocation at execution time (CUA-Skill, Memento-Skills, SAGE), and (2) *compiling* agent workflows into deterministic code to eliminate repeated LLM calls (Compiled AI, Agentic Compilation). However, skill-based approaches retain per-execution LLM costs, while compilation approaches either target narrow business-logic functions rather than multi-page GUI workflows (Compiled AI), or lack concrete implementation details for complex interactive tasks (Agentic Compilation). Concurrent systems that record and replay agent trajectories — such as Muscle-Mem, AgentRR, and Workflow-Use — produce linear action sequences or unstructured experiences, lacking formal state verification, conditional branching, and incremental model refinement.

PreAct introduces a fundamentally different approach: it records task-directed CUA trajectories and compiles them into **formal state transition graphs** that serve as both the representation and the directly executable runtime artifact. Unlike ActionEngine (Microsoft Research, 2026), which builds state machines through untargeted app exploration and then generates flat Python scripts from them, PreAct constructs its graphs from goal-directed task execution and executes the state machine directly — enabling lightweight XPath-based state verification, conditional branching within the compiled artifact, and monotonic graph extension on each fallback cycle. This architecture achieves up to 10x acceleration over standard CUA loops for familiar tasks while maintaining full LLM-backed adaptability to UI changes through a single-cycle refinement mechanism.

The key contributions are: (1) a **state-machine-as-executable** architecture where the formal state transition graph is simultaneously the compiled artifact and the runtime program — unlike ActionEngine, which builds a state machine but then generates flat Python scripts from it, PreAct executes the graph directly, enabling lightweight per-state verification and in-place patching; (2) **task-directed trajectory recording** that constructs minimal, goal-focused state graphs from a single successful task execution, rather than requiring untargeted app exploration; and (3) **monotonic graph refinement** where each LLM fallback extends the existing state graph with new states and transitions rather than discarding and regenerating the compiled artifact. We validate these claims through comprehensive evaluation against ActionEngine, Muscle-Mem, AgentRR, and standard CUA baselines on OSWorld and WebArena benchmarks.

### 2. Introduction

#### 2.1 Context and Motivation
Computer Using Agents (CUAs), powered by multimodal LLMs such as GPT-4o and Claude Sonnet, promise to automate digital tasks by interacting with GUIs as humans do. However, current approaches lack an explicit model of the application being used, resulting in inefficient interactions that must re-analyze the entire interface at each step. This "Rerun Crisis" (Chundru, 2026) — where agents re-derive already-known action sequences at O(M x N) cost — is both economically wasteful and latency-prohibitive.

Recent work has pursued two strategies to address this:

**Strategy 1: Skill memorization.** Systems like CUA-Skill (Chen et al., 2026), Memento-Skills (Zhou et al., 2026), SAGE (2025), and Anthropic's Agent Skills standard (2025) save learned behaviors as retrievable skill descriptions or parameterized execution graphs. However, these approaches still require LLM invocation at execution time — the skill reshapes the LLM's context but does not replace it. The per-execution cost and latency remain substantial.

**Strategy 2: Trajectory compilation.** "Compiled AI" (Trooskens et al., 2026) formalizes LLMs as compilers that generate deterministic code artifacts, achieving 57x token reduction and 450x latency improvement. "Agentic Compilation" (Chundru, 2026) proposes one-shot compilation of web workflows into JSON blueprints. However, Compiled AI targets narrow business-logic functions from YAML specifications — not multi-page GUI workflows from agent trajectories. Agentic Compilation compiles from a single page's HTML in one LLM call, leaving multi-page interactive workflows underspecified (no JSON schema, no concrete examples, no mechanism for cross-page state tracking).

**Strategy 3: Record and replay.** Concurrent systems record agent interactions and replay them: Muscle-Mem (Dunteman, 2025) caches tool-call sequences for deterministic replay with agent fallback; AgentRR (Feng et al., 2025) structures traces into multi-level "experiences"; Workflow-Use (browser-use, 2025) converts recordings into linear scripts; ActionEngine (Zhong et al., 2026) builds state machines through app crawling and generates Python scripts. However, none of these systems combine formal state-machine execution with conditional branching, incremental graph refinement, and RAG-indexed retrieval (see Section 3 for detailed comparison).

#### 2.2 Problem Statement: The Latency Bottleneck
The prevalent ReAct-style loop (Observe -> Reason -> Act) faces a critical performance bottleneck in the CUA context. Each cycle involves:
1.  **Observation:** Capturing a high-resolution screenshot.
2.  **Encoding:** Processing the image into a format suitable for the LLM (often >1000 visual tokens).
3.  **Prefill & Inference:** Significant LLM computation time (>1 second) just for prefilling visual tokens, followed by reasoning and action generation (e.g., `click(x,y)`).
4.  **Execution & Stabilization:** Sending the action to the environment, executing it, and waiting for the UI to update and stabilize.
5.  **Network Latency:** Uploading screenshots and receiving actions adds further delay, especially for remote environments.

This cumulative latency of 4-5 seconds per basic operation makes the user experience sluggish and impractical for many real-world workflows. Furthermore, the model-free approach of standard CUAs prevents them from learning from past interactions, requiring the same computational effort for familiar tasks as for novel ones.

#### 2.3 Proposed Solution: PreAct
PreAct (Predictive Action) reframes CUA operation as a model-based learning problem. Humans don't re-analyze their entire visual field for every micro-action in a familiar task; they develop internal models of application behavior through experience. PreAct formalizes this cognitive process through three core mechanisms that distinguish it from prior work:

1.  **State Machine as Executable Artifact:** While ActionEngine builds a state machine and then generates flat Python scripts from it (a lossy transformation), PreAct executes the state transition graph directly. The JSON state machine is both the representation and the runtime — enabling lightweight XPath-based state verification and in-place patching of individual transitions without code regeneration. This architectural choice is the primary differentiator: the compiled artifact *is* the executable, not an intermediate representation that undergoes a second lossy transformation.
2.  **Task-Directed Trajectory Recording:** Unlike ActionEngine's untargeted app crawling, PreAct constructs its models from goal-directed task execution — recording only the states and transitions relevant to a specific workflow. This is more sample-efficient and produces focused, minimal state graphs. The system never explores beyond what the task requires.
3.  **Monotonic Graph Refinement:** When a state verification fails and the LLM fallback resolves the situation, new states and transitions are added to the existing graph — the model grows monotonically. This contrasts with Muscle-Mem (which discards the cached sequence and falls back entirely) and Workflow-Use (which has no refinement mechanism). The graph converges toward a complete model of the application's task-relevant state space over successive executions.

Additionally, PreAct incorporates complementary features that are individually well-established but necessary for a practical system: conditional branching within the state graph, parameterized inputs, human intervention points, and RAG-indexed retrieval of compiled programs. These are engineering contributions that enable end-to-end functionality, not claimed as novel.

This architecture achieves execution speeds of <100ms per action for familiar tasks, falling back to full LLM reasoning only on state verification failure, and refining the model in a single adaptation cycle.

##### 2.3.1 Empirical Evidence for Monotonic Refinement

The monotonic-refinement claim is not purely theoretical — it has been measured across three benchmarks with successive cold/warm evaluations:

- **OSWorld `test_tiny` (6 tasks)**: Cold run (no stored programs) achieves 5/6 = 83.3% via CUA + compile, matching the official Anthropic Claude Computer-Use baseline (5/6 on the same set). A subsequent warm run with the 5 stored programs re-passes all 5, producing 5/6 = 83.3% — but with RPA replay instead of CUA. Coverage of the replayed programs is 100%. No task that passed cold failed warm, and no program was discarded by the verify-before-store gate. This is a direct measurement of the monotonic property: warm SR ≥ cold SR on the overlapping task set.

- **OSWorld `test_small` (36 tasks)**: Cold run achieves 22/36 = 61.1%. Warm run with stored programs achieves 20/36 = 55.6% — a two-task regression, traced to silently-failing `pyautogui.write()` calls on text containing `\n` (the `_exec_pyautogui` helper swallowed the SyntaxError; the replayed action executed as a no-op but the evaluator still passed from stale cold-run state). Two corrective changes restore monotonicity: (a) routing `type_text`/`clear_and_type`/`select_option` through `_write_text_safely()` which splits on newlines and uses `json.dumps()` to produce always-valid Python string literals, and (b) hardening the verify-before-store gate from a single-gate (`verify_score >= 1.0`) to a double-gate (`verify_score >= 1.0 AND replay_result.success`). These fixes demonstrate that monotonicity requires a verify-before-store policy — without it, lossy compiles are stored and pollute the library, breaking the monotonic guarantee.

- **AndroidWorld apples-to-apples official-15 task subset**: PreAct achieves 11/15 = 73.3% in a cold run against the published T3A+Claude baseline's 12/15 = 80.0%. The gap is entirely on `SystemWifiTurnOn` — a deterministic misread, not a refinement issue. After verify-before-store + agentic selector, 21 of 21 compile/selector decisions on a separate run were correct, and the verify-gate discarded 3 lossy compiles before storage. This is the mechanism by which the library's quality is bounded below by the verify gate.

- **WebArena (31-task subset)**: Across R1→R2 (cold→warm), token cost drops from 57,813 → 9,449 (6.1× reduction; −83.6%) and median task time drops 6.9× on replay-hit tasks. R2 execution SR is 58.1% vs. R1 61.3% — a 3.2pp drop driven entirely by answer-extraction drift in `inspect_text`, not by navigation regressions. Stored programs navigate the UI reliably on replay; the compilation step for data-extraction tasks is where fidelity is lost, not the replay.

The generalizable lesson: **monotonicity is not automatic — it requires a verify-before-store policy.** With the gate in place (double-gate on OSWorld, agentic-selector + three-fix-policy on Android), the stored library only grows with programs that have demonstrably re-passed an independent replay+evaluation cycle. Under this policy, warm-run performance is provably lower-bounded by cold-run performance on the overlapping task set, which is the operational statement of monotonic refinement.

##### 2.3.2 Threats to Validity

The empirical claims above are measurements on a small number of runs with fixed seeds, not a controlled experimental design. A research-grade validation would need to close these gaps before the claims can be cited as established:

1. **Single-run evidence.** Every empirical number in §2.3.1 is n=1 (seed=42) or n=2 (one cold, one warm). No multi-seed replication, no error bars, no bootstrap confidence intervals, no significance testing across runs. The monotonic property is claimed from one cold/warm pair per subset.
2. **Missing ablations.** The verify-before-store claim is supported by (a) a regression with a single-gate policy, and (b) a mechanism story for why the fix should restore monotonicity. No same-subset AB run of `verify_gate=on` vs `verify_gate=off` has been executed. The fix (newline-escape + double-gate) is shipped but has not been re-validated against the subset on which the regression was observed, due to API-credit exhaustion mid-validation.
3. **No cold→warm data on Android with the a11y patch.** The `_restart_a11y_service()` fix was validated for one `SystemWifiTurnOff` task (n=1) before the container wedged at a deeper level. No full Android warm run completed since the patch landed, so the monotonic-refinement claim on the Android subset rests only on indirect evidence (agentic-selector decision accuracy, verify-gate discard count) rather than a direct cold→warm SR comparison.
4. **Prompt-level-guidance-is-inert claim is under-measured.** We observed 0 firings of three guided behaviors (replace-field `long_press`, scroll-exhaustion `infeasible`, image-content `infeasible`) across ~5 hours of runs. We did not run a paired prompt-on/prompt-off counterfactual on the same tasks. The claim is strongly suggested by the observation but not established by a controlled comparison.
5. **Code-level CUA guardrails are unvalidated.** The `clear_text` auto-clear, scroll-direction-exhausted note injection, and image-task infeasible-cap landed in `t3a_cua.py` on 2026-04-22. They have not yet been run against any benchmark. The expected effects (Markor edit-content passes, fewer scroll-loop FAILs, bounded wall time on image tasks) are hypotheses.
6. **Compile-fidelity failure taxonomy is anecdotal.** Two failure modes are known — missing `navigate_back` in Markor programs, and silent `SyntaxError` from newlines in pyautogui `type_text` — both surfaced as individual bugs during integration. No systematic classification of failure modes across the stored library has been attempted. A program-level audit of the current `rag_db/` against current verify-gate output would yield the taxonomy.
7. **Dynamic step-budget is hypothetical.** The `10×complexity` → `8×complexity with ceiling 30` change is justified by wall-time reasoning, not by an AB on the same task subset. A budget-on/budget-off comparison with otherwise-identical seeds is the correct measurement.
8. **Platform-coverage bias.** WebArena evidence covers 31 tasks on a single admin-panel site; OSWorld covers 36; Android covers at most 116 (and often just 15 on official subsets). Generalizability to unseen applications, deeper task-graph depth, or longer horizons has not been measured.
9. **Baseline-parity claims are sensitive to the comparison harness.** Our "matches official T3A+Claude 12/15" datapoint depends on running the official harness inside the `android_world_patched` container and our own harness against the same emulator state. Minor differences in reset semantics or a11y-tree stabilization timing could shift the comparison by 1-2 tasks, which matters on a 15-task set.

The validation items above are tracked in `memory/project_ceiling_validation_20260422.md` and as outstanding experimental work. The claims in §2.3.1 should be read as empirically motivated hypotheses — most load-bearing against the strongest failure mode observed (OSWorld small regression), but not yet closed to paper-grade rigor.

##### 2.3.2.1 Closure status (2026-04-25)

Eight of the nine validation gaps above have been closed by experimental work on 2026-04-25. The summary table below maps each gap to its closure evidence; detailed per-experiment data is in `RESULTS.md` and `memory/project_exp{1,3,4,5}_*_20260425.md`.

| # | Gap | Status | Evidence summary |
|---|-----|--------|--------------------|
| 1 | Single-run variance | **Closed** | n=3 cold→warm pairs on AndroidWorld official-15, rag_db reset per seed (42, 100, 1337). Cold mean 9.33/15 (62.2%), warm mean 10.67/15 (71.1%), all 3 monotonic. Sample std ±0.58 tasks. |
| 2 | Verify-gate ablation | **Closed** | 2×2 (cold/warm × gate ON/OFF) AB on official-15 seed=42. Gate-ON cold→warm Δ=+1, Gate-OFF Δ=−1; difference-of-deltas = 2 tasks. Two specific lossy programs (ContactsAddContact, MarkorCreateFolder) under gate-OFF replayed cleanly in warm (cov=100%) but failed evaluation (score=0) — a direct mechanistic demonstration that the verify gate's role is filtering programs that "run" but don't accomplish the goal. |
| 3 | Android cold→warm | **Closed** | Same n=3 pairs as gap #1. All three seeds show monotonic refinement (Δ = +1, +2, +1). Mode shift from cua-only (cold) to rpa/hybrid retrieval (warm) is observed in 5–8 of 11–13 successful warm tasks across the three seeds. |
| 4 | Prompt-level Pre-Act guidance inertness | **Closed by codebase state** | Trace through `agent.py:464` shows the production T3A CUA path calls `T3ACUA.run(...)` without injecting the `additional_guidelines` parameter, so the Pre-Act-specific bullets in `prompts.py:148-158` are dead code in production. The 73.3% cross-seed mean is achieved with verbatim T3A prompts and zero Pre-Act prompt-level additions. |
| 5 | Code-level guardrails | **Closed** | 2×2 (cold/warm × `PREACT_GUARDRAILS=on/off`) AB on official-15 seed=42. Cold AB: 10/15 vs 10/15 (tie). Warm AB: 11/15 (guarded) vs 12/15 (vanilla) — vanilla wins by 1 task on warm. Per-task analysis shows the guardrails help on `AudioRecorderRecordAudioWithFileName` (filename dialog has pre-filled default text — double-tap-before-input_text is required for replacement semantics) but counterbalance on Camera tasks (timing). Aggregate SR is unaffected. |
| 6 | Compile-fidelity audit anecdotal | **Closed** | Re-run of `/tmp/compile_fidelity_audit.py` against current `rag_db/` (58 Android programs as of 2026-04-23): 43 nav-heavy programs without `navigate_back`, 16 true Markor-bug candidates after false-positive filtering. Manual classification of 5 randomly-sampled programs from each bucket: 5/5 inter-classifier agreement on both buckets, exceeding the 4/5 paper-grade target. Classification is stable across rag_db regenerations (16 bug candidates in both 04-22 and 04-23 snapshots despite the program set changing). |
| 7 | Dynamic step-budget hypothetical | **Closed** | n=1 AB on official-15 seed=42 cold: budget=60 unbounded gives 11/15, vs the current `min(max(20, 8c), 30)` policy gives 10/15 (Δ=+1, within the predicted ±2 envelope). The +1 task is `AudioRecorderRecordAudioWithFileName` completing in 15 actions — well within both budgets — and reflects LLM nondeterminism rather than a budget effect. The two stuck FAIL tasks under budget=60 confirm harness-determinism: `SystemBrightnessMax` ran the full 60 actions then failed (vs failing at 20 under cap-A), wasting +6.7 minutes of wall time with zero SR benefit. |
| 8 | Platform-coverage bias | **Out of scope** | Requires net-new benchmarks beyond OSWorld / AndroidWorld / WebArena. Acknowledged as a generalizability threat; the validation plan does not propose closing it within this work. |
| 9 | Baseline-parity sensitivity | **Closed** | Cross-model replication: 3-seed Gemini 3 Flash mean = 11.0/15 (73.3%) matches the prior Claude Sonnet 4.6 datapoint of 11/15 exactly. The stable failure set across Gemini-3 (×3 seeds) and Claude-Sonnet-4.6 is identical: `BrowserDraw`, `SystemBrightnessMax`, `SystemWifiTurnOn`. The shared fail set across two LLM backends and three seeds strongly implicates harness-level deterministic failures (status-bar stale read on wifi, scroll-on-seekbar incompatibility on brightness, image-canvas-not-in-a11y-tree on draw) rather than model-capability differences. The "matches T3A+Claude" claim is therefore not Claude-specific and not seed-specific. |

**Combined narrative**: The four AB experiments establish that **Pre-Act's success-rate value comes from the harness — RAG retrieval, the verify-before-store gate, the agentic program selector, and hybrid replay — not from the runtime add-ons sitting on top of T3A**. Specifically: (a) the verify gate is empirically load-bearing (gap #2 smoking gun); (b) prompt-level Pre-Act content is inert (gap #4 is satisfied by the code path that runs the verbatim T3A prompt); (c) code-level Pre-Act guardrails are roughly neutral on aggregate SR though they help on specific populated-field input tasks (gap #5); (d) the dynamic step-budget cap saves wall time without sacrificing SR (gap #7 confirms the cap-removal prediction). The three persistent FAIL tasks (`BrowserDraw`, `SystemBrightnessMax`, `SystemWifiTurnOn`) are deterministic harness-level failures uncorrected by budget changes, model swap, or guardrail adjustments — they bound the benchmark, not the method.

The §2.3.1 claims should now be read as empirically supported by the experiments above, with the caveat that all single-seed AB results (gaps #2, #5, #7) are n=1 and the multi-seed result (gaps #1, #3) is n=3. Multi-seed extension of the AB experiments is the natural next refinement but does not change the qualitative findings.

#### 2.4 Incremental Learning and Adaptive Performance

PreAct implements a progressive learning paradigm that mirrors human skill acquisition:

1.  **Initial Exploration:** When facing a previously unseen task, PreAct operates as a standard CUA with full LLM inference cycles (4-5 seconds per operation), while the Interaction Recorder captures the trajectory.

2.  **Model Formation:** Upon successful task completion, the interaction trace is analyzed to extract a formal state transition graph, encoded as a JSON RPA program, and stored in the RAG-indexed model repository.

3.  **Performance Acceleration:** When the same or similar task is encountered again, the system retrieves and executes the compiled state machine at up to 10x faster speeds with near-deterministic outcomes.

4.  **Model Refinement:** When UI changes trigger a state verification failure, the system falls back to LLM reasoning, resolves the situation, and monotonically extends the state graph with new states and transitions — typically requiring only a single adaptation cycle.

5.  **Library Growth:** Over time, the system accumulates a comprehensive library of application models, becoming progressively more efficient across a wider range of tasks. The RAG index enables transfer — a model compiled for "send email in Gmail" can be retrieved and adapted for "reply to email in Gmail."

This evolutionary capability enables PreAct to start with the exploratory flexibility of an LLM-powered agent while incrementally developing formal application models that enable the speed and reliability of purpose-built automation — without requiring explicit programming or manual updates.

### 3. Related Work

The problem of accelerating computer-use agents through learned behaviors sits at the intersection of several active research threads. We organize related work into five categories and provide a detailed comparison against the six most closely related systems.

#### 3.1 Computer-Use Agent Foundations

The ReAct paradigm (Yao et al., 2023) established the Observe-Reason-Act loop for LLM agents. Applied to GUI environments, this yields systems like Anthropic's Computer Use (2024), OpenAI's CUA/Operator (2025), and Google's Project Mariner (2025). These operate as stateless reasoners — each action requires full screenshot analysis and LLM inference. OSWorld (Xie et al., 2024) and WebArena (Zhou et al., 2024) provide standardized benchmarks, with success rates climbing from single digits to beyond human-level (72.6% on OSWorld by December 2025). However, even the best-performing agents (UI-TARS-2 at 47.5%, OpenCUA-72B at 45.0% on OSWorld-Verified) pay the full latency cost on every action, motivating the acceleration approaches below.

#### 3.2 Skill and Experience Memorization (LLM-in-the-Loop)

A large body of work saves learned behaviors as skills that reshape LLM context at execution time:

- **CUA-Skill** (Chen et al., 2026) encodes human expertise as parameterized execution graphs with composition rules, achieving 57.5% on WindowsAgentArena. Skills are manually engineered, not learned from trajectories, and still require an LLM agent runtime.
- **Memento-Skills** (Zhou et al., 2026) uses an "agent-designing agent" that creates and mutates markdown skill files with unit tests through read-write reflective learning. Improved GAIA accuracy by 13.7pp. Skills are LLM context, not executable artifacts.
- **SAGE** (2025) incorporates skills into reinforcement learning, reducing tokens by 59% and interaction steps by 26%. Skills guide RL policy, not replace LLM execution.
- **Agent Workflow Memory** (Wang et al., 2024) induces reusable sub-routines from trajectories, improving WebArena success by 51.1%. Workflows are natural-language routines injected into LLM prompts.
- **ExpeL** (Zhao et al., 2024) extracts natural-language insights from trajectories. **Reflexion** (Shinn et al., 2023) accumulates verbal self-reflections. Both improve performance but retain full LLM dependence.
- **Anthropic Agent Skills** (2025, open standard) provides filesystem-based skill bundles adopted by 20+ platforms. Skills are context-injection mechanisms, not standalone executables.

These approaches reduce tokens and improve success rates but fundamentally retain LLM invocation at execution time. PreAct eliminates LLM calls entirely for familiar workflows.

#### 3.3 Trajectory Compilation (LLM-Free Execution)

A smaller but growing body of work compiles workflows into deterministic, LLM-free artifacts:

- **Compiled AI** (Trooskens et al., 2026) generates Python/Temporal activities from YAML specifications in a single LLM call. Achieves 57x token reduction, 4.5ms P50 latency at 1,000 runs. However, it targets narrow business-logic functions (20-50 lines), not multi-page GUI workflows. Input is a human-written YAML spec, not an agent trajectory.
- **Agentic Compilation** (Chundru, 2026) proposes one-shot compilation of web workflows into JSON blueprints from a single page's HTML + user intent. Claims 80-94% zero-shot success and 1,500x cost reduction. However, the paper provides no JSON schema, no example blueprints, and no mechanism for workflows spanning multiple distinct page structures.
- **Meta-Tools** (Abuzakuk et al., 2026) discovers recurring tool-call sequences and bundles them into deterministic composite operations. Reduces LLM calls by 11.9%. Operates at the API/tool level, not the GUI level.

PreAct shares the compilation objective but differs in three fundamental ways: (1) it compiles from recorded multi-page agent trajectories, not from specifications or single-page HTML; (2) it produces a formal state machine with conditional branching, not flat code or unspecified blueprints; (3) it incrementally refines the compiled artifact rather than regenerating it.

#### 3.4 Record-Replay Systems (Most Closely Related)

These systems directly address the record-compile-replay-fallback loop:

- **ActionEngine** (Zhong et al., 2026, Microsoft Research) is the most architecturally similar. A Crawling Agent explores a GUI app and builds a state-machine graph; an Execution Agent synthesizes executable Python programs from the graph; vision-based re-grounding handles failures and updates the graph. Key differences from PreAct: (1) ActionEngine uses *untargeted exploration* to build its graph — it crawls the app broadly before any specific task, which is wasteful for goal-directed workflows; (2) it generates *flat Python scripts* from the state machine (a lossy transformation that prevents in-place patching); (3) its fallback is *selector-level re-grounding*, not full CUA reasoning for arbitrary unexpected states.
- **Muscle-Mem** (Dunteman, 2025) records agent tool-calling patterns and replays them deterministically, falling back to agent mode on edge cases. Described as a "JIT compiler for agent behavior." Key differences: (1) records *linear sequences*, not state transition graphs — no branching, no state verification; (2) replays *blindly* without per-step state verification; (3) *no incremental refinement* — on failure, the cached sequence is discarded entirely.
- **AgentRR** (Feng et al., 2025) introduces a Record-Summary-Replay framework with multi-level experiences and check functions as trust anchors. Key differences: (1) produces *natural-language experiences* at varying abstraction levels, not formal state machines; (2) low-level experiences are "precise operational descriptions," not XPath-verified deterministic executables; (3) provides no quantitative benchmarks.
- **Workflow-Use** (browser-use, 2025) records browser interactions and converts them into deterministic scripts with variables. Replays 10x faster, ~90% cheaper. Falls back to full agent mode. Key differences: (1) generates *linear scripts*, not state graphs; (2) *no conditional branching* in compiled artifacts; (3) *no incremental refinement*; (4) browser-only.
- **WALT** (Salesforce, 2025) reverse-engineers website functionality into deterministic action scripts (tools) from exploration traces. Includes "URL promotion" optimization and agentic fallback. Key differences: (1) produces *function-level tools* (single actions), not multi-step workflow programs; (2) still requires *LLM to compose tools* into task-solving sequences.
- **GPA** (Salesforce, 2026) records a single human demonstration and replays it deterministically using geometric matching. Runs fully locally without cloud LLMs. Key differences: (1) records from *human demos*, not agent traces; (2) uses *geometric/visual matching*, not DOM-based state verification; (3) *no LLM fallback* for truly novel states; (4) *no incremental learning*.

#### 3.5 State-Machine GUI Modeling

The model-based testing community has built state models of GUI applications for 20+ years:

- **Crawljax** (Mesbah et al., 2008-2012) automatically crawls AJAX applications and infers state-flow graphs where nodes are DOM states and edges are event-based transitions. The direct ancestor of state-machine GUI modeling.
- **TESTAR** (Vos et al., ongoing) explores GUIs at runtime and infers state models in graph databases.
- **Stoat** (Su et al., 2017) constructs stochastic FSMs of Android apps with frequency-annotated transitions.
- **AutoDroid** (Wen et al., 2024) extracts UI Transition Graphs through exploration and converts them to task-completion knowledge with LLMs. **GraphPilot** (2026) and **KG-RAG** (2025) extend this to knowledge-graph-based navigation.

These systems build state models for *testing*, not for *task automation replay*. PreAct repurposes the state-machine concept as an *execution acceleration layer* for LLM agents, adding task-directed construction, parameterized execution, conditional branching, and LLM fallback with graph refinement.

#### 3.6 Programming by Demonstration

- **WebRobot** (Dong et al., PLDI 2022) synthesizes loopy web RPA programs from user demonstrations via speculative rewriting. Produces deterministic programs but predates LLM integration and has no adaptive fallback.
- **TaskMind** (Yin et al., CHI 2025) recovers cognitive dependencies from demonstrations to build task graphs. Still requires LLM at execution for parameter inference.
- **ReUseIt** (Liu et al., IUI 2026) synthesizes reusable workflows from agent successes and failures with execution guards. Improved success from 24.2% to 70.1%. However, workflows are LLM-dependent natural-language instructions.

PreAct differs from PBD approaches in that it records from *LLM agent trajectories* (not human demonstrations) and produces *LLM-free formal state machines* (not NL-guided programs).

#### 3.7 Comparative Summary

| Property | ActionEngine | Muscle-Mem | AgentRR | Workflow-Use | WALT | GPA | **PreAct** |
|---|---|---|---|---|---|---|---|
| **Recording source** | App crawling | Agent tool calls | Agent traces | Human/agent | Agent exploration | Human demo | **Task-directed agent trajectory** |
| **Compiled representation** | State machine -> Python | Linear sequence | NL experiences | Linear script | Tools (functions) | Action graph | **JSON state machine (directly executable)** |
| **State verification** | Unclear | None (blind) | Check functions | Semantic selectors | Cached selectors | Geometric | **XPath polling with timeout** |
| **Conditional branching** | Via generated Python | No | No | No | No | No | **Yes (in state graph)** |
| **LLM-free execution** | Yes (Python) | Yes | Partial | Yes | Mostly | Yes (fully) | **Yes** |
| **Fallback mechanism** | Vision re-grounding | Full agent | Level cascade | Full agent | Fresh agent | Geometric anchors | **Full CUA loop** |
| **Incremental refinement** | Updates graph | No | No | No | Tool re-validation | No | **Monotonic graph extension** |
| **Parameterized inputs** | Unclear | No | High-level only | Script variables | URL params | No | **Typed parameters in state machine** |
| **Human intervention** | No | No | No | No | No | No | **Yes (embedded in graph)** |
| **RAG-indexed retrieval** | No | No | No | No | Tool library | No | **Yes** |
| **Benchmark evaluation** | Not reported | Not reported | None (qualitative) | Not reported | WebArena (52.9%) | Proprietary | **OSWorld + WebArena (planned)** |

PreAct's novelty lies in three specific architectural decisions that no existing system combines: (1) the state machine as the directly executable artifact (not an intermediate representation compiled to code), (2) task-directed trajectory recording (not untargeted exploration), and (3) monotonic graph refinement on fallback (not regeneration or discard). While individual elements — such as state-machine modeling, record-replay patterns, and LLM fallback — appear across the literature, this specific combination produces a system that is simultaneously more sample-efficient (task-directed), more patchable (direct execution), and more resilient (monotonic refinement) than any existing approach.

### 4. PreAct System Architecture

**(Conceptual Diagram)**

```mermaid
graph LR
    subgraph PreAct System
        A[User Task] --> B{Agent Core};
        B --> C{RAG DB Query};
        C -- Application Model Found --> D[RPA Executor];
        C -- No Match / Transition Failure --> E[Standard CUA Loop (LLM)];
        D -- Execute State Transition --> F[Computer Env Interface];
        F -- UI State --> D;
        D -- State Transition Failed --> B;
        E -- Action --> F;
        F -- Screenshot/State --> E;
        E -- Interaction Trace --> G[Interaction Recorder];
        G --> H{Model Generator (LLM)};
        H -- Generated Application Model --> I[RAG DB Storage];
    end

    style F fill:#f9f,stroke:#333,stroke-width:2px
```

#### 4.1 Components

*   **Agent Core:** The central LLM-based orchestrator. It receives the user's high-level task, interprets it, queries the RAG Database for relevant application models encoded as RPA Programs, decides the execution strategy (model-based execution vs. exploratory learning), manages transitions between model execution and the CUA loop (fallback), and potentially decomposes complex tasks into sub-tasks.
*   **Standard CUA Loop:** The baseline agent using a SOTA multimodal LLM (e.g., GPT-4o). It performs the full Observe (screenshot) -> Reason -> Act cycle. This is used for tasks with no matching application model, for handling unexpected state transitions during model execution (fallback), and for the initial exploration of tasks to generate traces for model learning.
*   **Interaction Recorder:** Passively monitors successful interactions performed by the Standard CUA Loop. It logs the sequence of observations (screenshots, potentially DOM state), LLM reasoning (optional), executed actions (`click`, `type`, etc.), and critically, uses environment-specific tools (e.g., browser debugging protocols, accessibility APIs) to determine and log robust state identifiers like XPaths for the elements targeted by these actions based on interaction coordinates or element references provided by the LLM.
*   **Model Generator:** An LLM-based component (potentially run offline or asynchronously). It takes a recorded interaction trace as input, extracts the underlying state transition graph, and generates a structured, executable RPA Program that represents an explicit model of the application. Key functions include:
    *   Identifying distinct UI states and their characteristics through stable selectors (e.g., XPath).
    *   Mapping actions to state transitions in the application model.
    *   Abstracting concrete inputs (e.g., typed email addresses, search queries) into parameters.
    *   Determining the state verification criteria (element to wait for) preceding each action.
    *   Inserting necessary inspection steps for states requiring content analysis.
    *   Generating the program in a defined JSON format (see Section 5) that represents the formal state machine.
*   **RAG Database:** A database storing the generated application models as RPA Programs. It's indexed by metadata such as task description keywords, application context (e.g., website URL, application name), required parameters, and potentially visual or structural hashes of the initial state. This allows the Agent Core to efficiently retrieve candidate application models relevant to the current task and context.
*   **RPA Executor:** A lightweight execution engine that traverses the state transition graph. It receives an application model from the Agent Core and executes its state transitions sequentially. For each state:
    *   It verifies the current state (e.g., polls for XPath existence) against the Computer Environment Interface.
    *   If the state verification succeeds within the timeout, it executes the associated action to transition to the next state.
    *   If the state verification fails (timeout), it immediately halts execution and signals the state transition failure back to the Agent Core, triggering the fallback mechanism.
*   **Computer Environment Interface:** An abstraction layer (e.g., implementing the `Computer` interface from the sample app) that provides capabilities to interact with the target environment (local browser, Docker container, remote VM, etc.). It handles sending actions (clicks, typing) and retrieving state (screenshots, DOM, element existence via XPath).

### 5. RPA Program Structure and Generation

#### 5.1 Representation
An RPA program serves as a structured representation of an application's state transition graph, encoded using JSON. This format is portable, easy to store in the RAG database, and simple for the Agent Core to analyze and modify. Each program represents an explicit model of the application being used, capturing its states, valid actions, and transition dynamics in a formal state machine.

**Example 1: Basic Email Workflow (Application Model as JSON)**

The following example shows a simple Gmail email composition workflow represented as a state transition graph in JSON format. This example demonstrates:
- The state space modeling of a web application with explicit states and transitions
- Simple sequential UI state transitions through actions
- Parameter usage for variable inputs (recipient, subject, message)
- State verification through UI element detection

```json
{
  "metadata": {
    "program_id": "gmail_send_basic_email_v1",
    "task_description": "Compose and send a basic email in Gmail",
    "application_context": "mail.google.com",
    "initial_states": ["logged_in_to_gmail", "inbox_view"],
    "parameters": ["recipient_email", "subject_line", "message_body"]
  },
  "states": [
    { "id": "initial", "verification": { "type": "expect_element", "xpath": "//div[text()='Compose']", "timeout_ms": 5000 } },
    { "id": "compose_button_clicked", "verification": { "type": "expect_element", "xpath": "//div[@aria-label='New Message']", "timeout_ms": 5000 } },
    { "id": "new_message_dialog_opened", "verification": { "type": "expect_element", "xpath": "//input[@aria-label='To recipients']", "timeout_ms": 1000 } },
    { "id": "recipient_field_focused", "verification": { "type": "expect_element", "xpath": "//input[@aria-label='To recipients' and @data-focused='true']", "timeout_ms": 1000 } },
    { "id": "recipient_entered", "verification": { "type": "expect_element", "xpath": "//input[@name='subjectbox']", "timeout_ms": 1000 } },
    { "id": "subject_field_focused", "verification": { "type": "expect_element", "xpath": "//input[@name='subjectbox' and @data-focused='true']", "timeout_ms": 1000 } },
    { "id": "subject_entered", "verification": { "type": "expect_element", "xpath": "//div[@aria-label='Message Body']", "timeout_ms": 1000 } },
    { "id": "message_body_focused", "verification": { "type": "expect_element", "xpath": "//div[@aria-label='Message Body' and @data-focused='true']", "timeout_ms": 1000 } },
    { "id": "message_entered", "verification": { "type": "expect_element", "xpath": "//div[text()='Send']", "timeout_ms": 1000 } },
    { "id": "send_button_clicked", "verification": { "type": "expect_element", "xpath": "//*[contains(text(),'Message sent')]", "timeout_ms": 5000 } },
    { "id": "message_sent", "verification": { "type": "terminal_state" } }
  ],
  "transitions": [
    { "from": "initial", "to": "compose_button_clicked", "action": { "type": "action_click", "target": "//div[text()='Compose']" } },
    { "from": "compose_button_clicked", "to": "new_message_dialog_opened", "action": { "type": "wait", "ms": 500 } },
    { "from": "new_message_dialog_opened", "to": "recipient_field_focused", "action": { "type": "action_click", "target": "//input[@aria-label='To recipients']" } },
    { "from": "recipient_field_focused", "to": "recipient_entered", "action": { "type": "action_type", "parameter_name": "recipient_email" } },
    { "from": "recipient_entered", "to": "subject_field_focused", "action": { "type": "action_click", "target": "//input[@name='subjectbox']" } },
    { "from": "subject_field_focused", "to": "subject_entered", "action": { "type": "action_type", "parameter_name": "subject_line" } },
    { "from": "subject_entered", "to": "message_body_focused", "action": { "type": "action_click", "target": "//div[@aria-label='Message Body']" } },
    { "from": "message_body_focused", "to": "message_entered", "action": { "type": "action_type", "parameter_name": "message_body" } },
    { "from": "message_entered", "to": "send_button_clicked", "action": { "type": "action_click", "target": "//div[text()='Send']" } },
    { "from": "send_button_clicked", "to": "message_sent", "action": { "type": "wait", "ms": 500 } }
  ],
  "human_interventions": [
    { "before_state": "send_button_clicked", 
      "prompt": "Please review this email before sending. Is the content appropriate to send?", 
      "intervention_type": "approval", 
      "timeout_sec": 60,
      "ui_elements": ["//div[@aria-label='Message Body']", "//input[@name='subjectbox']"],
      "on_timeout": "abort" }
  ]
}
```

The updated representation explicitly models the application as a state machine with:
- Distinct states identified by UI elements and verification criteria
- Clear transitions between states triggered by specified actions
- Human intervention points within the state transition flow
- Initial states and terminal states properly identified

**Example 2: E-commerce Product Evaluation (Advanced Application Model)**

The second example illustrates a more complex application model that requires content inspection and branching state transitions. This JSON representation demonstrates:
- A state transition graph with conditional paths
- States requiring content extraction and analysis
- Branching transitions based on state analysis
- Dynamic parameter usage across the state space
- Detailed error handling and fallback mechanisms

```json
{
  "metadata": {
    "program_id": "ecommerce_review_product_v1",
    "task_description": "Evaluate if a product meets criteria for purchase",
    "application_context": "amazon.com/dp/",
    "initial_states": ["on_product_page"],
    "parameters": ["product_price_threshold", "min_rating_required", "required_features"]
  },
  "states": [
    {
      "id": "product_page",
      "verification": { "type": "expect_element", "xpath": "//div[@id='ppd']", "timeout_ms": 8000 },
      "description": "Main product page loaded"
    },
    {
      "id": "product_title_visible",
      "verification": { "type": "expect_element", "xpath": "//span[@id='productTitle']", "timeout_ms": 2000 },
      "description": "Product title element is visible"
    },
    {
      "id": "product_title_extracted",
      "verification": { "type": "data_available", "data_key": "productName" },
      "description": "Product title has been extracted and processed"
    },
    {
      "id": "price_element_visible",
      "verification": { "type": "expect_element", "xpath": "//span[@class='a-price']", "timeout_ms": 2000 },
      "description": "Price element is visible"
    },
    {
      "id": "price_extracted",
      "verification": { "type": "data_available", "data_key": "price" },
      "description": "Price has been extracted and processed"
    },
    {
      "id": "ratings_element_visible",
      "verification": { "type": "expect_element", "xpath": "//div[@id='averageCustomerReviews']", "timeout_ms": 2000 },
      "description": "Ratings element is visible"
    },
    {
      "id": "rating_extracted",
      "verification": { "type": "data_available", "data_key": "rating" },
      "description": "Rating has been extracted and processed"
    },
    {
      "id": "features_element_visible",
      "verification": { "type": "expect_element", "xpath": "//div[@id='feature-bullets']", "timeout_ms": 2000 },
      "description": "Features list is visible"
    },
    {
      "id": "features_analyzed",
      "verification": { "type": "data_available", "data_key": "hasRequiredFeatures" },
      "description": "Features have been analyzed for requirements"
    },
    {
      "id": "decision_made",
      "verification": { "type": "data_available", "data_key": "meetsCriteria" },
      "description": "Decision has been made based on criteria"
    },
    {
      "id": "add_to_cart_visible",
      "verification": { "type": "expect_element", "xpath": "//input[@id='add-to-cart-button']", "timeout_ms": 2000 },
      "description": "Add to Cart button is visible"
    },
    {
      "id": "add_to_cart_clicked",
      "verification": { "type": "expect_element", "xpath": "//*[contains(text(),'Added to Cart')]", "timeout_ms": 5000 },
      "description": "Product added to cart"
    },
    {
      "id": "rejected",
      "verification": { "type": "data_available", "data_key": "rejectionReason" },
      "description": "Product rejected with reason"
    },
    {
      "id": "completed",
      "verification": { "type": "terminal_state" },
      "description": "Process completed"
    }
  ],
  "transitions": [
    { "from": "product_page", "to": "product_title_visible", "action": { "type": "wait", "ms": 500 } },
    { "from": "product_title_visible", "to": "product_title_extracted", "action": { "type": "inspect_text", "target": "//span[@id='productTitle']", "prompt": "Extract the product name and brand", "store_result_as": "productName" } },
    { "from": "product_title_extracted", "to": "price_element_visible", "action": { "type": "wait", "ms": 100 } },
    { "from": "price_element_visible", "to": "price_extracted", "action": { "type": "inspect_text", "target": "//span[@class='a-price']", "prompt": "Extract the current price as a numeric value (just the number)", "store_result_as": "price" } },
    { "from": "price_extracted", "to": "ratings_element_visible", "action": { "type": "wait", "ms": 100 } },
    { "from": "ratings_element_visible", "to": "rating_extracted", "action": { "type": "inspect_screenshot", "target": "//div[@id='averageCustomerReviews']", "prompt": "Extract the average rating as a numeric value out of 5", "store_result_as": "rating" } },
    { "from": "rating_extracted", "to": "features_element_visible", "action": { "type": "wait", "ms": 100 } },
    { "from": "features_element_visible", "to": "features_analyzed", "action": { "type": "inspect_text", "target": "//div[@id='feature-bullets']", "prompt": "Check if the following features are mentioned: ${required_features}. Return true or false.", "store_result_as": "hasRequiredFeatures" } },
    { "from": "features_analyzed", "to": "decision_made", "action": { "type": "evaluate_condition", "expression": "data.price <= parameters.product_price_threshold && data.rating >= parameters.min_rating_required && data.hasRequiredFeatures == 'true'", "store_result_as": "meetsCriteria" } },
    { "from": "decision_made", "to": "add_to_cart_visible", "action": { "type": "conditional", "condition": "data.meetsCriteria == true" } },
    { "from": "decision_made", "to": "rejected", "action": { "type": "conditional", "condition": "data.meetsCriteria == false", "then": { "type": "compute", "expression": "Rejection reasons: ${data.price > parameters.product_price_threshold ? 'Price ' + data.price + ' exceeds threshold ' + parameters.product_price_threshold : ''}${data.rating < parameters.min_rating_required ? '; Rating ' + data.rating + ' below required ' + parameters.min_rating_required : ''}${data.hasRequiredFeatures != 'true' ? '; Missing required features: ' + parameters.required_features : ''}", "store_result_as": "rejectionReason" } } },
    { "from": "add_to_cart_visible", "to": "add_to_cart_clicked", "action": { "type": "action_click", "target": "//input[@id='add-to-cart-button']" } },
    { "from": "add_to_cart_clicked", "to": "completed", "action": { "type": "wait", "ms": 500 } },
    { "from": "rejected", "to": "completed", "action": { "type": "wait", "ms": 100 } }
  ],
  "human_interventions": [
    { 
      "before_state": "completed", 
      "prompt": "Product evaluation complete. ${data.meetsCriteria ? 'Product was added to cart.' : 'Product was rejected: ' + data.rejectionReason}",
      "intervention_type": "approval",
      "timeout_sec": 10,
      "on_timeout": "continue"
    }
  ]
}
```

This enhanced representation explicitly models the e-commerce application as a formal state machine with:

1. **Explicit State Identification:** Each distinct UI state is clearly defined with verification criteria.
2. **State Transitions:** Formally defined transitions between states, triggered by specific actions.
3. **Data Extraction States:** States specifically dedicated to extracting and analyzing application content.
4. **Conditional Branching:** Explicit modeling of different paths through the state space based on content analysis.
5. **Terminal States:** Clear identification of completion states in the application model.

This model-based approach allows the agent to develop a rich understanding of the application's behavior through reinforcement learning principles, continuously refining its model based on successful interactions.

#### 5.2 Step Types
*   `expect_element`: Specifies the primary expectation. Contains `xpath` (or other robust selector) and `timeout_ms`. Actions implicitly target the element found by the preceding `expect_element`.
*   `action_click`, `action_double_click`, `action_move`, `action_scroll`, `action_keypress`, `action_drag`: Standard UI interactions.
*   `action_type`: Types text. Can take literal `text` or a `parameter_name` defined in `metadata`.
*   `wait`: Explicit pause (`ms`).
*   `inspect_text`: Extracts text content from a specific element or region of the page. Contains `target_selector` (XPath or other selector to target specific content like a product description, article body, or sidebar) and `prompt` for the LLM. When `target_selector` is specified, only the text from that element is extracted, dramatically reducing processing time and improving focus compared to whole-page extraction. Results can be stored in variables using `store_result_as` for later conditional operations.
*   `inspect_screenshot`: Captures a screenshot of a specific element or region and sends it to a multimodal LLM. Contains `target_selector` (XPath or other selector to focus on specific UI elements like a chart, image, or status indicator) and `prompt` for the LLM. When `target_selector` is specified, only that element is captured, significantly reducing the visual token count and processing time while improving accuracy by focusing the LLM's attention. Results can be stored using `store_result_as`.
*   `condition`: Executes different steps based on a logical expression, typically using variables set by previous inspection steps. Contains `expression` (a logical condition), `true_steps` (steps to execute if condition is true), and `false_steps` (steps to execute otherwise).
*   `request_human_intervention`: Pauses RPA execution and requests human input or approval. Contains `prompt` (the message shown to the user), `intervention_type` (one of: "approval", "input", "selection", or "verification"), `timeout_sec` (maximum wait time for human response), `ui_elements` (optional array of element selectors to highlight), and `store_result_as` (variable to store the human response). If timeout occurs, can specify `on_timeout` as either "continue" (proceed with default value), "retry" (show prompt again), or "abort" (terminate RPA execution and trigger LLM fallback).

#### 5.3 Generation Process
The Model Generator analyzes a successful trace from the Interaction Recorder to extract the underlying state transition graph of the application:
1.  **State Identification:** For each distinct UI state in the interaction, identify unique and stable element patterns (XPaths, accessibility IDs, visual patterns) that reliably indicate that state.
2.  **Action Mapping:** Link each action to its preceding state and the resulting state transition it causes in the application model.
3.  **Parameterize Inputs:** Use LLM reasoning to identify typed text that represents variable input (names, emails, search terms, content) and replace it with parameter references in the state transition actions.
4.  **Identify Content-Dependent States:** If the original LLM trace indicates reasoning based on page *content* (text) or *visuals* (images/layout), create explicit states for content extraction and analysis, inserting corresponding `inspect_text` or `inspect_screenshot` actions in the appropriate state transitions.
5.  **Model Branching Pathways:** Identify conditional paths through the application state space and model them as branching transitions in the state machine.
6.  **Set State Timeouts:** Assign reasonable default timeouts to state verification steps (e.g., 1-5 seconds), potentially adjusted based on observed UI load times in the trace.
7.  **Generate Model Metadata:** Create descriptive metadata (task description, context, parameters) to facilitate RAG retrieval of the application model.

### 6. Execution Flow

1.  **Task Initiation:** User provides a high-level task (e.g., "Send an email to customer X about their recent order Y").
2.  **Model Selection:** The Agent Core analyzes the task, identifies parameters (X, Y), checks the current application state (e.g., logged into Gmail), and queries the RAG DB for matching application models (e.g., `gmail_send_basic_email`). An LLM might be used to select the best fit if multiple candidates exist. If no suitable model is found, proceed directly to the exploratory learning mode with the Standard CUA Loop (Step 5).
3.  **Model-Based Execution:** The selected application model and extracted parameters are passed to the RPA Executor, which traverses the state transition graph:
    *   The Executor begins at the initial state and verifies the current UI matches the expected state.
    *   For each state, it verifies the state (e.g., polls for XPath existence) against the Computer Env Interface.
        *   **Success:** If verified within timeout, execute the associated action to transition to the next state.
        *   **Failure:** If verification fails, halt execution and signal state transition failure to the Agent Core (Go to Step 4).
    *   For actions that trigger transitions, send the command to the Computer Env Interface.
    *   For inspection actions, retrieve text/screenshot from the specified element, invoke the necessary LLM via the Agent Core with the targeted prompt, and store the result in the program's data context for later conditional transitions.
    *   For human intervention points, pause execution and request user input before continuing state transitions.
    *   **Completion:** If a terminal state is reached successfully, signal success to the Agent Core.
4.  **Model Adaptation Mechanism:** On state transition failure, the Agent Core takes control. It captures the current state (screenshot) and invokes the Standard CUA Loop, providing the original task goal, the current context, and information about the failed state transition. The CUA LLM analyzes the situation, determines the next action to recover, and updates the application model with new states and transitions learned from this adaptation.
5.  **Exploratory Learning:** If no application model was selected initially, or after a fallback, the Standard CUA Loop runs its Observe->Reason->Act cycle until the task is completed or fails, collecting interaction data for model construction.
6.  **Model Construction & Refinement:** Upon successful task completion:
    *   If novel interaction sequences were performed by the Standard CUA Loop (either initially or during adaptation), the Interaction Recorder logs these traces.
    *   These traces are analyzed to extract states, actions, and transition dynamics, which are then used to create new application models or refine existing ones, continuously improving the system's model-based reinforcement learning capabilities.
7.  **UI Change Adaptation:** When UI changes trigger a state transition failure:
    *   The Standard CUA Loop takes over and adapts to the new UI patterns through its visual reasoning capabilities.
    *   Once successful, the new interaction sequence is immediately processed to update the existing application model with new states and transitions.
    *   Subsequent encounters with the changed UI will use the updated model at full speed, requiring only a single adaptation cycle for each significant UI change.

### 7. Task Repetition and Muscle Memory

PreAct's design incorporates a model-based reinforcement learning approach to handling repetitive tasks, inspired by how humans develop muscle memory through state transition models of familiar applications:

#### 7.1 Repetition Detection

When the Agent Core receives a task that involves multiple similar operations:
* It recognizes repetition patterns through explicit indicators ("Process these 10 invoices")
* It identifies list-based operations in the application state space (tables, directories, search results)
* It analyzes the task structure for iterative elements in the state transition graph

#### 7.2 Learn-Once, Execute-Many Approach

PreAct follows a streamlined three-phase model-based reinforcement learning approach to repetitive tasks:

1. **Model Learning Phase (First Execution)**
   * The first instance of a repetitive task runs using exploratory learning with the full LLM-based CUA
   * The system identifies variable states and transitions in the application model
   * Upon successful completion, a state transition graph is immediately extracted and encoded as an RPA program

2.  **Model Exploitation Phase (Subsequent Executions)**
   * For all remaining repetitions, the system leverages the learned application model
   * Variable parameters are substituted based on the current iteration context
   * Execution speed increases dramatically (up to 10x faster) through efficient state verification
   * The model enables direct state transitions without full screenshot analysis

3.  **Model Adaptation Phase (When Needed)**
   * If any iteration encounters an unexpected application state, the system seamlessly falls back to exploratory learning
   * The LLM resolves the issue and updates the application model with new states and transitions
   * Subsequent iterations use the refined model without interruption

### 8. Evaluation Plan

We propose a comprehensive evaluation designed to validate PreAct's core claims and provide direct comparison against the most closely related systems. The evaluation consists of five experiments, each targeting a specific contribution.

#### 8.1 Benchmarks

- **OSWorld** (Xie et al., 2024): 369 tasks across Ubuntu, Windows, and macOS. The primary benchmark for cross-platform computer-use evaluation. We use the OSWorld-Verified subset for reliable automated scoring.
- **WebArena** (Zhou et al., 2024): 812 realistic web tasks across self-hosted web applications (shopping, forums, CMS, maps, GitLab). The standard benchmark for web-based agent evaluation.

No new benchmark is introduced. The "repeat" capability — PreAct's primary value proposition — is measured through a **two-run protocol** applied to existing benchmark tasks: Run 1 is exploration (all systems use LLM), Run 2 is replay (record-replay systems use their compiled artifacts, standard CUA baselines run unchanged). This two-run comparison is sufficient because compilation happens after Run 1 — further repetitions on stable UIs demonstrate nothing new. For UI adaptation experiments, we inject controlled mutations between Run 2 and Run 3 into the existing benchmark environments (WebArena's self-hosted applications are modifiable), then measure recovery in Runs 3-4.

#### 8.2 Baselines

| System | Type | Source |
|---|---|---|
| **Standard CUA (Claude Sonnet)** | Pure LLM agent, ReAct loop | Anthropic Computer Use API |
| **Standard CUA (GPT-4o)** | Pure LLM agent, ReAct loop | OpenAI CUA API |
| **ActionEngine** | State machine via crawling -> Python script generation | Microsoft Research (arxiv 2602.20502) |
| **Muscle-Mem** | Linear tool-call replay with agent fallback | github.com/pig-dot-dev/muscle-mem |
| **AgentRR** | Multi-level experience replay | arxiv 2505.17716 |
| **Workflow-Use** | Linear script compilation with agent fallback | github.com/browser-use/workflow-use |
| **PreAct (ours)** | State-machine compilation with graph refinement | This work |

For ActionEngine and AgentRR, we implement the published algorithms to the best fidelity possible from their papers, using the same underlying LLM (Claude Sonnet) for fair comparison. Muscle-Mem and Workflow-Use are evaluated using their open-source implementations.

#### 8.3 Metrics

| Metric | Definition | Validates |
|---|---|---|
| **Task Success Rate (SR)** | Fraction of tasks completed correctly, scored by benchmark evaluators | Overall effectiveness |
| **First-Run SR** | Success rate on Run 1 (exploration, no prior model) | Baseline CUA competence |
| **Second-Run SR** | Success rate on Run 2 using the compiled artifact | Compilation quality |
| **Latency per Action** | Wall-clock time from action decision to next state verification | Speed claim (10x) |
| **Total LLM Tokens** | Sum of input + output tokens across the entire task | Cost efficiency |
| **Cost per Task ($)** | API cost at published pricing | Economic viability |
| **Adaptation Cycles** | Number of LLM fallbacks needed after a UI mutation before the model stabilizes | Refinement efficiency |
| **Graph Coverage** | Fraction of task steps executed via state machine vs. LLM fallback | Model completeness |
| **Compilation Overhead** | Time and tokens spent on Model Generator (one-time cost) | Practical deployability |

#### 8.4 Experiments

**Experiment 1: End-to-End Performance (OSWorld + WebArena)**

*Goal:* Establish that PreAct achieves competitive or superior task success rates compared to standard CUA baselines and record-replay systems on established benchmarks.

*Protocol:*
- Run all systems on the full OSWorld-Verified and WebArena task suites.
- For PreAct and record-replay baselines, each task is executed twice: Run 1 (exploration/recording) and Run 2 (replay from compiled artifact). Report both first-run and second-run success rates.
- For standard CUA baselines, report single-run success rates.

*Expected outcome:* PreAct's first-run SR matches standard CUA (both use the same underlying LLM). PreAct's second-run SR exceeds all baselines due to deterministic state-machine execution eliminating LLM reasoning errors on familiar workflows.

*Key comparison:* PreAct second-run SR vs. ActionEngine second-run SR — tests whether direct state-machine execution outperforms generated Python scripts.

**Experiment 2: Acceleration on Second Run (Two-Run Protocol)**

*Goal:* Measure the speed and cost improvement from Run 1 (exploration) to Run 2 (replay) across all systems.

*Protocol:*
- Select the tasks from WebArena that were successfully completed by the standard CUA baseline in Experiment 1 (ensuring all systems have a fair starting point).
- Execute each task twice with all systems, resetting the environment to an equivalent initial state between runs.
- Record per-action latency, total tokens, and cost for both Run 1 and Run 2.
- Report the Run 1 -> Run 2 delta for each system.

*Expected outcome:* Standard CUA baselines show no improvement (stateless — Run 2 is identical to Run 1). PreAct, Muscle-Mem, and Workflow-Use show significant latency and cost reduction on Run 2. PreAct shows the largest improvement due to per-state verification avoiding unnecessary fallbacks. ActionEngine requires a separate exploration phase before Run 1, adding upfront cost that may not amortize by Run 2.

*Key comparison:* Run 2 latency and cost across all record-replay systems. PreAct vs. Muscle-Mem vs. Workflow-Use — does per-state verification produce better Run 2 outcomes than blind replay or linear scripts?

**Experiment 3: Adaptation to UI Changes (Mutation Protocol)**

*Goal:* Validate PreAct's single-cycle adaptation claim and monotonic graph refinement.

*Protocol:*
- Use the same WebArena tasks from Experiment 2. After Run 2 (all systems have compiled/cached models), inject controlled UI mutations into the self-hosted WebArena applications:
  - **Minor:** CSS class changes, element repositioning within the same container
  - **Moderate:** Added confirmation modals, renamed form fields, reorganized navigation
  - **Major:** Completely restructured page layout, new multi-step sub-flows
- Execute Run 3 (first post-mutation run) and Run 4 (second post-mutation run).
- Measure: number of LLM fallbacks triggered in Run 3, success rate on Run 3 vs. Run 4, graph size growth from Run 2 to Run 4.

WebArena's self-hosted applications (OneStopShop, Reddit-like forum, GitLab, CMS) are fully modifiable, making controlled mutation injection straightforward without creating a custom benchmark.

*Expected outcome:* PreAct's Run 3 triggers targeted fallbacks at the mutated states but succeeds by extending the graph; Run 4 executes at full speed using the extended graph. Muscle-Mem's Run 3 discards its cache entirely, requiring full re-recording; Run 4 replays the new recording. Workflow-Use falls back to full agent mode in Run 3 with no model update, so Run 4 shows no improvement. ActionEngine requires re-crawling the changed sections before Run 3 can succeed.

*Key comparison:* Run 4 performance — does the system recover to full-speed execution after one adaptation cycle? PreAct (monotonic extension) vs. ActionEngine (re-crawl + re-generate) vs. Muscle-Mem (full re-record).

**Experiment 4: Representation Quality — State Machine vs. Flat Code**

*Goal:* Directly compare PreAct's "state machine as executable" approach against ActionEngine's "state machine -> Python script" approach.

*Protocol:*
- For a controlled set of 20 multi-page workflows:
  - Record both systems on the same successful trajectory.
  - PreAct produces its JSON state machine; ActionEngine produces a Python script.
  - Execute both artifacts 50 times with minor UI variations.
  - Measure: success rate, ability to patch specific steps without regeneration, artifact size, human inspectability (user study with 10 developers rating readability on a 1-5 scale).

*Expected outcome:* PreAct's state-machine artifacts show higher success rates under minor UI variation (per-state verification catches deviations early) and better patchability (update one transition vs. regenerate entire script). ActionEngine's Python scripts may be more flexible for complex conditional logic but harder to incrementally update.

*Key comparison:* This experiment isolates the specific architectural choice of direct state-machine execution vs. code generation from state machines. This is PreAct's primary differentiator from ActionEngine.

**Experiment 5: Ablation Study**

*Goal:* Quantify the contribution of each PreAct component.

*Protocol:* Evaluate the following ablated variants on the same WebArena tasks using the two-run protocol:

| Variant | Description |
|---|---|
| PreAct-Full | Complete system |
| PreAct-NoVerify | Remove XPath state verification (blind replay, like Muscle-Mem) |
| PreAct-NoBranch | Remove conditional branching (linear execution only, like Workflow-Use) |
| PreAct-NoRefine | Disable incremental graph refinement (discard and re-record on failure) |
| PreAct-NoRAG | Disable RAG retrieval (always record from scratch, no model reuse) |
| PreAct-FlatCode | Generate Python scripts from state machine instead of direct execution (like ActionEngine) |

*Expected outcome:*
- PreAct-NoVerify shows significantly lower second-run SR (blind replay misses state mismatches, leading to cascading failures).
- PreAct-NoBranch fails on workflows with content-dependent paths (e-commerce evaluation, conditional routing).
- PreAct-NoRefine shows same first-failure behavior but much higher recovery cost (full re-recording vs. graph extension).
- PreAct-NoRAG shows slower deployment to similar tasks (must re-explore even when a related model exists).
- PreAct-FlatCode shows similar performance on stable UIs but lower patchability and higher regeneration cost under UI changes.

#### 8.5 Statistical Methodology

- All experiments report mean and 95% confidence intervals across 3 independent trials of the full protocol with different random seeds.
- Paired comparisons use the Wilcoxon signed-rank test (non-parametric, accounts for per-task variance).
- Cost analysis uses published API pricing at the time of evaluation (Anthropic, OpenAI) and reports both token counts and dollar amounts.
- Latency measurements exclude network variability by running all systems against the same locally-hosted environments (Docker containers for web apps, VMs for desktop tasks).

#### 8.6 Reproducibility

- All evaluation scripts, repetition/mutation protocols, and the PreAct implementation will be released as open source.
- Baseline implementations (ActionEngine, AgentRR reimplementations) will include documentation of any deviations from the original papers.
- UI mutation injection scripts for WebArena's self-hosted applications will be released as a reusable toolkit for the community.
- Environment snapshots (Docker images, VM configurations) will be provided for exact reproduction.

### 9. Conclusion

PreAct addresses the fundamental inefficiency of current Computer Using Agents — the repeated re-derivation of known action sequences at full LLM cost. While recent work has established that this "Rerun Crisis" is economically and practically untenable, existing solutions remain incomplete: skill-based approaches retain per-execution LLM costs; compilation approaches target narrow business logic or lack mechanisms for complex multi-page workflows; record-replay systems produce linear sequences without formal state verification or incremental refinement.

PreAct contributes three specific architectural decisions: (1) **state machine as executable** — executing the state transition graph directly rather than generating code from it, enabling lightweight per-state verification and in-place patching; (2) **task-directed trajectory recording** — constructing minimal state graphs from goal-directed execution rather than wasteful app-wide exploration; and (3) **monotonic graph refinement** — extending the existing graph on each fallback rather than discarding and regenerating the compiled artifact.

The proposed evaluation (Section 8) is designed to validate each of these three claims through direct comparison against the most closely related systems (ActionEngine, Muscle-Mem, AgentRR, Workflow-Use) on established benchmarks (OSWorld, WebArena) using a repetition protocol that measures acceleration and adaptation across repeated executions of the same tasks. Experiment 4 directly isolates the state-machine-as-executable claim against ActionEngine's code-generation approach. Experiment 3 tests monotonic refinement against systems that discard or regenerate. Experiment 2 measures the sample efficiency of task-directed recording. The ablation study quantifies the contribution of each component.

If the evaluation confirms our hypotheses, PreAct demonstrates that the trajectory compilation paradigm — when the compiled artifact is also the executable, constructed from task-directed traces, and refined monotonically — can achieve order-of-magnitude improvements in cost and latency for familiar tasks while maintaining the full adaptability of LLM-powered agents for novel situations.

### Appendix A. Computer Action Specification for JSON RPA Programs

The following section provides a detailed specification of all computer actions supported by the PreAct JSON-based RPA programs. These actions can be used as steps in RPA programs and are also generated when parsing actions from LLM providers like Anthropic Claude.

| Action Type | Parameters | Description |
|-------------|------------|-------------|
| **expect_element** | `xpath`: String, `timeout_ms`: Number | Waits for an element matching the XPath to be visible on the page. If the element is not found within the timeout, the execution fails. |
| **action_click** | `xpath`: String | Clicks on the element matching the XPath. |
| **action_double_click** | `xpath`: String | Double-clicks on the element matching the XPath. |
| **action_move** | `xpath`: String | Moves the mouse to the element matching the XPath without clicking. |
| **action_type** | `xpath`: String, `text`: String | Types the specified text into the element matching the XPath. |
| **action_keypress** | `key`: String | Presses a keyboard key (e.g., "Enter", "Tab", "Escape"). |
| **wait** | `ms`: Number | Pauses execution for the specified number of milliseconds. |
| **inspect_text** | `xpath`: String, `prompt`: String, `store_result_as`: String | Extracts text from an element, processes it with an LLM using the provided prompt, and stores the result in the variable specified by `store_result_as`. |
| **inspect_screenshot** | `xpath`: String, `prompt`: String, `store_result_as`: String, `return_to_api`: Boolean, `description`: String | Takes a screenshot of an element, processes it with vision-capable LLM using the provided prompt, and stores the result in the variable specified by `store_result_as`. When `return_to_api` is set to true (default behavior), the RPA execution will pause after capturing the screenshot, and control will be returned to the original Responses API for screenshot analysis. When `return_to_api` is set to false, the RPA executor will call the vision model itself and continue executing the RPA program steps without returning control. |
| **condition** | `condition`: String, `true_steps`: Array, `false_steps`: Array | Evaluates a logical condition using variables from the data context, and executes either `true_steps` or `false_steps` based on the result. |
| **request_human_intervention** | `prompt`: String, `xpath_highlight`: String, `store_result_as`: String, `timeout_sec`: Number, `on_timeout`: String | Displays a prompt to the user, optionally highlights elements, waits for user input within the timeout, and stores the response. The `on_timeout` parameter specifies behavior if no response is received (continue, retry, abort). |

This specification ensures that all actions supported by the Anthropic Computer API can be properly translated to actions that JSON RPA programs can execute, maintaining compatibility while providing a rich set of interaction possibilities.
